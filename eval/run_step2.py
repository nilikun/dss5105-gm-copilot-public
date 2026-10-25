"""Focused PUBLIC development run; never reads held-out files or uses the agent's grounding flag to score.

Run from the repo root: backend/.venv/bin/python eval/run_step2.py --output-dir eval/results/step2/live-v1
Use --backend-root /path/to/baseline/backend to compare an unchanged code snapshot with the same cases/checks.
All attempts, API-reported tokens, raw replies, traces, and independent references are preserved.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "eval"))
from step2_reference import reference, score  # noqa: E402


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def run(args):
    backend = args.backend_root.resolve()
    sys.path.insert(0, str(backend))
    from app.agent.runtime import Agent
    from app.clock import SimClock
    from app.config import SETTINGS
    from app.db.database import connect
    from app.llm import budget
    from app.llm.base import BudgetExceeded
    from app.llm.openai_responses import OpenAIResponsesClient
    from app.observability.trace import load_turn

    fixture = ROOT / "eval" / "fixtures" / "step2_order_status.json"
    suite = json.loads(fixture.read_text(encoding="utf-8"))
    cases = [c for c in suite["cases"] if not args.only or c["id"] in args.only.split(",")]
    if not cases:
        raise ValueError("No matching development cases")
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=False)  # never replace an earlier run
    source_paths = sorted([*(backend / "app").rglob("*.py"), *backend.glob("prompts/*.md")])
    data_paths = sorted((backend.parent / "data").glob("*.csv"))
    metadata = {
        "started_utc": datetime.now(UTC).isoformat(), "scope": suite["scope"], "clock": suite["clock"],
        "code_commit": git(backend.parent, "rev-parse", "HEAD"),
        "code_dirty": bool(git(backend.parent, "status", "--porcelain")),
        "backend_source_sha256": {str(p.relative_to(backend)): sha(p) for p in source_paths},
        "data_sha256": {p.name: sha(p) for p in data_paths},
        "fixture_sha256": sha(fixture), "reference_sha256": sha(ROOT / "eval" / "step2_reference.py"),
        "checker_sha256": sha(ROOT / "eval" / "answer_contracts.py"), "runner_sha256": sha(Path(__file__)),
        "model": args.model or SETTINGS.llm_model, "reasoning_effort": SETTINGS.reasoning_effort,
        "critic": False, "repetitions": args.repetitions, "cases": [c["id"] for c in cases],
        "usage_note": "Provider-reported response usage; output includes reasoning, do not add it again.",
        "cost_note": "Repository-configured cost estimate, not a verified bill; failures may have unreported usage.",
        "configured_usd_per_million": {"input": SETTINGS.price_input_per_m,
                                       "cached_input": SETTINGS.price_cached_input_per_m,
                                       "output": SETTINGS.price_output_per_m},
        "max_cost_estimate_usd": args.max_cost,
    }
    # Independent reference data must be the same CSV bytes as the evaluated backend's data.
    assert all(sha(ROOT / "data" / p.name) == sha(p) for p in data_paths)
    (out / "manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")
    spent = 0.0
    results = []

    for repeat in range(1, args.repetitions + 1):
        for case in cases:
            db = connect(backend.parent / "data")
            for field, value in case.get("override", {}).items():
                if field not in {"due_date", "current_stage", "completed_date"}:
                    raise ValueError("Unsupported synthetic override")
                db.execute(f"UPDATE orders SET {field} = ? WHERE order_id = ?", (value, case["order_id"]))
            db.commit()
            calls = []

            class Metered:
                def __init__(self, call_records):
                    self.calls = call_records
                    self.inner = OpenAIResponsesClient(model=args.model, timeout=45)
                    self.model = self.inner.model

                def create(self, **kwargs):
                    nonlocal spent
                    if spent >= args.max_cost:
                        raise BudgetExceeded("Step 2 suite cost cap reached")
                    response = self.inner.create(**kwargs)
                    usage = response.usage
                    cost = budget.cost_usd(usage)
                    spent += cost
                    self.calls.append({"model": response.model, "input_tokens": usage.input_tokens,
                                  "cached_tokens": usage.cached_tokens, "output_tokens": usage.output_tokens,
                                  "reasoning_tokens": usage.reasoning_tokens, "latency_ms": response.latency_ms,
                                  "cost_estimate_usd": cost})
                    return response

            start = time.perf_counter()
            context_reply, reply, error = None, {}, None
            try:
                agent = Agent(db, SimClock.at(suite["clock"]), Metered(calls))
                cid = None
                if case.get("context"):
                    context_reply = agent.run(case["context"]).model_dump(mode="json")
                    cid = context_reply["conversation_id"]
                reply = agent.run(case["question"], cid).model_dump(mode="json")
            except Exception as exc:
                # Preserve useful error diagnostics without ever writing credentials.
                message = str(exc)
                if SETTINGS.openai_api_key:
                    message = message.replace(SETTINGS.openai_api_key, "[redacted]")
                error = {"type": type(exc).__name__, "message": message[:1000]}
            ref = reference(case, suite["clock"])
            errors = score(ref, reply) if reply else ["execution_error"]
            executed = db.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
            if executed:
                errors.append("unconfirmed_action")
            if reply and (len(reply["headline"]) > 420 or len(reply["headline"].splitlines()) > 3):
                errors.append("headline_length")
            row = {"id": case["id"], "repeat": repeat, "question": case["question"],
                   "synthetic": case.get("synthetic"), "override": case.get("override", {}), "reference": ref,
                   "reply": reply, "context_reply": context_reply, "errors": errors, "error": error,
                   "pass": not errors and error is None, "api_calls": calls,
                   "wall_seconds": round(time.perf_counter() - start, 3),
                   "traces": [load_turn(db, turn[0]) for turn in db.execute(
                       "SELECT DISTINCT turn_id FROM traces ORDER BY id")], "unconfirmed_actions": executed}
            results.append(row)
            with (out / "results.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(f"{case['id']} run {repeat}: {'PASS' if row['pass'] else 'FAIL ' + ','.join(errors)} "
                  f"({row['wall_seconds']:.1f}s, {len(calls)} API calls)", flush=True)
            db.close()
            if error and not calls:
                # Do not repeatedly send calls after a credentials/network/model/budget failure.
                break
        if results[-1]["error"] and not results[-1]["api_calls"]:
            break
    calls = [call for row in results for call in row["api_calls"]]
    latencies = sorted(row["wall_seconds"] for row in results)
    summary = {
        "planned": len(cases) * args.repetitions, "attempted": len(results),
        "passed": sum(row["pass"] for row in results),
        "by_case": {c["id"]: {"passed": sum(r["pass"] for r in results if r["id"] == c["id"]),
                              "attempted": sum(r["id"] == c["id"] for r in results)} for c in cases},
        "failures": [{"id": r["id"], "repeat": r["repeat"], "errors": r["errors"], "error": r["error"]}
                     for r in results if not r["pass"]],
        "api_calls": len(calls),
        "usage": {key: sum(c[key] for c in calls) for key in (
            "input_tokens", "cached_tokens", "output_tokens", "reasoning_tokens")},
        "cost_estimate_usd": spent, "p50_seconds": statistics.median(latencies),
        "p90_seconds": latencies[round(.9 * (len(latencies) - 1))],
        "unconfirmed_actions": sum(r["unconfirmed_actions"] for r in results),
        "completed_utc": datetime.now(UTC).isoformat(),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: summary[k] for k in ("planned", "attempted", "passed", "api_calls", "usage")}), flush=True)
    return 0 if summary["passed"] == summary["planned"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--backend-root", type=Path, default=ROOT / "backend")
    parser.add_argument("--model", default=None)
    parser.add_argument("--only", default=None)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--max-cost", type=float, default=1.0)
    args = parser.parse_args()
    if args.repetitions < 1 or args.max_cost <= 0:
        parser.error("repetitions and max-cost must be positive")
    raise SystemExit(run(args))
