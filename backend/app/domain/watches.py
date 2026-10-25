"""Standing checks ('tell me if…') as a small typed language, not free text (docs/PLAN.md §7).

order_stage_unchanged(order_id, by)   fires at `by` 07:00 if the order is still in the stage it was in when set
order_not_complete(order_id, by)      fires at `by` 07:00 if the order is not complete
stage_below_normal(stage, tier)       fires on each new log day whose output is at or below `tier`
reminder(at, text[, stage])           fires at `at`; with `stage`, only if that stage is below normal then
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from typing import Any

from app.domain import normal

TYPES = ("order_stage_unchanged", "order_not_complete", "stage_below_normal", "reminder")


def describe(kind: str, p: dict[str, Any], snapshot: dict[str, Any]) -> str:
    if kind == "order_stage_unchanged":
        return (f"On {p['by']} at 07:00, alert me if {p['order_id']} is still in {snapshot['stage']}.")
    if kind == "order_not_complete":
        return f"On {p['by']} at 07:00, alert me if {p['order_id']} is not complete."
    if kind == "stage_below_normal":
        return f"Alert me whenever {p['stage']} output is below normal ({p['tier']} tier or worse)."
    if kind == "reminder":
        cond = f" if {p['stage']} is still below normal" if p.get("stage") else ""
        return f"At {p['at'].replace('T', ' ')}, remind me{cond}: \"{p['text']}\""
    raise ValueError(kind)


def _order(db: sqlite3.Connection, oid: str) -> dict[str, Any] | None:
    r = db.execute("SELECT * FROM orders WHERE order_id = ?", (oid,)).fetchone()
    return dict(r) if r else None


def _stage_status(db: sqlite3.Connection, stage: str) -> tuple[dict[str, Any] | None, str | None]:
    series = normal.working_series(db, stage)
    if not series:
        return None, None
    return normal.judge(series, len(series) - 1), series[-1][0]


def evaluate(db: sqlite3.Connection, w: dict[str, Any], now: datetime) -> dict[str, Any]:
    """Decide what happens to one active watch now. Returns {'action': none|fire|satisfied|expired, ...}."""
    p, snap = w["params"], w["snapshot"]
    if now.isoformat(timespec="minutes") > w["expires_at"]:
        return {"action": "expired"}
    kind = w["type"]
    due_now = lambda d: now >= datetime.fromisoformat(f"{d}T07:00")  # noqa: E731
    if kind in ("order_stage_unchanged", "order_not_complete"):
        o = _order(db, p["order_id"])
        if o is None:
            return {"action": "expired"}
        if o["status"] == "COMPLETE":
            return {"action": "satisfied", "note": f"{o['order_id']} completed on {o['completed_date']}"}
        if kind == "order_stage_unchanged" and o["current_stage"] != snap["stage"]:
            return {"action": "satisfied", "note": f"{o['order_id']} moved to {o['current_stage']}"}
        if due_now(p["by"]):
            if kind == "order_stage_unchanged":
                body = (f"{o['order_id']} ({o['pieces']} × {o['product']}, {o['customer']}) is still in "
                        f"{o['current_stage']}; last activity {o['last_activity_date']}, due {o['due_date']}.")
                title = f"{o['order_id']} has not moved"
            else:
                body = (f"{o['order_id']} is not complete: in {o['current_stage']}, due {o['due_date']}, "
                        f"last activity {o['last_activity_date']}.")
                title = f"{o['order_id']} is not complete"
            return {"action": "fire", "once": True, "title": title, "body": body, "rows": [o]}
        return {"action": "none"}
    if kind == "stage_below_normal":
        r, d = _stage_status(db, p["stage"])
        if r is None or d == w.get("last_fired_on"):
            return {"action": "none"}
        worse = r["tier"] == "interrupt" or (p["tier"] == "briefing" and r["tier"] == "briefing")
        if worse and r["direction"] == "below":
            return {"action": "fire", "once": False, "fired_on": d, "title": f"{p['stage']} below normal",
                    "body": f"{p['stage']} made {r['actual']:.0f} pieces on {d} vs a normal "
                            f"{r['baseline_median']:.0f} ({r['pct_vs_baseline']}%, {r['tier']} tier).",
                    "rows": [{"stage": p["stage"], "date": d, "actual": r["actual"],
                              "baseline_median": r["baseline_median"], "z": round(r["z"], 2)}]}
        return {"action": "none"}
    if kind == "reminder":
        if now < datetime.fromisoformat(p["at"]):
            return {"action": "none"}
        if p.get("stage"):
            r, d = _stage_status(db, p["stage"])
            if r is not None and r["tier"] == "normal":
                return {"action": "satisfied", "note": f"{p['stage']} was back to normal on {d}"}
        return {"action": "fire", "once": True, "title": "Reminder", "body": p["text"], "rows": [p]}
    return {"action": "none"}


def parse_when(s: str) -> datetime:
    """ISO date (→ 07:00) or ISO datetime."""
    return datetime.fromisoformat(s) if "T" in s else datetime.combine(date.fromisoformat(s), datetime.min.time()) \
        .replace(hour=7)
