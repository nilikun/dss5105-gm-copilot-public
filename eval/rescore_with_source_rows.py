"""Post-hoc second score for the formal run: let the judge see the source rows a reply talks about.

The judge fails true statements that the reference package omits. In the formal run most failures were of this kind:
a correct working-day count or workshop ID flagged as unsupported. This script re-judges stored replies; it runs no
agent and changes no question, reply, or strict score. It is applied to both versions by one rule:

- only attempts whose hard checks passed and whose judge failed `unsupported_claims` or `clarity` are re-judged;
- every other result stands, so this can only move answers the rubric sends for review;
- the judge gets the same prompt, plus the CSV rows for the orders, workshops and stages named in the question and
  reply, and a fixed description of what the data and the product are.

This was decided after seeing the results, so it is reported beside the strict score, never instead of it.

    uv run --project backend --with pandas python eval/rescore_with_source_rows.py --results <run>/results.jsonl \
        --package <frozen>/heldout.yaml --output <run>/rescored.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "eval"))

from dotenv import load_dotenv  # noqa: E402
from independent_scoring import combine  # noqa: E402
from judge import evaluate  # noqa: E402

CONTEXT = {
    "source_file": "data/data_dictionary.md and the product description",
    "row_filter": "all",
    "calculation": "fixed description, the same for every item",
    "result": (
        "The factory is SweaterCo, closed on Sundays, with stages KNITTING, ASSEMBLY, WASHING, PACKING. Orders cover "
        "2026-01-01 to 2026-03-27 and the production log 2026-01-01 to 2026-03-31; the clock is 2026-04-01 07:00. "
        "The product shows actions as proposals with IDs such as A-1, which the manager confirms on a card in its web "
        "interface, and estimates come from its completion model (P50/P80 dates, fitted on completed orders) and "
        "workshop cards. Such a date is a labelled estimate. The rule for normal output: median of the previous 20 "
        "working days, robust sigma 1.4826 x MAD, briefing tier z < -1.75, interrupt tier z < -3 or z < -2 on 2 of the "
        "last 3 working days. This describes the system; it does not vouch for any figure in a reply."
    ),
    "workbook_cells_or_script": "eval/rescore_with_source_rows.py",
}


def source_rows(text: str) -> list[dict]:
    orders = pd.read_csv(ROOT / "data/orders.csv").fillna("")
    workshops = pd.read_csv(ROOT / "data/workshops.csv").fillna("")
    log = pd.read_csv(ROOT / "data/production_log.csv")
    named = sorted(set(re.findall(r"ORD-\d+", text)))
    customers = [c for c in orders.customer.unique() if c.lower() in text.lower()]
    products = [p for p in orders["product"].unique() if p.lower() in text.lower()]
    picked = orders[orders.order_id.isin(named) | ((orders.customer.isin(customers) | orders["product"].isin(products))
                                                   & (orders.status == "IN_PROGRESS"))]
    out = [CONTEXT]
    if len(picked):
        out.append({"source_file": "data/orders.csv", "row_filter": "orders named in the question or reply",
                    "calculation": "rows as recorded", "result": picked.to_dict("records"),
                    "workbook_cells_or_script": "eval/rescore_with_source_rows.py"})
    out.append({"source_file": "data/workshops.csv", "row_filter": "all", "calculation": "rows as recorded",
                "result": workshops.to_dict("records"), "workbook_cells_or_script": "eval/rescore_with_source_rows.py"})
    stages = [s for s in ("KNITTING", "ASSEMBLY", "WASHING", "PACKING") if s.lower() in text.lower()]
    if stages:
        rows = log[log.stage.isin(stages) & (log.date >= "2026-02-20")]
        out.append({"source_file": "data/production_log.csv", "row_filter": f"{stages}, from 2026-02-20",
                    "calculation": "rows as recorded", "result": rows.to_dict("records"),
                    "workbook_cells_or_script": "eval/rescore_with_source_rows.py"})
    return out


def needs_review(row: dict) -> bool:
    score = row.get("score") or {}
    hard = score.get("hard") or {}
    if not hard.get("pass") or score.get("judge_status") != "scored" or row.get("pass"):
        return False
    failed = {d["criterion_id"] for d in (score.get("judge") or {}).get("decisions", []) if not d["pass"]}
    return bool(failed & {"unsupported_claims", "clarity"})


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results", type=Path, required=True)
    ap.add_argument("--package", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--judge-model", default="gpt-6-astra")
    a = ap.parse_args()
    load_dotenv(ROOT / "backend/.env")
    load_dotenv(ROOT / "backend/.env.team")
    key = os.environ["OPENAI_API_KEY"]
    rows = [json.loads(x) for x in a.results.read_text(encoding="utf-8").splitlines() if x.strip()]
    items = {i["id"]: i for i in yaml.safe_load(a.package.read_text(encoding="utf-8"))["items"]}
    with a.output.open("x", encoding="utf-8") as out:
        for n, row in enumerate(rows):
            record = {"id": row["id"], "version": row["version"], "repeat": row["repeat"], "strict_pass": row["pass"],
                      "rejudged": False, "reviewed_pass": row["pass"], "judge": None}
            if needs_review(row):
                item = items[row["id"]]
                reply = row["reply"]
                reply_text = " ".join(str(reply.get(k) or "") for k in ("headline", "details"))
                context = " ".join(t["user"] for t in item.get("context_turns", []))
                enriched = {**item, "reference_evidence": item["reference_evidence"]
                            + source_rows(f"{item['question']} {context} {reply_text}")}
                judgment = evaluate(enriched, reply, api_key=key, model=a.judge_model, timeout=120)
                combined = combine(row["score"]["hard"], judgment)
                record.update(rejudged=True, reviewed_pass=combined["pass"], judge=judgment,
                              judge_status=combined["judge_status"])
                failed = [(d["criterion_id"], d["reason"][:90]) for d in judgment["decisions"] if not d["pass"]]
                print(n + 1, row["version"], row["id"], row["repeat"], "PASS" if combined["pass"] else f"FAIL {failed}",
                      judgment["error"] or "", flush=True)
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            out.flush()


if __name__ == "__main__":
    main()
