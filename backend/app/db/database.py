"""SQLite data layer.

Base tables (orders, production_log, workshops) are loaded from the CSVs; the data advancer may append to them
as simulated time moves forward. State tables hold everything the system itself creates (notes, proposals,
audit log, evidence, traces, …). One connection per unit of work; SQLite serialises writers.
"""

from __future__ import annotations

import csv
import json
import re
import sqlite3
import threading
from pathlib import Path
from typing import Any

from app.config import DATA_DIR

BASE_SCHEMA = """
CREATE TABLE orders (
    order_id TEXT PRIMARY KEY,
    customer TEXT NOT NULL,
    product TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('TOPS', 'ACCESSORIES')),
    pieces INTEGER NOT NULL CHECK (pieces > 0),
    order_date TEXT NOT NULL,
    due_date TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('COMPLETE', 'IN_PROGRESS')),
    current_stage TEXT NOT NULL,
    last_activity_date TEXT NOT NULL,
    completed_date TEXT,
    days_late INTEGER
);
CREATE TABLE production_log (
    date TEXT NOT NULL,
    stage TEXT NOT NULL,
    pieces_completed INTEGER NOT NULL,
    PRIMARY KEY (date, stage)
);
CREATE TABLE workshops (
    workshop_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    capacity_pieces_per_day INTEGER NOT NULL,
    pickup_lead_days INTEGER NOT NULL,
    defect_rate REAL NOT NULL,
    cost_per_piece REAL NOT NULL,
    makes TEXT NOT NULL,
    status TEXT NOT NULL,
    max_batch_pieces INTEGER,
    current_queue_days REAL NOT NULL,
    notes TEXT
);
CREATE INDEX idx_orders_customer ON orders(customer);
CREATE INDEX idx_orders_status ON orders(status, due_date);
"""

STATE_SCHEMA = """
CREATE TABLE counters (name TEXT PRIMARY KEY, value INTEGER NOT NULL);
CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE clock_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    mode TEXT NOT NULL DEFAULT 'sim',
    sim_now TEXT NOT NULL,
    real_anchor REAL,
    data_anchor TEXT,
    scenario TEXT NOT NULL DEFAULT 'baseline'
);
CREATE TABLE notes (
    note_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL REFERENCES orders(order_id),
    text TEXT NOT NULL,
    created_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE TABLE outbox (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT,
    workshop_id TEXT,
    recipient_role TEXT NOT NULL,
    intent TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'in_outbox'
);
CREATE TABLE watches (
    watch_id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    params TEXT NOT NULL,
    snapshot TEXT NOT NULL,
    description TEXT NOT NULL,
    priority TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    fired_at TEXT,
    last_fired_on TEXT
);
CREATE TABLE pending_actions (
    action_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    payload TEXT NOT NULL,
    preview TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    turn_id TEXT,
    decided_at TEXT
);
CREATE TABLE audit_log (
    audit_id TEXT PRIMARY KEY,
    action_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    executed_at TEXT NOT NULL,
    actor TEXT NOT NULL,
    summary TEXT NOT NULL,
    before TEXT,
    after TEXT,
    undone_at TEXT
);
CREATE TABLE evidence (
    evidence_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    keys TEXT NOT NULL,
    description TEXT NOT NULL,
    rows TEXT NOT NULL,
    as_of TEXT NOT NULL,
    turn_id TEXT
);
CREATE TABLE conversations (
    conversation_id TEXT PRIMARY KEY,
    created_at REAL NOT NULL,
    title TEXT
);
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    turn_id TEXT,
    created_at REAL NOT NULL
);
CREATE TABLE traces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    turn_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    ts REAL NOT NULL,
    clock_time TEXT,
    kind TEXT NOT NULL,
    data TEXT NOT NULL
);
CREATE INDEX idx_traces_turn ON traces(turn_id, seq);
CREATE TABLE briefings (
    date TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    structured TEXT NOT NULL,
    narrative TEXT,
    narrative_status TEXT NOT NULL DEFAULT 'pending'
);
CREATE TABLE notifications (
    notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    priority TEXT NOT NULL,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    evidence_ids TEXT NOT NULL DEFAULT '[]',
    source_id TEXT,
    read INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE llm_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    day TEXT NOT NULL,
    model TEXT NOT NULL,
    purpose TEXT NOT NULL,
    turn_id TEXT,
    input_tokens INTEGER NOT NULL,
    cached_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    reasoning_tokens INTEGER NOT NULL,
    cost_usd REAL NOT NULL,
    latency_ms INTEGER NOT NULL
);
"""

