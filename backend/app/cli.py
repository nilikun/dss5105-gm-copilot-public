"""Ask the co-pilot from a terminal and watch every step it takes.

    uv run python -m app.cli "Was assembly's output yesterday normal?"
    uv run python -m app.cli --fresh "How is the TrendCart order doing?"     (in-memory database, clock at 2026-04-01)
"""

from __future__ import annotations

import argparse

from app.agent.runtime import Agent
from app.clock import DbClock, SimClock
from app.config import DATASET_TODAY, SETTINGS
from app.db.database import connect, open_db
from app.llm.openai_responses import OpenAIResponsesClient
from app.observability.logging_setup import configure


def main() -> None:
    configure()
    ap = argparse.ArgumentParser()
    ap.add_argument("question", nargs="+")
    ap.add_argument("--fresh", action="store_true", help="use a fresh in-memory database")
    ap.add_argument("--critic", action="store_true", help="enable the LLM critic")
    ap.add_argument("--conversation", default=None)
    a = ap.parse_args()
    if a.fresh:
        db, clock = connect(), SimClock.at(DATASET_TODAY)
    else:
        db = open_db(SETTINGS.db_path)
        clock = DbClock(db)
    reply = Agent(db, clock, OpenAIResponsesClient(), critic_enabled=a.critic).run(" ".join(a.question),
                                                                                    a.conversation)
    print("\n" + "=" * 80)
    print(f"[{reply.kind}] {reply.headline}")
    if reply.details:
        print("\n" + reply.details)
    for o in reply.options:
        print(f"  ( ) {o.label}")
    for p in reply.proposals:
        print(f"  [{p['action_id']}] {p['preview']}  — awaiting confirmation")
    print(f"\nevidence: {reply.evidence_ids} · {reply.llm_calls} LLM calls · ${reply.cost_usd:.5f} · "
          f"{reply.latency_s}s")


if __name__ == "__main__":
    main()
