"""Capture PUBLIC reproducibility metadata without opening any hidden question or label file.

Produces a provisional manifest; the independent custodian completes and freezes it
only after an accepted human calibration report and clean committed code exist.
"""

import argparse
import json
import platform
import subprocess
from importlib.metadata import version
from pathlib import Path

from frozen_protocol import ROOT, SCORING_FILES, sha


def capture(baseline, improved, out):
    manifest = json.loads((ROOT / "eval/heldout_freeze.template.json").read_text(encoding="utf-8"))
    manifest["status"] = "provisional_not_releasable"
    for label, checkout in [("baseline", baseline), ("improved", improved)]:
        manifest["versions"][label + "_commit"] = subprocess.check_output(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True
        ).strip()
        manifest["versions"][label + "_dirty"] = bool(
            subprocess.check_output(["git", "-C", str(checkout), "status", "--porcelain"], text=True).strip()
        )
        manifest["versions"][label + "_prompts_sha256"] = {
            p.name: sha(p) for p in sorted((checkout / "backend/prompts").glob("*.md"))
        }
    manifest["versions"].update(
        scorer_commit=subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip(),
        scoring_files_sha256={p: sha(ROOT / p) for p in SCORING_FILES},
        rubric_sha256=sha(ROOT / "eval/protocol/rubric.md"),
        dependency_lock_sha256=sha(ROOT / "backend/uv.lock"),
        python_version=platform.python_version(),
        sdk_versions={k: version(k) for k in ("openai", "pydantic", "pandas", "PyYAML")},
    )
    manifest["data"] = {
        "snapshot_sha256": json.loads((ROOT / "eval/baselines/step1.json").read_text(encoding="utf-8"))[
            "data_snapshot_sha256"
        ],
        "files": [
            {"path": p.relative_to(ROOT).as_posix(), "sha256": sha(p)} for p in sorted((ROOT / "data").glob("*.csv"))
        ],
    }
    manifest["agent_settings"].update(
        provider="OpenAI Responses",
        model="gpt-5.6-luna",
        reasoning_effort="low",
        temperature_or_omitted="omitted",
        seed_or_unsupported="unsupported",
        max_output_tokens=4000,
        critic_enabled=False,
        max_tool_steps=6,
        repair_limit=1,
    )
    manifest["judge_settings"].update(
        provider="OpenAI Responses",
        model="gpt-6-astra",
        reasoning_effort="low",
        temperature_or_omitted="omitted",
        max_output_tokens=4000,
        timeout_seconds=60,
        max_retries=0,
        prompt_sha256=sha(ROOT / "eval/protocol/judge_prompt.md"),
        rubric_sha256=sha(ROOT / "eval/protocol/rubric.md"),
    )
    manifest["execution"].update(
        repetitions_per_item_per_version=3,
        order="seeded shuffle of item/repeat/version",
        randomization_seed=5105,
        concurrency=1,
        timeout_seconds=180,
        max_api_calls_per_attempt=30,
        retry_policy="no automatic retries; retain every attempt",
        on_budget_exhaustion="stop; retain planned denominator",
    )
    manifest["calibration"]["report"] = {"filename": None, "sha256": None}
    manifest["pricing"] = {
        "source_and_date": None,
        "agent": dict.fromkeys(["input_per_million", "cached_input_per_million", "output_per_million"]),
        "judge": dict.fromkeys(["input_per_million", "cached_input_per_million", "output_per_million"]),
    }
    manifest["reporting"].update(
        metric_definitions_sha256=sha(ROOT / "eval/protocol/rubric.md"),
        error_and_exclusion_policy="retain all attempts; append adjudications separately",
        human_review_sampling_plan="review every failed/unscored answer and a frozen random sample of passes",
        uncertainty_method="paired bootstrap over question IDs, 2000 draws, seed 5105",
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("baseline", "improved", "output"):
        parser.add_argument("--" + arg, type=Path, required=True)
    a = parser.parse_args()
    capture(a.baseline, a.improved, a.output)
