"""The clock-driven scheduler (docs/PLAN.md §7).

At each day boundary (07:00 clock time) it: generates the previous day's data (advancer), runs the alert policy,
evaluates watches and builds the structured briefing. Within a day it only evaluates watches (timed reminders).
Sim mode advances on request; real mode is driven by a background ticker that calls `catch_up`.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from typing import Any

from app.clock import DbClock
from app.clock.advancer import generate_day, load_scenario
from app.db.database import get_setting, set_setting
from app.workflows import briefing, notifications, watch_engine


def _processed_through(db: sqlite3.Connection) -> date:
    v = get_setting(db, "processed_through")
    if v:
        return date.fromisoformat(v)
    first = DbClock(db).now().date()
    set_setting(db, "processed_through", first.isoformat())
    return first


def _scenario(db: sqlite3.Connection):
    return load_scenario(db.execute("SELECT scenario FROM clock_state WHERE id = 1").fetchone()[0])


def run_boundary(db: sqlite3.Connection, clock: DbClock, day: date) -> dict[str, Any]:
    """Everything that happens at 07:00 on `day`."""
    scenario = _scenario(db)
    last_log = date.fromisoformat(db.execute("SELECT MAX(date) FROM production_log").fetchone()[0])
    generated = []
    d = last_log + timedelta(days=1)
    while d < day:
        generated.append(generate_day(db, d, scenario))
        d += timedelta(days=1)
    alerts = []
    for g in generated:
        if not g.get("skipped"):
            alerts += notifications.on_new_day(db, clock, date.fromisoformat(g["date"]))
    fired = watch_engine.evaluate_all(db, clock)
    b = briefing.ensure(db, clock, rebuild=True)
    set_setting(db, "processed_through", day.isoformat())
    return {"day": day.isoformat(), "generated": generated, "alerts": alerts, "watches": fired,
            "briefing_items": len(b["structured"]["yesterday"]) + len(b["structured"]["at_risk"])}


def advance(db: sqlite3.Connection, days: int = 0, hours: int = 0) -> dict[str, Any]:
    clock = DbClock(db)
    start = clock.now()
    target = start + timedelta(days=days, hours=hours)
    report = catch_up(db, clock, target)
    clock.set_now(target)
    report["watches_at_target"] = watch_engine.evaluate_all(db, clock)
    report["from"], report["to"] = start.isoformat(timespec="minutes"), target.isoformat(timespec="minutes")
    return report


def catch_up(db: sqlite3.Connection, clock: DbClock, target: datetime | None = None) -> dict[str, Any]:
    """Run every 07:00 boundary between the last processed day and `target` (default: now)."""
    target = target or clock.now()
    done = _processed_through(db)
    boundaries = []
    d = done + timedelta(days=1)
    while datetime.combine(d, datetime.min.time()).replace(hour=7) <= target:
        clock.set_now(datetime.combine(d, datetime.min.time()).replace(hour=7))
        boundaries.append(run_boundary(db, clock, d))
        d += timedelta(days=1)
    return {"boundaries": boundaries}


def start_day(db: sqlite3.Connection) -> None:
    """On startup: make sure today's structured briefing exists."""
    _processed_through(db)
    briefing.ensure(db, DbClock(db))
