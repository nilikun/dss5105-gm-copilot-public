"""Two live attempts of PUBLIC D35 through the new subprocess/score/judge/report pipeline.

This script has no external-question option and can never label its output held-out.
"""

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from frozen_protocol import ROOT, SCORING_FILES, sha
from independent_scoring import contract_rules
from run_frozen import execute
from step3_reference import reference


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    case = json.loads((ROOT / "eval/fixtures/step3_production.json").read_text(encoding="utf-8"))["cases"][0]
    ref = reference(case, "2026-04-01")
    item = {
        "id": "PUBLIC_D35",
        "category": "judgement",
        "question": case["question"],
        "expected_behavior": "refuse",
        "required_facts": contract_rules(ref),
        "reference_evidence": [ref],
        "reference_answer": "ASSEMBLY produced 394 pieces on 25 March 2026, 48.6% below its prior "
        "20-working-day median of 766.5 (2–24 March). Cause unknown.",
        "prohibited_claims": [],
    }
    manifest = {
        "scope": "PUBLIC engineering smoke test — NOT held-out or human calibration",
        "status": "smoke_only",
        "source_sha256": {p: sha(ROOT / p) for p in SCORING_FILES},
        "execution": {
            "repetitions_per_item_per_version": 1,
            "randomization_seed": 5105,
            "budget_usd": 1,
            "timeout_seconds": 180,
            "max_api_calls_per_attempt": 12,
        },
        "agent_settings": {"model": "gpt-5.6-luna", "reasoning_effort": "low", "max_output_tokens": 4000},
        "judge_settings": {
            "model": "gpt-6-astra",
            "reasoning_effort": "low",
            "max_output_tokens": 4000,
            "timeout_seconds": 60,
        },
        "pricing": {
            "source_and_date": "User planning assumptions / repository rates; NOT verified billing",
            "agent": {"input_per_million": 0.2, "cached_input_per_million": 0.02, "output_per_million": 1.2},
            "judge": {"input_per_million": 10, "cached_input_per_million": 10, "output_per_million": 50},
        },
    }
    load_dotenv(ROOT / "backend/.env")
    load_dotenv(ROOT / "backend/.env.team")
    summary = execute(
        manifest,
        {"as_of": "2026-04-01T07:00:00", "items": [item]},
        {"baseline": args.baseline.resolve(), "improved": ROOT},
        args.output_dir,
        os.environ["OPENAI_API_KEY"],
    )
    print(json.dumps({"attempted": summary["attempted"], "scope": summary["scope"]}))


if __name__ == "__main__":
    main()
