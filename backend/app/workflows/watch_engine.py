"""Evaluate every active watch at a clock tick (deterministic; no LLM)."""

from __future__ import annotations

import sqlite3
from typing import Any

from app.clock import Clock
from app.db.database import loads
from app.domain import watches
from app.tools.base import EvidenceStore
from app.workflows.notifications import notify


def evaluate_all(db: sqlite3.Connection, clock: Clock) -> list[dict[str, Any]]:
    now = clock.now()
    events = []
    for r in db.execute("SELECT * FROM watches WHERE status = 'active' ORDER BY created_at").fetchall():
        w = dict(r)
        w["params"], w["snapshot"] = loads(w["params"]), loads(w["snapshot"])
        res = watches.evaluate(db, w, now)
        action = res["action"]
        if action == "none":
            continue
        if action == "fire":
            ev = EvidenceStore(db, clock, f"watch-{w['watch_id']}").register(
                "watch", [w["watch_id"]], f"watch {w['watch_id']} fired: {res['title']}", res.get("rows", []))
            prio = "P1" if w["priority"] == "interrupt" else "P2"
            n = notify(db, clock, prio, "watch", f"{res['title']} ({w['watch_id']})", res["body"], [ev.id],
                       w["watch_id"], capped=False)  # the manager asked for this one: never capped
            if res.get("once", True):
                db.execute("UPDATE watches SET status = 'fired', fired_at = ? WHERE watch_id = ?",
                           (now.isoformat(timespec="minutes"), w["watch_id"]))
            else:
                db.execute("UPDATE watches SET last_fired_on = ? WHERE watch_id = ?", (res["fired_on"], w["watch_id"]))
            events.append({"watch_id": w["watch_id"], "action": "fired", "notification": n})
        else:
            db.execute("UPDATE watches SET status = ? WHERE watch_id = ?", (action, w["watch_id"]))
            events.append({"watch_id": w["watch_id"], "action": action, "note": res.get("note")})
        db.commit()
    return events
