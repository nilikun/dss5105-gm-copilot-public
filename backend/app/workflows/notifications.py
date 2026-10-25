"""Alerts and the proactive policy — the dial between 'useful' and 'muted' (docs/PLAN.md §7).

P1 interrupt: pushed now (the manager's own watch fired; an interrupt-tier output drop at onset; a large order
               newly overdue). System alerts beyond the daily cap are downgraded to P2.
P2 briefing:   shown in the next briefing and the alert list (briefing-tier drops, continuing drops, smaller
               orders newly overdue).
P3:            not raised; available on request.
"""

from __future__ import annotations

import sqlite3
from datetime import date
from typing import Any

from app.clock import Clock
from app.config import STAGES
from app.db.database import dumps, get_setting
from app.domain import normal

DEFAULT_INTERRUPT_CAP = 3
LARGE_ORDER_PIECES = 1000


def interrupts_today(db: sqlite3.Connection, day: str) -> int:
    return db.execute("SELECT COUNT(*) FROM notifications WHERE priority = 'P1' AND kind != 'watch' AND "
                      "substr(created_at, 1, 10) = ?", (day,)).fetchone()[0]


def notify(db: sqlite3.Connection, clock: Clock, priority: str, kind: str, title: str, body: str,
           evidence_ids: list[str] | None = None, source_id: str | None = None, capped: bool = True) -> dict[str, Any]:
    now = clock.now().isoformat(timespec="minutes")
    note = ""
    if priority == "P1" and capped:
        cap = get_setting(db, "interrupt_cap", DEFAULT_INTERRUPT_CAP)
        if interrupts_today(db, now[:10]) >= cap:
            priority, note = "P2", f" (daily interrupt cap of {cap} reached; moved to the briefing)"
    cur = db.execute("INSERT INTO notifications (created_at, priority, kind, title, body, evidence_ids, source_id) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?)", (now, priority, kind, title, body + note,
                                                      dumps(evidence_ids or []), source_id))
    db.commit()
    return {"notification_id": cur.lastrowid, "priority": priority, "title": title}


def on_new_day(db: sqlite3.Connection, clock: Clock, day: date) -> list[dict[str, Any]]:
    """Run the policy after the data for `day` arrived."""
    raised: list[dict[str, Any]] = []
    if day.weekday() != 6:
        for s in STAGES:
            series = normal.working_series(db, s)
            if not series or series[-1][0] != day.isoformat():
                continue
            r = normal.judge(series, len(series) - 1)
            if r is None or r["tier"] == "normal" or r["direction"] != "below":
                continue
            prev = normal.judge(series, len(series) - 2)
            onset = prev is None or prev["tier"] != "interrupt"
            prio = "P1" if r["tier"] == "interrupt" and onset else "P2"
            body = (f"{s} made {r['actual']:.0f} pieces on {day.isoformat()} vs a normal {r['baseline_median']:.0f} "
                    f"({r['pct_vs_baseline']}%, {r['tier']} tier, "
                    f"{r['consecutive_low_days']} low working days in a row).")
            raised.append(notify(db, clock, prio, "stage_drop", f"{s} output below normal", body, source_id=s))
    for o in db.execute("SELECT * FROM orders WHERE status = 'IN_PROGRESS' AND due_date = ?", (day.isoformat(),)):
        prio = "P1" if o["pieces"] >= LARGE_ORDER_PIECES else "P2"
        body = (f"{o['order_id']} ({o['pieces']} × {o['product']}, {o['customer']}) was due {o['due_date']} and is "
                f"still in {o['current_stage']}.")
        raised.append(notify(db, clock, prio, "overdue", f"{o['order_id']} is now overdue", body,
                             source_id=o["order_id"]))
    return raised
