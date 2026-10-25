"""Record/verify the pre-change source and data snapshot. Offline; no credentials read.

python eval/record_step1_baseline.py --write  # once, before runtime changes
python eval/record_step1_baseline.py --check  # verifies frozen commit AND current data
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "eval/baselines/step1.json"


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=ROOT)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def selected(path: str) -> bool:
    return (path.startswith(("backend/app/", "backend/prompts/", "data/"))
            or path in {"backend/pyproject.toml", "backend/uv.lock", "eval/run.py", "eval/scoring.py",
                        "eval/questions_dev.yaml", "eval/redteam.yaml", "eval/ground_truth/dev_truth.py"})


def snapshot(commit: str) -> dict:
    files = {}
    for path in git("ls-tree", "-r", "--name-only", commit).decode().splitlines():
        if not selected(path):
            continue
        content = git("show", f"{commit}:{path}")
        entry = {"sha256": digest(content), "bytes": len(content)}
        if path.endswith(".csv"):
            records = list(csv.DictReader(io.StringIO(content.decode())))
            entry["rows"] = len(records)
            if records and "date" in records[0]:
                entry["date_range"] = [min(row["date"] for row in records), max(row["date"] for row in records)]
        files[path] = entry
    data_hashes = {path: value["sha256"] for path, value in files.items() if path.startswith("data/")}
    return {"files": files, "data_snapshot_sha256": digest(json.dumps(data_hashes, sort_keys=True).encode())}


def has_commit(commit: str) -> bool:
    """True when the commit is in this clone's history (not in the single-commit public export)."""
    probe = subprocess.run(["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=ROOT, capture_output=True)
    return probe.returncode == 0


def verify(manifest: dict, history: bool = True) -> list[str]:
    """Check the manifest against the baseline commit (history=True) and the current data files (always)."""
    errors = []
    if history:
        baseline = snapshot(manifest["baseline_commit"])
        for key in ("files", "data_snapshot_sha256"):
            if baseline[key] != manifest[key]:
                errors.append(f"baseline {key} differs from the recorded commit")
    for path, entry in manifest["files"].items():
        # Runtime changes are expected in Steps 2/3; source must still resolve at
        # the baseline commit. Data must stay identical for the paired evaluation.
        if path.startswith("data/"):
            current = ROOT / path
            if not current.exists() or digest(current.read_bytes()) != entry["sha256"]:
                errors.append(f"data changed: {path}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write:
        if TARGET.exists():
            parser.error("baseline already exists; do not silently replace the frozen baseline")
        commit = git("rev-parse", "HEAD").decode().strip()
        state = snapshot(commit)
        for path, entry in state["files"].items():
            if digest((ROOT / path).read_bytes()) != entry["sha256"]:
                parser.error(f"baseline source/data has uncommitted changes: {path}")
        manifest = {
            "schema_version": 1, "recorded_on": "2026-10-20",
            "baseline_commit": commit, "baseline_branch": "main",
            "repository": "https://github.com/nilikun/dss5105-gm-copilot",
            "simulated_now": "2026-04-01T07:00:00",
            "clock_convention": "timezone-naive factory simulation; never substitute wall-clock time",
            "historical_final_run_commit": "6714fe0",
            "baseline_evaluation_status": "not run; historical metrics are not measurements of this baseline",
            "source_defaults_only": {"model": "gpt-5.6-luna", "reasoning_effort": "low", "critic": False,
                                     "workers": 3},
            "effective_model_settings": None,
            "settings_note": "No API calls; freeze effective baseline/improved/judge settings before Step 5. "
                             "Engineering-model estimates are not evaluation model settings. No .env files recorded.",
            "heldout_questions_sha256": None,
            "heldout_note": "Independent author supplies hash after private freeze; no hidden content read.",
            **state,
        }
        TARGET.parent.mkdir(parents=True, exist_ok=True)
        TARGET.write_text(json.dumps(manifest, indent=2) + "\n")
        print(f"Recorded {commit}: {len(state['files'])} source/data files")
    else:
        errors = verify(json.loads(TARGET.read_text(encoding="utf-8")))
        if errors:
            raise SystemExit("\n".join(errors))
        print("PASS: baseline commit hashes and current data snapshot match")


if __name__ == "__main__":
    main()
