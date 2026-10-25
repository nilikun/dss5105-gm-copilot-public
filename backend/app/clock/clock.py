"""The system's notion of 'now'. Tools never read the wall clock directly (TOOL_SPEC §1.6).

SimClock: an in-memory clock for tests and evaluation.
DbClock: the application clock, persisted in `clock_state` so it survives restarts. Two modes (D8):
  - sim:  time only moves when advanced (demo, scenarios);
  - real: data time = anchor + elapsed wall-clock time since the mode was switched on.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.domain.calendar import is_sunday, working_days_between  # noqa: F401  (re-exported for callers)


class Clock:
    def now(self) -> datetime:  # pragma: no cover - interface
        raise NotImplementedError

    def today(self) -> date:
        return self.now().date()


@dataclass
class SimClock(Clock):
    current: datetime

    @classmethod
    def at(cls, day: str, hour: int = 7) -> SimClock:
        return cls(datetime.fromisoformat(day).replace(hour=hour))

    def now(self) -> datetime:
        return self.current

    def advance(self, days: int = 0, hours: int = 0) -> None:
        self.current += timedelta(days=days, hours=hours)


class DbClock(Clock):
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def state(self) -> sqlite3.Row:
        return self.conn.execute("SELECT * FROM clock_state WHERE id = 1").fetchone()

    def now(self) -> datetime:
        s = self.state()
        if s["mode"] == "real" and s["real_anchor"] is not None:
            elapsed = time.time() - s["real_anchor"]
            return datetime.fromisoformat(s["data_anchor"]) + timedelta(seconds=elapsed)
        return datetime.fromisoformat(s["sim_now"])

    def set_now(self, when: datetime) -> None:
        self.conn.execute("UPDATE clock_state SET sim_now = ?, data_anchor = ?, real_anchor = ? WHERE id = 1",
                          (when.isoformat(timespec="minutes"), when.isoformat(timespec="minutes"),
                           time.time() if self.state()["mode"] == "real" else None))
        self.conn.commit()

    def set_mode(self, mode: str) -> None:
        if mode not in ("sim", "real"):
            raise ValueError("mode must be 'sim' or 'real'")
        now = self.now()
        self.conn.execute("UPDATE clock_state SET mode = ?, sim_now = ?, data_anchor = ?, real_anchor = ? WHERE id = 1",
                          (mode, now.isoformat(timespec="minutes"), now.isoformat(timespec="minutes"),
                           time.time() if mode == "real" else None))
        self.conn.commit()
