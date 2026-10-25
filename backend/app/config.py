"""Configuration. Domain parameters are documented decisions (docs/PLAN.md decision log); runtime settings come
from environment variables: backend/.env (personal, git-ignored) first, then backend/.env.team (the team's shared
settings, tracked in the private repo only — never published); see backend/.env.example."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKEND_DIR.parent
DATA_DIR = REPO_DIR / "data"
SCENARIO_DIR = DATA_DIR / "scenarios"
PROMPT_DIR = BACKEND_DIR / "prompts"
VAR_DIR = BACKEND_DIR / "var"  # runtime state: database, logs (git-ignored)

load_dotenv(BACKEND_DIR / ".env")       # personal settings first (git-ignored)
load_dotenv(BACKEND_DIR / ".env.team")  # then the team defaults shared in the private repo (never published)

# ----------------------------------------------------------------- domain (decisions, not knobs)
DATASET_TODAY = "2026-04-01"  # Wednesday; the clock starts here at 07:00 in simulation mode
STAGES = ("KNITTING", "ASSEMBLY", "WASHING", "PACKING")

# D6 — "normal" stage output (analysis/threshold_backtest.py)
NORMAL_WINDOW_WORKING_DAYS = 20
MAD_TO_SIGMA = 1.4826
BRIEFING_Z = -1.75
INTERRUPT_Z = -3.0
SUSTAINED_Z = -2.0  # z below this on 2 of the last 3 working days also interrupts

# TOOL_SPEC §7.1 — QUIET threshold
QUIET_WORKING_DAYS = 3

# Discovery: how many findings make the page
TOP_K_FINDINGS = 5

FIND_ORDERS_DEFAULT_LIMIT = 10
FIND_ORDERS_MAX_LIMIT = 50

# Agent loop bounds (docs/PLAN.md §6)
MAX_TOOL_STEPS = 6
MAX_REPAIRS = 1
HISTORY_TURNS = 6


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-5.6-luna")
    reasoning_effort: str = os.getenv("LLM_REASONING_EFFORT", "low")
    price_input_per_m: float = float(os.getenv("PRICE_INPUT_PER_M", "0.20"))
    price_cached_input_per_m: float = float(os.getenv("PRICE_CACHED_INPUT_PER_M", "0.02"))
    price_output_per_m: float = float(os.getenv("PRICE_OUTPUT_PER_M", "1.20"))
    daily_budget_usd: float = float(os.getenv("DAILY_BUDGET_USD", "1.0"))
    access_code: str = os.getenv("ACCESS_CODE", "")
    critic_enabled_default: bool = _bool("CRITIC_ENABLED", False)
    db_path: str = os.getenv("DB_PATH", str(VAR_DIR / "gm.db"))
    log_dir: str = os.getenv("LOG_DIR", str(VAR_DIR / "logs"))
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "20"))
    # Behind Cloudflare every request arrives from the tunnel; trust CF-Connecting-IP only when this is set,
    # otherwise anyone could forge the header and dodge the per-IP limit.
    trust_proxy: bool = _bool("TRUST_PROXY", False)


SETTINGS = Settings()
