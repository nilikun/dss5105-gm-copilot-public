"""Dates computed by code and given to the model up front, so common questions need no resolve_time step.
The same values are added to the verifier's whitelist: they are tool-made facts, not model arithmetic."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import Any

from app.domain.calendar import previous_working_day


def build(db: sqlite3.Connection, now: datetime) -> dict[str, Any]:
    today = now.date()
    monday = today - timedelta(days=today.weekday())
    last_log = db.execute("SELECT MAX(date) FROM production_log").fetchone()[0]
    return {
        "now": now.strftime("%Y-%m-%d %H:%M"), "today": today.isoformat(), "weekday": now.strftime("%A"),
        "yesterday": (today - timedelta(days=1)).isoformat(),
        "previous_working_day": previous_working_day(today).isoformat(),
        "this_week": [monday.isoformat(), (monday + timedelta(days=6)).isoformat()],
        "last_week": [(monday - timedelta(days=7)).isoformat(), (monday - timedelta(days=1)).isoformat()],
        "latest_day_in_production_log": last_log,
    }


def render(cal: dict[str, Any]) -> str:
    return ("Calendar (computed by the system — use these dates directly): "
            f"today {cal['today']} ({cal['weekday']}); yesterday {cal['yesterday']}; previous working day "
            f"{cal['previous_working_day']}; this week {cal['this_week'][0]}..{cal['this_week'][1]}; last week "
            f"{cal['last_week'][0]}..{cal['last_week'][1]}; latest day with output data "
            f"{cal['latest_day_in_production_log']}. For any other phrase use resolve_time.")
