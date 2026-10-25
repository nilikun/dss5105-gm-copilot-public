"""Order completion projection (decision D13, analysis/projection_backtest.py).

log(cycle_days) = a + b·log(pieces), fitted on orders completed up to `as_of`. P50 / P80 come from the
median / 80th percentile of the residuals. Load scaling was tested and rejected (it made forecasts worse).
"""

from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np

DEFINITION = {
    "model": "log(cycle_days) = a + b * log(pieces), least squares on completed orders",
    "p50": "fitted value + median residual",
    "p80": "fitted value + 80th-percentile residual",
    "backtest": "walk-forward over 34 orders: MAE 4.6 days vs 6.9 for promised dates (analysis/projection_backtest.py)",
    "not_used": "current load (scaling by load made forecasts worse in the backtest)",
}


@dataclass(frozen=True)
class Projection:
    a: float
    b: float
    q50: float
    q80: float
    n: int
    pieces_range: tuple[int, int]

    def cycle_days(self, pieces: int, q: float = 0.5) -> float:
        resid = self.q50 if q == 0.5 else self.q80
        return math.exp(self.a + self.b * math.log(pieces) + resid)

    def finish(self, start: date, pieces: int, q: float = 0.5) -> date:
        return start + timedelta(days=math.ceil(self.cycle_days(pieces, q)))


def fit(db: sqlite3.Connection, as_of: date) -> Projection | None:
    rows = db.execute("SELECT pieces, order_date, completed_date FROM orders WHERE status = 'COMPLETE' "
                      "AND completed_date <= ?", (as_of.isoformat(),)).fetchall()
    if len(rows) < 10:
        return None
    pieces = np.array([r[0] for r in rows], dtype=float)
    cycle = np.array([(date.fromisoformat(r[2]) - date.fromisoformat(r[1])).days for r in rows], dtype=float)
    x, y = np.log(pieces), np.log(np.maximum(cycle, 1))
    b, a = np.polyfit(x, y, 1)
    resid = y - (a + b * x)
    return Projection(a=float(a), b=float(b), q50=float(np.quantile(resid, 0.5)), q80=float(np.quantile(resid, 0.8)),
                      n=len(rows), pieces_range=(int(pieces.min()), int(pieces.max())))
