"""Development check: the independent judge and hard checks on replies the live system really produced.

The reviewer packet holds hand-varied answers. This asks a different question: does the judge accept what the system
actually writes, or does it reject true statements its reference package does not mention?

    uv run --project backend python eval/judge_real_replies.py --replies eval/results/step3/live-v2/results.jsonl \
        --output eval/results/step4/real-replies-v1.jsonl

One reply per case (first attempt). About $0.03 per reply at the planning rates. Development cases only: this is not
human calibration and never reads held-out files.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "eval"))

from dotenv import load_dotenv  # noqa: E402
from independent_scoring import combine, contract_rules, hard_score  # noqa: E402
from judge import evaluate  # noqa: E402

CLOCK = "2026-04-01"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--replies", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--model", default="gpt-6-astra")
    a = ap.parse_args()
    load_dotenv(ROOT / "backend/.env")
    load_dotenv(ROOT / "backend/.env.team")
    fixtures = json.loads((ROOT / "eval/fixtures/answer_contracts.json").read_text(encoding="utf-8"))["cases"]
    cases = {c["id"]: c for c in fixtures}
    rows = [json.loads(line) for line in a.replies.read_text(encoding="utf-8").splitlines() if line.strip()]
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("x", encoding="utf-8") as out:
        for row in (r for r in rows if r["run"] == 0):
            case = cases[row["id"]]
            ref = case["reference"]
            item = {"question": row["question"], "required_facts": contract_rules(ref),
                    "expected_behavior": ref.get("expected_kind", "answer"),
                    "reference_answer": case["accepted"][0]["text"], "reference_evidence": [ref],
                    "prohibited_claims": []}
            reply = {"kind": row["kind"], "text": row["text"]}
            hard = hard_score(item, reply, CLOCK)
            judgment = evaluate(item, reply, api_key=os.environ["OPENAI_API_KEY"], model=a.model)
            result = combine(hard, judgment)
            failed = [c for c in judgment["decisions"] if not c["pass"]]
            out.write(json.dumps({"id": row["id"], "text": row["text"], "hard_pass": hard["pass"],
                                  "pass": result["pass"], "judge": judgment}, ensure_ascii=False) + "\n")
            out.flush()
            print(row["id"], "hard", hard["pass"], "judge", judgment["valid"], "final", result["pass"],
                  [(c["criterion_id"], c["reason"][:170]) for c in failed], judgment["error"] or "", flush=True)


if __name__ == "__main__":
    main()
