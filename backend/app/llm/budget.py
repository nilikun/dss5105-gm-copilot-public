"""Cost accounting and the daily spend cap.

Prices are per million tokens from the provider's pricing page (configured in backend/.env). Every call is
recorded in llm_usage; before a call, today's spend (UTC) is compared with DAILY_BUDGET_USD.
"""

from __future__ import annotations

import sqlite3
import time
from typing import Any

from app.config import SETTINGS
from app.llm.base import BudgetExceeded, Usage


def cost_usd(u: Usage) -> float:
    uncached = max(u.input_tokens - u.cached_tokens, 0)
    return (uncached * SETTINGS.price_input_per_m + u.cached_tokens * SETTINGS.price_cached_input_per_m
            + u.output_tokens * SETTINGS.price_output_per_m) / 1_000_000


def today_utc() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime())


def spent_today(db: sqlite3.Connection) -> float:
    return db.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM llm_usage WHERE day = ?", (today_utc(),)).fetchone()[0]


def check(db: sqlite3.Connection, budget: float | None = None) -> None:
    cap = SETTINGS.daily_budget_usd if budget is None else budget
    spent = spent_today(db)
    if spent >= cap:
        raise BudgetExceeded(f"daily LLM budget reached: ${spent:.4f} of ${cap:.2f} spent today (UTC)")


def record(db: sqlite3.Connection, model: str, purpose: str, turn_id: str | None, u: Usage,
           latency_ms: int) -> dict[str, Any]:
    c = cost_usd(u)
    db.execute("INSERT INTO llm_usage (ts, day, model, purpose, turn_id, input_tokens, cached_tokens, output_tokens, "
               "reasoning_tokens, cost_usd, latency_ms) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
               (time.time(), today_utc(), model, purpose, turn_id, u.input_tokens, u.cached_tokens, u.output_tokens,
                u.reasoning_tokens, c, latency_ms))
    db.commit()
    return {"model": model, "purpose": purpose, "input_tokens": u.input_tokens, "cached_tokens": u.cached_tokens,
            "output_tokens": u.output_tokens, "reasoning_tokens": u.reasoning_tokens, "cost_usd": round(c, 6),
            "latency_ms": latency_ms}


def summary(db: sqlite3.Connection) -> dict[str, Any]:
    day = today_utc()
    row = db.execute("SELECT COUNT(*) n, COALESCE(SUM(cost_usd),0) c, COALESCE(SUM(input_tokens),0) i, "
                     "COALESCE(SUM(output_tokens),0) o FROM llm_usage WHERE day = ?", (day,)).fetchone()
    return {"day_utc": day, "calls": row["n"], "cost_usd": round(row["c"], 4), "input_tokens": row["i"],
            "output_tokens": row["o"], "daily_budget_usd": SETTINGS.daily_budget_usd,
            "remaining_usd": round(max(SETTINGS.daily_budget_usd - row["c"], 0), 4)}
