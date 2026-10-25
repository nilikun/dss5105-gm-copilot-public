"""Order risk levels (decisions D13–D14, TOOL_SPEC §7).

OVERDUE  due date before today and not complete
AT_RISK  P50 projected finish after the due date (likely late)
WATCH    only the P80 projected finish after the due date (could slip)
OK       otherwise
QUIET    a flag, not a level: no activity for ≥ QUIET_WORKING_DAYS working days
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app.config import QUIET_WORKING_DAYS
from app.domain.calendar import working_days_between
from app.domain.projection import Projection

DEFINITION = {
    "OVERDUE": "due date before today and the order is not complete",
    "AT_RISK": "P50 projected finish is after the due date (likely late)",
    "WATCH": "only the P80 projected finish is after the due date (could slip)",
    "OK": "both projected finishes are on or before the due date",
    "QUIET": f"flag: no recorded activity for at least {QUIET_WORKING_DAYS} working days",
    "projection": "order date + log-linear size model (see projection definition)",
}

LEVEL_ORDER = {"OVERDUE": 0, "AT_RISK": 1, "WATCH": 2, "OK": 3}


def classify(order: dict[str, Any], today: date, proj: Projection | None) -> dict[str, Any]:
    oid = order["order_id"]
    due = date.fromisoformat(order["due_date"])
    if order["status"] == "COMPLETE":
        return {"order_id": oid, "level": "COMPLETE", "completed_date": order["completed_date"],
                "days_late": order["days_late"], "reasons": [f"{oid} completed on {order['completed_date']}"]}
    ordered = date.fromisoformat(order["order_date"])
    last = date.fromisoformat(order["last_activity_date"])
    idle_wd = working_days_between(last, today) if last < today else 0
    p50 = proj.finish(ordered, order["pieces"], 0.5) if proj else None
    p80 = proj.finish(ordered, order["pieces"], 0.8) if proj else None
    reasons = []
    if due < today:
        level = "OVERDUE"
        reasons.append(f"due {due.isoformat()}, {(today - due).days} days ago, still in {order['current_stage']}")
    elif p50 and p50 > due:
        level = "AT_RISK"
        reasons.append(f"P50 projected finish {p50.isoformat()} is after the due date {due.isoformat()}")
    elif p80 and p80 > due:
        level = "WATCH"
        reasons.append(f"P80 projected finish {p80.isoformat()} is after the due date {due.isoformat()}")
    else:
        level = "OK"
        if p80:
            reasons.append(f"P80 projected finish {p80.isoformat()} is on or before the due date {due.isoformat()}")
    quiet = idle_wd >= QUIET_WORKING_DAYS
    if quiet:
        reasons.append(f"no activity for {idle_wd} working days (last on {last.isoformat()})")
    return {"order_id": oid, "customer": order["customer"], "product": order["product"], "pieces": order["pieces"],
            "stage": order["current_stage"], "due_date": due.isoformat(), "days_to_due": (due - today).days,
            "level": level, "quiet": quiet, "idle_working_days": idle_wd,
            "p50_finish": p50.isoformat() if p50 else None, "p80_finish": p80.isoformat() if p80 else None,
            "slack_days_p50": (due - p50).days if p50 else None, "reasons": reasons}
