"""Working-day arithmetic. The factory works Monday–Saturday and is closed on Sundays."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np


def working_days_between(start: date, end: date) -> int:
    """Mon–Sat days in [start, end)."""
    return int(np.busday_count(start, end, weekmask="1111110"))


def is_sunday(d: date) -> bool:
    return d.weekday() == 6


def previous_working_day(d: date) -> date:
    """The last Mon–Sat day strictly before d."""
    p = d - timedelta(days=1)
    while is_sunday(p):
        p -= timedelta(days=1)
    return p


def days(n: int) -> str:
    """'1 day' / '3 days' — display text for a day count computed by code."""
    return f"{n} day" if abs(n) == 1 else f"{n} days"
