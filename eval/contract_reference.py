"""Small, independent CSV calculations for PUBLIC development contracts only.

No backend/tool/scorer imports and no model calls. Hidden authors must use their own
Excel workbook or script; this module is not their reference-answer generator.
"""

from __future__ import annotations

import csv
import statistics
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AS_OF = "2026-04-01"


def rows(filename: str) -> list[dict]:
    with (ROOT / "data" / filename).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def order_reference(order_id: str) -> dict:
    order = next(row for row in rows("orders.csv") if row["order_id"] == order_id)
    return {
        "type": "order", "as_of": AS_OF, "order_id": order_id,
        "stage": order["current_stage"], "status": order["status"],
        "due_date": order["due_date"] or None, "completed_date": order["completed_date"] or None,
    }


def production_reference(stage: str, start: str, end: str, *, baseline_before: str | None = None) -> dict:
    """Daily value or mean of Mon–Sat observations; fixed prior-20-day median.

    Window endpoints are inclusive; baseline strictly precedes baseline_before.
    Require all Mon–Sat dates in the requested observation window to be present.
    Missing records are not zero. Sunday's recorded zero is not an operating-day
    observation. A Sunday-only query is deliberately outside this helper.
    """
    from datetime import timedelta

    start_day, end_day = date.fromisoformat(start), date.fromisoformat(end)
    if end_day < start_day or end >= AS_OF:
        raise ValueError("require a completed, ordered observation window before the simulated date")
    series = sorted(
        (row["date"], int(row["pieces_completed"])) for row in rows("production_log.csv")
        if row["stage"] == stage and date.fromisoformat(row["date"]).weekday() != 6
    )
    actual = [(day, value) for day, value in series if start <= day <= end]
    expected_days = {
        (start_day + timedelta(days=i)).isoformat()
        for i in range((end_day - start_day).days + 1)
        if (start_day + timedelta(days=i)).weekday() != 6
    }
    if not expected_days or {day for day, _ in actual} != expected_days:
        raise ValueError("observation window has no working days or is missing observations")
    cutoff = baseline_before or start
    if cutoff > start:
        raise ValueError("baseline must precede the observation window")
    history = [(day, value) for day, value in series if day < cutoff][-20:]
    if len(history) != 20:
        raise ValueError("this development reference requires 20 baseline working days")
    baseline = statistics.median(value for _, value in history)
    value = statistics.mean(value for _, value in actual)
    return {
        "type": "production", "as_of": AS_OF, "stage": stage,
        "start": start, "end": end, "statistic": "daily" if start == end else "mean",
        "observed_days": len(actual), "actual": value,
        "baseline": baseline, "baseline_start": history[0][0], "baseline_end": history[-1][0],
        "baseline_days": len(history), "baseline_method": "median",
        "pct_change": 100 * (value / baseline - 1) if baseline else None,
        "cause": "unknown",
    }
