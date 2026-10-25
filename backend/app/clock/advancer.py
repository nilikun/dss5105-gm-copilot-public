"""Seeded data advancer: generates the days after the dataset ends so watches and alerts can actually fire.

Documented data extension (the brief allows extending the data). For each simulated day:
- production: each stage = level × (1 + noise), noise ~ N(0, 0.087) (the observed coefficient of variation);
  level = the stage's current run-rate (median of its last 5 working days in the delivered data), unless a
  scenario event sets it to its pre-anomaly normal or a factor of it. Sundays are zero.
- orders: an open order is active with p = 0.85 (0 if a scenario marks it stuck); an active order moves to the
  next stage with p = 1 / dwell, dwell = P50 cycle days / 4, stretched by how far the stage runs below normal.
  Leaving PACKING completes the order (completed_date, days_late).
- scenario events can also add new orders.
Each day uses its own RNG seeded by (scenario seed, date), so a run is reproducible.
"""

from __future__ import annotations

import random
import sqlite3
import statistics
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import yaml

from app.config import DATASET_TODAY, SCENARIO_DIR, STAGES
from app.domain import projection

NOISE_CV = 0.087
P_ACTIVE = 0.85
ANOMALY_START = "2026-03-25"  # pre-anomaly normal = median of the 20 working days before this date


@dataclass
class Scenario:
    name: str
    title: str
    description: str
    seed: int
    events: list[dict[str, Any]] = field(default_factory=list)


def list_scenarios() -> list[Scenario]:
    return [load_scenario(p.stem) for p in sorted(SCENARIO_DIR.glob("*.yaml"))]


def load_scenario(name: str) -> Scenario:
    data = yaml.safe_load((SCENARIO_DIR / f"{name}.yaml").read_text(encoding="utf-8"))
    return Scenario(name=data["name"], title=data.get("title", name), description=data.get("description", "").strip(),
                    seed=int(data.get("seed", 0)), events=data.get("events") or [])


def _day_index(d: date) -> int:
    return (d - date.fromisoformat(DATASET_TODAY)).days


def _active(event: dict[str, Any], idx: int) -> bool:
    lo = event.get("from_day", event.get("day", 0))
    hi = event.get("to_day", lo if "day" in event else 10_000)
    return lo <= idx <= hi


def _levels(db: sqlite3.Connection) -> tuple[dict[str, float], dict[str, float]]:
    """(current run-rate, pre-anomaly normal) per stage, from the delivered data only."""
    current, normal = {}, {}
    for s in STAGES:
        rows = [r[0] for r in db.execute(
            "SELECT pieces_completed FROM production_log WHERE stage = ? AND date <= ? AND pieces_completed > 0 "
            "ORDER BY date", (s, _base_last_day(db)))]
        pre = [r[0] for r in db.execute(
            "SELECT pieces_completed FROM production_log WHERE stage = ? AND date < ? AND pieces_completed > 0 "
            "ORDER BY date", (s, ANOMALY_START))]
        current[s] = statistics.median(rows[-5:])
        normal[s] = statistics.median(pre[-20:])
    return current, normal


def _base_last_day(db: sqlite3.Connection) -> str:
    return (date.fromisoformat(DATASET_TODAY) - timedelta(days=1)).isoformat()


def generate_day(db: sqlite3.Connection, day: date, scenario: Scenario) -> dict[str, Any]:
    """Append one simulated day (idempotent). Returns a summary of what changed."""
    if db.execute("SELECT 1 FROM production_log WHERE date = ?", (day.isoformat(),)).fetchone():
        return {"date": day.isoformat(), "skipped": True}
    rng = random.Random(f"{scenario.seed}-{day.isoformat()}")
    idx = _day_index(day)
    events = [e for e in scenario.events if _active(e, idx)]
    current, normal = _levels(db)
    summary: dict[str, Any] = {"date": day.isoformat(), "output": {}, "moved": [], "completed": [], "new_orders": []}
    sunday = day.weekday() == 6

    level_now: dict[str, float] = {}
    for s in STAGES:
        level = current[s]
        for e in events:
            if e["type"] == "stage_level" and e["stage"] == s:
                level = normal[s] if e["level"] == "normal" else normal[s] * float(e["level"])
        level_now[s] = level
        value = 0 if sunday else max(0, round(level * (1 + rng.gauss(0, NOISE_CV))))
        db.execute("INSERT INTO production_log (date, stage, pieces_completed) VALUES (?, ?, ?)",
                   (day.isoformat(), s, value))
        summary["output"][s] = value

    for e in events:
        if e["type"] == "new_order" and e.get("day") == idx:
            n = db.execute("SELECT MAX(CAST(SUBSTR(order_id, 5) AS INTEGER)) FROM orders").fetchone()[0] + 1
            o = e["order"]
            oid = f"ORD-{n:03d}"
            db.execute("INSERT INTO orders (order_id, customer, product, category, pieces, order_date, due_date, "
                       "status, current_stage, last_activity_date) "
                       "VALUES (?, ?, ?, ?, ?, ?, ?, 'IN_PROGRESS', 'KNITTING', ?)",
                       (oid, o["customer"], o["product"], o["category"], int(o["pieces"]), day.isoformat(),
                        (day + timedelta(days=int(o["due_in_days"]))).isoformat(), day.isoformat()))
            summary["new_orders"].append(oid)

    if not sunday:
        stuck = {e["order_id"] for e in events if e["type"] == "stuck_order"}
        proj = projection.fit(db, day)
        for o in db.execute("SELECT * FROM orders WHERE status = 'IN_PROGRESS' AND order_date < ? ORDER BY order_id",
                            (day.isoformat(),)).fetchall():
            if o["order_id"] in stuck or rng.random() > P_ACTIVE:
                continue
            stage = o["current_stage"]
            dwell = max(1.0, (proj.cycle_days(o["pieces"]) if proj else 24) / 4)
            dwell *= max(1.0, normal[stage] / max(level_now[stage], 1))
            updates = {"last_activity_date": day.isoformat()}
            if rng.random() < 1 / dwell:
                i = STAGES.index(stage)
                if i == len(STAGES) - 1:
                    late = (day - date.fromisoformat(o["due_date"])).days
                    updates |= {"status": "COMPLETE", "current_stage": "COMPLETE", "completed_date": day.isoformat(),
                                "days_late": late}
                    summary["completed"].append(o["order_id"])
                else:
                    updates["current_stage"] = STAGES[i + 1]
                    summary["moved"].append(f"{o['order_id']}→{STAGES[i + 1]}")
            cols = ", ".join(f"{k} = ?" for k in updates)
            db.execute(f"UPDATE orders SET {cols} WHERE order_id = ?", [*updates.values(), o["order_id"]])
    db.commit()
    return summary