INT_COLUMNS = {"pieces", "days_late", "pieces_completed", "capacity_pieces_per_day", "pickup_lead_days",
               "max_batch_pieces"}
REAL_COLUMNS = {"defect_rate", "cost_per_piece", "current_queue_days"}

_write_lock = threading.RLock()


def _coerce(column: str, value: str):
    if value == "":
        return None
    if column in INT_COLUMNS:
        return int(float(value))
    if column in REAL_COLUMNS:
        return float(value)
    return value


def _load_csv(conn: sqlite3.Connection, table: str, path: Path) -> None:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    cols = list(rows[0].keys())
    conn.executemany(
        f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})",
        [[_coerce(c, r[c]) for c in cols] for r in rows],
    )


def _new_connection(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if path != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL")
    return conn


def initialise(conn: sqlite3.Connection, data_dir: Path = DATA_DIR, start: str | None = None) -> None:
    """Create all tables, load the base CSVs and set the clock to the dataset's 'today' at 07:00."""
    from app.config import DATASET_TODAY

    # IF NOT EXISTS: a reset may keep some tables (spend, traces, chat history) and recreate the rest
    conn.executescript(re.sub(r"CREATE (TABLE|INDEX) ", r"CREATE \g<1> IF NOT EXISTS ", BASE_SCHEMA + STATE_SCHEMA))
    for table in ("orders", "production_log", "workshops"):
        _load_csv(conn, table, data_dir / f"{table}.csv")
    conn.execute("INSERT INTO clock_state (id, mode, sim_now) VALUES (1, 'sim', ?)",
                 (start or f"{DATASET_TODAY}T07:00",))
    conn.commit()


def connect(data_dir: Path = DATA_DIR, path: str = ":memory:") -> sqlite3.Connection:
    """A fresh database with the base data loaded (tests, evaluation runs)."""
    conn = _new_connection(path)
    initialise(conn, data_dir)
    return conn


def open_db(path: str) -> sqlite3.Connection:
    """Open the application database, creating and loading it on first use."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fresh = not p.exists()
    conn = _new_connection(path)
    if fresh:
        with _write_lock:
            initialise(conn)
    return conn


# Survive every reset: the day's model spend (or a reset would lift the daily budget cap), the AI execution
# log, and the manager's preferences.
ALWAYS_KEPT = {"llm_usage", "traces", "settings"}
# Also kept when only the factory's timeline is rewound: the chats and the evidence their answers cite, and the
# id counters so new evidence / proposal ids never reuse an id an old answer points to.
HISTORY_KEPT = {"conversations", "messages", "evidence", "counters"}


def reset_in_place(conn: sqlite3.Connection, scenario: str = "baseline", keep_history: bool = False) -> None:
    """Back to the dataset as delivered, clock at 2026-04-01 07:00, without deleting the file (other connections
    may hold it open, which Windows does not allow).

    The factory world is always reset: orders and production (the advancer appends to them), notes, outbox,
    watches, proposals, audit log, briefings and alerts. Spend, traces and settings are always kept; with
    keep_history (a rewind of the clock) the conversations, their evidence and the id counters are kept too.
    """
    keep = ALWAYS_KEPT | (HISTORY_KEPT if keep_history else set())
    with _write_lock:
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND "
                                             "name NOT LIKE 'sqlite_%'")]
        conn.execute("PRAGMA foreign_keys = OFF")
        for t in tables:
            if t not in keep:
                conn.execute(f"DROP TABLE IF EXISTS {t}")
        conn.execute("DELETE FROM settings WHERE key = 'processed_through'")  # simulation progress, not a preference
        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON")
        initialise(conn)
        conn.execute("UPDATE clock_state SET scenario = ? WHERE id = 1", (scenario,))
        conn.commit()


# ----------------------------------------------------------------- small helpers shared by the modules
def next_id(conn: sqlite3.Connection, name: str, prefix: str) -> str:
    with _write_lock:
        row = conn.execute("SELECT value FROM counters WHERE name = ?", (name,)).fetchone()
        value = (row[0] if row else 0) + 1
        conn.execute("INSERT INTO counters (name, value) VALUES (?, ?) "
                     "ON CONFLICT(name) DO UPDATE SET value = excluded.value", (name, value))
    return f"{prefix}{value}"


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def loads(text: str | None) -> Any:
    return json.loads(text) if text else None


def get_setting(conn: sqlite3.Connection, key: str, default: Any = None) -> Any:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return loads(row[0]) if row else default


def set_setting(conn: sqlite3.Connection, key: str, value: Any) -> None:
    conn.execute("INSERT INTO settings (key, value) VALUES (?, ?) "
                 "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, dumps(value)))
    conn.commit()
