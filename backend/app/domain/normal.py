"""What 'normal' stage output means (decision D6, analysis/threshold_backtest.py).

Baseline = median of the previous N working days; spread = 1.4826 × MAD; z = (actual − baseline) / spread.
Briefing tier: z < −1.75. Interrupt tier: z < −3, or z < −2 on 2 of the last 3 working days.
"""

from __future__ import annotations

import sqlite3
import statistics
from datetime import date
from typing import Any

from app.config import BRIEFING_Z, INTERRUPT_Z, MAD_TO_SIGMA, NORMAL_WINDOW_WORKING_DAYS, SUSTAINED_Z

DEFINITION = {
    "baseline": f"median of the previous {NORMAL_WINDOW_WORKING_DAYS} working days (Sundays excluded)",
    "spread": f"robust sigma = {MAD_TO_SIGMA} x median absolute deviation",
    "z": "(actual - baseline) / robust sigma",
    "briefing_tier": f"z < {BRIEFING_Z}",
    "interrupt_tier": f"z < {INTERRUPT_Z}, or z < {SUSTAINED_Z} on 2 of the last 3 working days",
    "evidence": "analysis/threshold_backtest.py",
}

Series = list[tuple[str, float]]


def working_series(db: sqlite3.Connection, stage: str) -> Series:
    return [(r[0], r[1]) for r in db.execute(
        "SELECT date, pieces_completed FROM production_log WHERE stage = ? ORDER BY date", (stage,))
        if date.fromisoformat(r[0]).weekday() != 6]


def robust_z(series: Series, idx: int) -> dict[str, Any] | None:
    """z of series[idx] against the working days strictly before it; None with fewer than 5 prior days."""
    hist = [v for _, v in series[max(0, idx - NORMAL_WINDOW_WORKING_DAYS):idx]]
    if len(hist) < 5:
        return None
    med = statistics.median(hist)
    sigma = MAD_TO_SIGMA * statistics.median(abs(v - med) for v in hist)
    actual = series[idx][1]
    return {"z": (actual - med) / sigma if sigma else 0.0, "baseline_median": med, "robust_sigma": sigma,
            "window": [series[max(0, idx - NORMAL_WINDOW_WORKING_DAYS)][0], series[idx - 1][0]],
            "window_days": len(hist), "actual": actual}


def judge(series: Series, idx: int, quoted: bool = False) -> dict[str, Any] | None:
    """Apply the two-tier rule at series[idx]. `quoted` = a hypothetical number: no sustained / streak logic."""
    zr = robust_z(series, idx)
    if zr is None:
        return None
    recent = [] if quoted else [robust_z(series, i) for i in range(max(1, idx - 2), idx + 1)]
    sustained = sum(r is not None and r["z"] < SUSTAINED_Z for r in recent) >= 2
    z = zr["z"]
    tier = "interrupt" if z < INTERRUPT_Z or sustained else "briefing" if z < BRIEFING_Z else "normal"
    direction = "below" if z < BRIEFING_Z else "above" if z > -BRIEFING_Z else "within"
    consecutive = 0
    if not quoted:
        for i in range(idx, 0, -1):
            r = robust_z(series, i)
            if r is None or r["z"] >= BRIEFING_Z:
                break
            consecutive += 1
    return {**zr, "tier": tier, "direction": direction, "consecutive_low_days": consecutive,
            "pct_vs_baseline": round(100 * (zr["actual"] / zr["baseline_median"] - 1), 1)}
