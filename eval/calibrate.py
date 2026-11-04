"""Build a blinded human packet, record judge predictions, then compare supplied human labels."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from frozen_protocol import ROOT, SCORING_FILES, require, sha
from independent_scoring import SEMANTIC, combine, contract_rules, hard_score
from judge import evaluate


def rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def make_packet(out):
    out.mkdir(parents=True, exist_ok=False)
    fixtures = json.loads((ROOT / "eval/fixtures/answer_contracts.json").read_text(encoding="utf-8"))["cases"]
    chosen = [next(c for c in fixtures if c["id"] == key) for key in ("D02", "D35")]
    examples = []
    for case in chosen:
        selected = [0, 1, 2, 3, 4] if case["id"] == "D02" else [2, 4, 7, 8, 11]
        good = case["accepted"][0]
        variants = [
            good | {"text": good["text"].replace("2026-03-16", "16 March 2026")},
            good | {"text": good["text"].replace("Due ", "Deadline: ")},
            good | {"text": good["text"].replace("2026-03-25", "March 25, 2026")},
        ]
        if case["id"] == "D35":
            variants = [
                good | {"text": good["text"].replace("2026-03-25", "March 25, 2026")},
                good | {"text": good["text"].replace("48.6% below", "-48.6% versus")},
                good | {"text": good["text"].replace("The cause is unknown from these data.", "No cause is recorded.")},
            ]
        else:
            variants[2] = good | {"text": good["text"].replace("16 days overdue", "overdue by 16 days")}
        candidates = case["accepted"][:2] + variants + [case["rejected"][i]["answer"] for i in selected]
        require(len(candidates) == 10, "Expected 10 public candidates per target")
        facts = contract_rules(case["reference"])
        for f in facts:
            f.update(unit="see reference", calculation="See independent CSV reference and reference evidence")
        item = {
            "id": case["id"],
            "question": case["question"],
            "required_facts": facts,
            "expected_behavior": case["reference"].get("expected_kind", "answer"),
            "reference_answer": case["accepted"][0]["text"],
            "reference_evidence": [case["reference"]],
            "prohibited_claims": [
                r"\b(?:because of|caused by|due to)\s+(?:a |the )?(?:machine|staff|material)",
                r"\b(?:machine breakdown|staff shortage|material shortage) caused",
            ],
        }
        for candidate in candidates:
            examples.append(
                {
                    "id": f"C{len(examples) + 1:02d}",
                    "item": item,
                    "candidate": {"kind": candidate["kind"], "text": candidate["text"]},
                }
            )
    # Mix examples deterministically without attaching expected good/bad labels to the blind packet.
    import random

    random.Random(5105).shuffle(examples)
    (out / "candidates.jsonl").write_text("".join(json.dumps(e) + "\n" for e in examples))
    labels = [
        {
            "id": e["id"],
            "reviewer": "",
            "reviewed_at": "",
            "decisions": [
                {"criterion_id": f, "pass": None, "excerpt": "", "reason": ""}
                for f in [x["criterion_id"] for x in e["item"]["required_facts"]] + list(SEMANTIC)
            ],
        }
        for e in examples
    ]
    (out / "human_labels.template.jsonl").write_text("".join(json.dumps(e) + "\n" for e in labels))
    (out / "README.md").write_text(
        "# Human reviewer packet — development only\n\nReview all 20 candidates against the supplied references. "
        "Fill every criterion with true/false, a short literal excerpt (empty for omissions), and your reason. "
        "Add your name and review time. Do not view judge predictions or development acceptance labels first. "
        "A second reviewer should adjudicate disagreements where possible. These are public development "
        "answers, never held-out questions. Do not let the held-out author read this packet.\n\n"
        "Return a copy named human_labels.jsonl outside the development checkout; preserve original candidates.\n",
        encoding="utf-8",
    )


def compare(packet, labels, judgments, out, resolutions=None):
    """`resolutions`: recorded decisions on hard-check disagreements. A disagreement without a record still blocks."""
    resolved = {(r["id"], r["criterion_id"]): r for r in resolutions or []}
    examples, human, machine = rows(packet), rows(labels), rows(judgments)
    require(len(examples) >= 20, "At least 20 human-labelled examples required")
    expected = {e["id"] for e in examples}
    require(
        len(expected) == len(examples) and {r["id"] for r in human} == expected and len(human) == len(expected),
        "Missing/duplicate human labels",
    )
    require({r["id"] for r in machine} == expected and len(machine) == len(expected), "Incomplete judge run")
    human = {r["id"]: r for r in human}
    machine = {r["id"]: r for r in machine}
    counts, disagreements, hard_disagreements, reviewers = Counter(), [], [], set()
    for example in examples:
        h, m = human[example["id"]], machine[example["id"]]
        require(bool(h.get("reviewer")) and bool(h.get("reviewed_at")), "Human identity/date required")
        reviewers.add(h["reviewer"])
        require(m["judge"]["valid"], "Invalid judge output requires resolution before calibration")
        require(m.get("packet_sha256") == sha(packet), "Judge predictions belong to another packet")
        require(
            m.get("scoring_files_sha256") == {p: sha(ROOT / p) for p in SCORING_FILES},
            "Scoring changed since these judge predictions; rerun development calibration",
        )
        require(
            m["judge"]["settings"] == machine[examples[0]["id"]]["judge"]["settings"],
            "Mixed judge settings cannot be calibrated together",
        )
        datetime.fromisoformat(h["reviewed_at"])
        wanted = [f["criterion_id"] for f in example["item"]["required_facts"]] + list(SEMANTIC)
        require(sorted(c["criterion_id"] for c in h["decisions"]) == sorted(wanted), "Incomplete human criteria")
        predicted = {c["criterion_id"]: c["pass"] for c in m["judge"]["decisions"]}
        for c in h["decisions"]:
            require(type(c.get("pass")) is bool and c.get("reason"), "Unfilled human label")
            label, prediction = c["pass"], predicted[c["criterion_id"]]
            hard_decision = next(
                (d["pass"] for d in m["hard"]["criteria"] if d["criterion_id"] == c["criterion_id"]), None
            )
            if hard_decision is not None and hard_decision != label:
                hard_disagreements.append(
                    {"id": example["id"], "criterion_id": c["criterion_id"], "human": label, "hard": hard_decision}
                )
            counts[f"human_{label}_judge_{prediction}"] += 1
            if label != prediction:
                disagreements.append(
                    {
                        "id": example["id"],
                        "criterion_id": c["criterion_id"],
                        "human": label,
                        "judge": prediction,
                        "human_reason": c["reason"],
                    }
                )
    total = sum(counts.values())
    agreement = (counts["human_True_judge_True"] + counts["human_False_judge_False"]) / total
    # Prospective acceptance: >=90% criterion agreement, both positive and negative labels,
    # and no false-positive critical/unsupported-claim decisions on this small calibration set.
    critical_false_passes = [
        d for d in disagreements if not d["human"] and d["judge"] and d["criterion_id"] not in ("clarity", "relevance")
    ]
    both_labels = all(any(k.startswith(f"human_{value}_") and n for k, n in counts.items()) for value in (True, False))
    for d in hard_disagreements:
        d["resolution"] = resolved.get((d["id"], d["criterion_id"]))
    unresolved = [d for d in hard_disagreements if not d["resolution"]]
    report = {
        "scope": "human calibration on public development answers",
        "sample_count": len(examples),
        "human_reviewers": sorted(reviewers),
        "agreement": agreement,
        "confusion_counts": dict(counts),
        "disagreements": disagreements,
        "hard_disagreements": hard_disagreements,
        "critical_false_passes": critical_false_passes,
        "unresolved_hard_disagreements": unresolved,
        "accepted": agreement >= 0.9 and not critical_false_passes and both_labels and not unresolved,
        "acceptance_threshold": (
            ">=0.90 criterion agreement; zero critical false passes; "
            "both labels present; no unresolved hard disagreements"
        ),
        "packet_sha256": sha(packet),
        "labels_sha256": sha(labels),
        "judgments_sha256": sha(judgments),
        "scoring_files_sha256": {p: sha(ROOT / p) for p in SCORING_FILES},
        "judge_settings": machine[examples[0]["id"]]["judge"]["settings"],
        "completed_utc": datetime.now(UTC).isoformat(),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("packet")
    p.add_argument("--output-dir", type=Path, required=True)
    p = sub.add_parser("judge")
    p.add_argument("--packet", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--model", default="gpt-6-astra")
    p.add_argument("--effort", default="low")
    p.add_argument("--max-calls", type=int, default=20)
    p = sub.add_parser("compare")
    for arg in ("packet", "labels", "judgments", "output"):
        p.add_argument("--" + arg, type=Path, required=True)
    p.add_argument("--adjudication", type=Path, help="JSON holding hard_check_resolutions")
    args = parser.parse_args()
    if args.command == "packet":
        make_packet(args.output_dir)
    elif args.command == "compare":
        records = json.loads(args.adjudication.read_text(encoding="utf-8")) if args.adjudication else {}
        compare(args.packet, args.labels, args.judgments, args.output, records.get("hard_check_resolutions"))
    else:
        import os

        from dotenv import load_dotenv

        load_dotenv(ROOT / "backend/.env")
        load_dotenv(ROOT / "backend/.env.team")
        key = os.environ.get("OPENAI_API_KEY")
        require(bool(key), "OPENAI_API_KEY is required")
        examples = rows(args.packet)
        require(len(examples) <= args.max_calls, "Call cap is below packet size; no partial calibration")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        frozen_hashes = {p: sha(ROOT / p) for p in SCORING_FILES}
        with args.output.open("x", encoding="utf-8") as stream:
            for e in examples:
                judgment = evaluate(e["item"], e["candidate"], api_key=key, model=args.model, effort=args.effort)
                hard = hard_score(e["item"], e["candidate"], "2026-04-01")
                stream.write(
                    json.dumps(
                        {
                            "id": e["id"],
                            "judge": judgment,
                            "hard": hard,
                            "combined": combine(hard, judgment),
                            "packet_sha256": sha(args.packet),
                            "scoring_files_sha256": frozen_hashes,
                        }
                    )
                    + "\n"
                )
                stream.flush()
                print(e["id"], "scored" if judgment["valid"] else "ERROR", flush=True)
                if not judgment["valid"] and judgment["usage"] is None:
                    break


if __name__ == "__main__":
    main()
