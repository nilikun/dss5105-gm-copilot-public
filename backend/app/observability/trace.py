"""Turn-level tracing: every step the AI takes is logged three ways.

1. the `traces` table   — what the UI's "Show thinking" panel and /api/traces read;
2. a JSONL file per day — var/logs/traces-YYYY-MM-DD.jsonl, for offline analysis;
3. the console          — one readable line per step, e.g.
       [turn 7f3a] · action    use tool compare_to_normal {"stage":"ASSEMBLY"} → ok tier=interrupt [E1] (5 ms)

Event kinds: question · plan · action · llm · draft · verifier · critic · repair · fallback · reply · error ·
workflow (briefing, watches, clock).
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.clock import Clock
from app.config import SETTINGS
from app.db.database import dumps

log = logging.getLogger("gm.trace")

SYMBOL = {"question": "▶", "plan": "·", "action": "·", "llm": "·", "draft": "·", "verifier": "✓", "critic": "·",
          "repair": "↻", "fallback": "!", "reply": "■", "error": "!", "workflow": "◆"}


def _short(obj: Any, n: int = 160) -> str:
    s = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False, default=str, separators=(",", ":"))
    return s if len(s) <= n else s[: n - 1] + "…"


def console_line(turn_id: str, kind: str, data: dict[str, Any]) -> str:
    sym = SYMBOL.get(kind, "·")
    if kind == "verifier" and not data.get("ok", True):
        sym = "✗"
    msg = data.get("message") or ""
    if kind == "question":
        msg = f'"{_short(data.get("text", ""), 200)}"'
    elif kind == "action":
        status = "ok" if data.get("ok") else f"ERROR {data.get('error_code')}"
        ev = f" [{', '.join(data.get('evidence', []))}]" if data.get("evidence") else ""
        msg = (f"use tool {data.get('tool')} {_short(data.get('args', {}), 120)} → {status} "
               f"{data.get('summary', '')}{ev} ({data.get('ms', 0):.0f} ms)")
    elif kind == "llm":
        msg = (f"{data.get('purpose')} · {data.get('model')} · in {data.get('input_tokens')} "
               f"(cached {data.get('cached_tokens')}) · out {data.get('output_tokens')} · "
               f"${data.get('cost_usd', 0):.5f} · {data.get('latency_ms')} ms")
    return f"[turn {turn_id[:6]}] {sym} {kind:<9} {msg}"


class Tracer:
    def __init__(self, db: sqlite3.Connection, clock: Clock, turn_id: str,
                 sink: Callable[[dict[str, Any]], None] | None = None, log_dir: str | None = None):
        self.db, self.clock, self.turn_id, self.sink = db, clock, turn_id, sink
        self.seq = 0
        self.dir = Path(log_dir or SETTINGS.log_dir)
        self.dir.mkdir(parents=True, exist_ok=True)

    def emit(self, kind: str, /, **data: Any) -> dict[str, Any]:
        self.seq += 1
        event = {"turn_id": self.turn_id, "seq": self.seq, "ts": time.time(),
                 "clock_time": self.clock.now().isoformat(timespec="minutes"), "kind": kind, "data": data}
        self.db.execute("INSERT INTO traces (turn_id, seq, ts, clock_time, kind, data) VALUES (?, ?, ?, ?, ?, ?)",
                        (self.turn_id, self.seq, event["ts"], event["clock_time"], kind, dumps(data)))
        self.db.commit()
        day = time.strftime("%Y-%m-%d", time.gmtime(event["ts"]))
        with (self.dir / f"traces-{day}.jsonl").open("a", encoding="utf-8") as f:
            f.write(dumps(event) + "\n")
        log.info(console_line(self.turn_id, kind, data))
        if self.sink:
            self.sink(event)
        return event


def load_turn(db: sqlite3.Connection, turn_id: str) -> list[dict[str, Any]]:
    return [{"seq": r["seq"], "ts": r["ts"], "clock_time": r["clock_time"], "kind": r["kind"],
             "data": json.loads(r["data"])}
            for r in db.execute("SELECT * FROM traces WHERE turn_id = ? ORDER BY seq", (turn_id,))]


def recent_turns(db: sqlite3.Connection, limit: int = 30) -> list[dict[str, Any]]:
    rows = db.execute("SELECT turn_id, MIN(ts) AS started, MAX(ts) AS ended, COUNT(*) AS steps FROM traces "
                      "GROUP BY turn_id ORDER BY started DESC LIMIT ?", (limit,)).fetchall()
    out = []
    for r in rows:
        first = db.execute("SELECT kind, data FROM traces WHERE turn_id = ? ORDER BY seq LIMIT 1",
                           (r["turn_id"],)).fetchone()
        last = db.execute("SELECT kind, data FROM traces WHERE turn_id = ? ORDER BY seq DESC LIMIT 1",
                          (r["turn_id"],)).fetchone()
        out.append({"turn_id": r["turn_id"], "started": r["started"], "duration_s": round(r["ended"] - r["started"], 2),
                    "steps": r["steps"], "first": {"kind": first["kind"], **json.loads(first["data"])},
                    "last": {"kind": last["kind"], **json.loads(last["data"])}})
    return out


def summarize_result(result: Any) -> str:
    """A few salient fields of a ToolResult for the console line."""
    if not result.ok:
        return _short(result.error.message, 100)
    d = result.data
    keys = ("verdict", "tier", "level", "total_matches", "count", "counts", "covered", "start", "proposal_id",
            "suppressed_count", "earliest_finish")
    parts = []
    for k in keys:
        if k in d:
            parts.append(f"{k}={_short(d[k], 60)}")
    if not parts and "results" in d and d["results"]:
        r = d["results"][0]
        parts = [f"{r.get('stage')}: tier={r.get('tier')} z={r.get('z')}"]
    if not parts and "assessment" in d:
        parts = [f"level={d['assessment'].get('level')}"]
    if not parts and "findings" in d:
        parts = [f"{len(d['findings'])} findings"]
    return " ".join(parts)[:160]
