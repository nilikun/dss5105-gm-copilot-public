"""Step 3 gate: comparison replies on the live model, three runs each.

Run from the repo root (about $0.03 per suite):
    uv run --project backend python eval/run_step3.py --output-dir eval/results/step3/live-v1
    uv run --project backend python eval/run_step3.py --suite production --output-dir eval/results/step3/independent-v1

`contracts` is D35 plus twelve variations from answer_contracts.json. `production` is the eleven cases written for a
different implementation of this route (step3_production.json), with references recomputed from the CSVs by
step3_reference.py, so neither the cases nor the references were shaped by the code they check here.

Replies are checked by the bounded answer-contract checker, which recomputes nothing from the agent's tools and
does not use the reply's `grounded` flag. The `production` suite also reports the independent scorer's hard checks.
Synthetic edges change a fresh in-memory database only; the `contracts` fixture questions name no stage or date, so
the live model is asked a concrete question about the changed day instead. Never reads held-out files. Every attempt,
raw reply and failure code is kept.
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "eval"))

from answer_contracts import check_answer  # noqa: E402
from independent_scoring import contract_rules, hard_score  # noqa: E402
from step3_reference import apply_overrides, reference, score  # noqa: E402

from app.agent.runtime import Agent  # noqa: E402
from app.clock import SimClock  # noqa: E402
from app.config import SETTINGS  # noqa: E402
from app.db.database import connect  # noqa: E402
from app.llm.openai_responses import OpenAIResponsesClient  # noqa: E402

CLOCK = "2026-04-01"
DAY = "2026-03-25"
CASE_IDS = ["D35", "P01", "P02", "P03", "P04", "P05", "P06", "P07", "P08", "P09", "P10", "P11", "P12"]
CONCRETE = "Compare assembly output on 2026-03-25 with its previous 20 working days."


def _window(db, value):
    db.execute("UPDATE production_log SET pieces_completed = ? WHERE stage = 'ASSEMBLY' AND date < ? "
               "AND strftime('%w', date) != '0'", (value, DAY))


def _day(db, value):
    db.execute("UPDATE production_log SET pieces_completed = ? WHERE stage = 'ASSEMBLY' AND date = ?", (value, DAY))


SYNTHETIC = {
    "P07": lambda db: _window(db, 0),
    "P08": lambda db: db.execute("DELETE FROM production_log WHERE stage = 'ASSEMBLY' AND date < ?", (DAY,)),
    "P09": lambda db: (_window(db, 100), _day(db, 120)),
    "P10": lambda db: (_window(db, 100), _day(db, 100)),
    "P11": lambda db: db.execute("DELETE FROM production_log WHERE stage = 'ASSEMBLY' AND date = ?", (DAY,)),
    "P12": lambda db: _day(db, 0),
}


def attempt_production(case: dict, run: int, llm) -> dict:
    db = connect()
    apply_overrides(db, case)
    reply = Agent(db, SimClock.at(CLOCK), llm).run(case["question"]).model_dump(mode="json")
    ref = reference(case, CLOCK)
    failures = score(ref, reply)
    item = {"expected_behavior": ref.get("expected_kind", "clarify"),
            "required_facts": contract_rules(ref) if ref.get("type") else []}
    hard = hard_score(item, reply, CLOCK)
    executed = db.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
    db.close()
    return {"id": case["id"], "run": run, "synthetic": bool(case.get("overrides")), "question": case["question"],
            "kind": reply["kind"], "text": " ".join(x for x in (reply["headline"], reply["details"]) if x),
            "failures": failures, "hard_pass": hard["pass"],
            "hard_issues": {c["criterion_id"]: c["issues"] for c in hard["criteria"] if c["issues"]},
            "reference": ref, "tools": [t["tool"] for t in reply["tool_calls"]], "latency_s": reply["latency_s"],
            "cost_usd": reply["cost_usd"], "llm_calls": reply["llm_calls"],
            "verifier_rejections": reply["verifier_rejections"], "unconfirmed_executions": executed}


def attempt(case: dict, run: int, llm) -> dict:
    db = connect()
    mutate = SYNTHETIC.get(case["id"])
    if mutate:
        mutate(db)
        db.commit()
    question = CONCRETE if mutate else case["question"]
    reply = Agent(db, SimClock.at(CLOCK), llm).run(question)
    text = " ".join(x for x in (reply.headline, reply.details) if x)
    failures = check_answer(case["reference"], {"kind": reply.kind, "text": text})
    executed = db.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
    db.close()
    return {"id": case["id"], "run": run, "synthetic": bool(mutate), "question": question, "kind": reply.kind,
            "text": text, "failures": failures, "tools": [t["tool"] for t in reply.tool_calls],
            "latency_s": reply.latency_s, "cost_usd": reply.cost_usd, "llm_calls": reply.llm_calls,
            "verifier_rejections": reply.verifier_rejections, "unconfirmed_executions": executed}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--suite", choices=["contracts", "production"], default="contracts")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    if a.suite == "production":
        run_one = attempt_production
        cases = json.loads((ROOT / "eval/fixtures/step3_production.json").read_text(encoding="utf-8"))["cases"]
    else:
        run_one = attempt
        fixtures = json.loads((ROOT / "eval/fixtures/answer_contracts.json").read_text(encoding="utf-8"))["cases"]
        cases = [c for c in fixtures if c["id"] in CASE_IDS]
    llm = OpenAIResponsesClient()
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        rows = list(pool.map(lambda job: run_one(job[0], job[1], llm),
                             [(c, r) for c in cases for r in range(a.runs)]))
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                            cwd=ROOT).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no", "backend", "eval"],
                           capture_output=True, text=True, cwd=ROOT).stdout.strip()
    passed = [r for r in rows if not r["failures"]]
    lat = sorted(r["latency_s"] for r in rows)
    summary = {"suite": a.suite, "hard_passed": sum(r.get("hard_pass", False) for r in rows),
               "commit": commit + ("-dirty" if dirty else ""), "model": llm.model, "effort": SETTINGS.reasoning_effort,
               "date": datetime.now(UTC).isoformat(timespec="seconds"), "clock": CLOCK, "attempts": len(rows),
               "passed": len(passed), "passed_source_backed": sum(not r["synthetic"] for r in passed),
               "attempts_source_backed": sum(not r["synthetic"] for r in rows),
               "routed_to_compare_to_normal": sum("compare_to_normal" in r["tools"] for r in rows),
               "unconfirmed_executions": sum(r["unconfirmed_executions"] for r in rows),
               "latency_p50_s": statistics.median(lat), "latency_p90_s": lat[round(0.9 * (len(lat) - 1))],
               "cost_usd": round(sum(r["cost_usd"] for r in rows), 5)}
    a.output_dir.mkdir(parents=True, exist_ok=True)
    with open(a.output_dir / "results.jsonl", "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    (a.output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    for r in rows:
        print(("PASS " if not r["failures"] else "FAIL ") + r["id"], r["run"], r["kind"], r["tools"],
              "" if not r["failures"] else f"{r['failures']} | {r['text'][:230]}",
              "" if r.get("hard_pass", True) else f"HARD {r['hard_issues']} | {r['text'][:230]}")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
