"""Validation and release gates for external, independently authored evaluation packages."""

from __future__ import annotations

import hashlib
import json
import platform
import re
import subprocess
from collections import Counter
from datetime import datetime
from importlib.metadata import version
from pathlib import Path

import yaml
from independent_scoring import SEMANTIC, validate_rule

ROOT = Path(__file__).resolve().parents[1]
COVERAGE = {
    "lookup": 3,
    "aggregation": 2,
    "judgement": 2,
    "tracing": 2,
    "discovery": 1,
    "feasibility": 3,
    "action": 3,
    "ambiguous": 2,
    "unanswerable": 2,
}
SCORING_FILES = [
    "eval/answer_contracts.py",
    "eval/independent_scoring.py",
    "eval/judge.py",
    "eval/frozen_protocol.py",
    "eval/calibrate.py",
    "eval/frozen_worker.py",
    "eval/run_frozen.py",
    "eval/protocol/judge_prompt.md",
    "eval/protocol/rubric.md",
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_package(package):
    require(package.get("version") == 2 and package.get("status") == "frozen", "Package must be filled and frozen v2")
    for key in ("author", "written_on", "exposure_declaration", "as_of"):
        require(bool(package.get(key)), f"Missing {key}")
    datetime.fromisoformat(package["as_of"])
    items = package.get("items", [])
    require(len(items) == 20 and len({i["id"] for i in items}) == 20, "Exactly 20 unique items required")
    require(Counter(i["category"] for i in items) == COVERAGE, "Category coverage differs from protocol")
    for item in items:
        for key in ("question", "reference_answer", "verification", "reference_evidence", "required_facts"):
            require(bool(item.get(key)), f"{item['id']}: blank {key}")
        require(
            item["expected_behavior"] in {"answer", "clarify", "refuse", "estimate", "propose_action", "reject_action"},
            "Unknown expected behavior",
        )
        for turn in item.get("context_turns", []):
            require(set(turn) == {"user"} and bool(turn["user"]), "Context must contain user turns only")
        ids = [f["criterion_id"] for f in item["required_facts"]]
        require(len(set(ids)) == len(ids) and not set(ids).intersection(SEMANTIC), "Duplicate/reserved criterion")
        for fact in item["required_facts"]:
            validate_rule(fact)
            for key in ("unit", "calculation"):
                require(bool(fact.get(key)), f"Fact requires {key}; use not_applicable where appropriate")
        for ev in item["reference_evidence"]:
            for key in ("source_file", "row_filter", "calculation", "result", "workbook_cells_or_script"):
                require(ev.get(key) not in (None, ""), f"Evidence requires {key}")
        for pattern in item.get("prohibited_claims", []):
            re.compile(pattern)
    return package


def checked_file(base, entry):
    path = (base / entry["filename"]).resolve()
    require(path.is_relative_to(base.resolve()), "Package file escapes custody directory")
    require(sha(path) == entry["sha256"], f"Hash mismatch: {path.name}")
    return path


def check_checkout(root, commit, prompts, data, lock):
    actual = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(["git", "-C", str(root), "status", "--porcelain"], text=True).strip()
    require(
        actual == commit and re.fullmatch("[0-9a-f]{40}", commit) and not dirty,
        "Formal evaluation requires the exact clean committed checkout",
    )
    require(set(prompts) == {p.name for p in (root / "backend/prompts").glob("*.md")}, "Incomplete prompt hashes")
    for name, digest in prompts.items():
        require(sha(root / "backend/prompts" / name) == digest, "Prompt mismatch")
    require(sha(root / "backend/uv.lock") == lock, "Dependency lock mismatch")
    require(
        {e["path"] for e in data} == {"data/orders.csv", "data/production_log.csv", "data/workshops.csv"},
        "All three source data files must be frozen",
    )
    for entry in data:
        require(sha(root / entry["path"]) == entry["sha256"], "Source data differs between frozen versions")


def load_released(freeze_path, baseline, improved):
    """Do not parse questions until code, rubric, settings, data and human-calibration gates pass."""
    freeze_path = Path(freeze_path).resolve()
    base = freeze_path.parent
    require(not base.is_relative_to(ROOT), "Hidden package must be outside the development checkout")
    manifest = json.loads(freeze_path.read_text(encoding="utf-8"))
    require(manifest.get("status") == "frozen", "Blank/provisional manifest is not releasable")
    require(manifest.get("authored_before_outputs") is True, "Independence declaration is required")
    for key in ("author", "custodian", "exposure_declaration", "frozen_at_with_timezone"):
        require(bool(manifest.get(key)), f"Missing {key}")
    frozen_at = datetime.fromisoformat(manifest["frozen_at_with_timezone"])
    release = manifest["release"]
    require(
        release["scorer_and_settings_frozen_before_question_release"] is True and release.get("operator"),
        "Release not authorized by custodian",
    )
    released_at = datetime.fromisoformat(release["released_at"])
    require(frozen_at.tzinfo and released_at.tzinfo and frozen_at <= released_at, "Invalid freeze/release timestamps")
    versions = manifest["versions"]
    require(versions["python_version"] == platform.python_version(), "Python runtime differs from freeze")
    require(
        versions["sdk_versions"] == {k: version(k) for k in ("openai", "pydantic", "pandas", "PyYAML")},
        "Installed dependencies differ from freeze",
    )
    scorer_commit = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    require(versions["scorer_commit"] == scorer_commit, "Scorer commit differs from freeze")
    expected_hashes = {p: sha(ROOT / p) for p in SCORING_FILES}
    require(versions["scoring_files_sha256"] == expected_hashes, "Scoring implementation changed after freeze")
    require(versions["rubric_sha256"] == sha(ROOT / "eval/protocol/rubric.md"), "Rubric changed")
    require(manifest["judge_settings"]["prompt_sha256"] == sha(ROOT / "eval/protocol/judge_prompt.md"), "Judge changed")
    cal = manifest["calibration"]
    require(cal.get("accepted_before_release") is True, "Human calibration not accepted")
    report_path = checked_file(base, cal["report"])
    report = json.loads(report_path.read_text(encoding="utf-8"))
    require(
        report["accepted"] is True and report["human_reviewers"] and report["sample_count"] >= 20,
        "Calibration report is not accepted human calibration",
    )
    require(report["scoring_files_sha256"] == expected_hashes, "Calibration used different scoring code")
    require(
        report["judge_settings"] == {k: manifest["judge_settings"][k] for k in report["judge_settings"]},
        "Calibration used different judge settings",
    )
    require(datetime.fromisoformat(report["completed_utc"]) <= frozen_at, "Calibration must precede freeze")
    require(bool(manifest["independent_calculations"]), "Independent calculation files required")
    for entry in manifest["independent_calculations"]:
        require(entry["method"] and entry.get("checked_by"), "Independent calculation provenance missing")
        checked_file(base, entry)
    for label, root in [("baseline", baseline), ("improved", improved)]:
        check_checkout(
            Path(root),
            versions[f"{label}_commit"],
            versions[f"{label}_prompts_sha256"],
            manifest["data"]["files"],
            versions["dependency_lock_sha256"],
        )
    execution = manifest["execution"]
    require(
        execution["repetitions_per_item_per_version"] >= 1 and execution["concurrency"] == 1,
        "Positive repetitions and serial randomized execution required",
    )
    require(execution["fresh_database_per_item"] and execution["reset_clock_per_item"], "State reset required")
    require(execution["retry_policy"] == "no automatic retries; retain every attempt", "Unsupported retry policy")
    require(
        execution["timeout_seconds"] > 0 and execution["max_api_calls_per_attempt"] > 0,
        "Explicit timeout and API call cap required",
    )
    require(execution["budget_usd"] > 0 and manifest["pricing"]["source_and_date"], "Frozen budget/rates required")
    require(manifest["agent_settings"]["critic_enabled"] is False, "This comparison protocol freezes critic off")
    require(
        manifest["agent_settings"]["max_tool_steps"] == 6 and manifest["agent_settings"]["repair_limit"] == 1,
        "Agent loop differs from protocol",
    )
    require(manifest["judge_settings"]["max_retries"] == 0, "Judge retries must be disabled")
    for settings in (manifest["agent_settings"], manifest["judge_settings"]):
        require(
            bool(settings["model"]) and bool(settings["reasoning_effort"]) and settings["max_output_tokens"] > 0,
            "Effective model settings missing",
        )
    for rates in (manifest["pricing"]["agent"], manifest["pricing"]["judge"]):
        require(
            all(
                isinstance(rates[k], (int, float)) and 0 <= rates[k] < 10000
                for k in ("input_per_million", "cached_input_per_million", "output_per_million")
            ),
            "Invalid frozen prices",
        )
    questions = checked_file(base, manifest["questions_and_references"])
    package = validate_package(yaml.safe_load(questions.read_text(encoding="utf-8")))
    require(package["as_of"] == manifest["clock"]["simulated_now"], "Clock mismatch")
    require(package["author"] == manifest["author"], "Author mismatch")
    return manifest, package
