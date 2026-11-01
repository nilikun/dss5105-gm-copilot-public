"""Independent public production references: stdlib CSV/calendar, no agent/tool imports."""

from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path
from statistics import mean, median

from answer_contracts import check_answer

ROOT = Path(__file__).resolve().parents[1]


def reference(case, as_of):
    args = case["tool_args"]
    if not args.get("stage") or not args.get("date_from"):
        return {"behavior": "clarify", "as_of": as_of}
    start = date.fromisoformat(args["date_from"])
    end = date.fromisoformat(args.get("date_to") or args["date_from"])
    with (ROOT / "data/production_log.csv").open(encoding="utf-8") as stream:
        values = {
            r["date"]: float(r["pieces_completed"]) for r in csv.DictReader(stream) if r["stage"] == args["stage"]
        }
    for change in case.get("overrides", []):
        if change["stage"] != args["stage"]:
            continue
        for day in list(values):
            if change["start"] <= day <= change["end"]:
                if change["value"] is None:
                    del values[day]
                else:
                    values[day] = change["value"]
    days = [
        start + timedelta(days=i)
        for i in range((end - start).days + 1)
        if (start + timedelta(days=i)).isoweekday() != 7
    ]
    history = []
    cursor = start
    while len(history) < 20:
        cursor -= timedelta(days=1)
        if cursor.isoweekday() != 7:
            history.insert(0, cursor)
    actual = mean(values[d.isoformat()] for d in days) if days and all(d.isoformat() in values for d in days) else None
    baseline = median(values[d.isoformat()] for d in history) if all(d.isoformat() in values for d in history) else None
    return {
        "type": "production",
        "as_of": as_of,
        "stage": args["stage"],
        "start": start.isoformat(),
        "end": end.isoformat(),
        "statistic": "daily" if start == end else "mean",
        "actual": actual,
        "baseline": baseline,
        "baseline_start": history[0].isoformat(),
        "baseline_end": history[-1].isoformat(),
        "baseline_days": 20,
        "cause": "unknown",
        "expected_kind": "refuse" if args.get("explain_cause") else "answer",
    }


def score(ref, reply):
    if ref.get("behavior") == "clarify":
        return [] if reply.get("kind") == "clarify" and reply.get("clarification_question") else ["clarification"]
    text = "\n".join([reply.get("headline", ""), reply.get("details") or ""] + reply.get("followups", []))
    return check_answer(ref, {"kind": reply.get("kind"), "text": text.replace("**", "").replace("`", "")})


def apply_overrides(db, case):
    """Runner-only synthetic mutations; reference() above uses original CSVs independently."""
    for item in case.get("overrides", []):
        params = (item["stage"], item["start"], item["end"])
        if item["value"] is None:
            db.execute("DELETE FROM production_log WHERE stage = ? AND date BETWEEN ? AND ?", params)
        else:
            db.execute(
                "UPDATE production_log SET pieces_completed = ? WHERE stage = ? AND date BETWEEN ? AND ?",
                (item["value"], *params),
            )
    db.commit()
