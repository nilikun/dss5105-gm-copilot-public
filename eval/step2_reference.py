"""Independent CSV references for the public Step 2 development suite (no app imports)."""

from __future__ import annotations

import csv
import re
from datetime import date
from pathlib import Path

from answer_contracts import check_answer

ROOT = Path(__file__).resolve().parents[1]


def reference(case: dict, as_of: str) -> dict:
    with (ROOT / "data" / "orders.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if case.get("behavior") == "not_found":
        return {"behavior": "not_found", "as_of": as_of}
    if case.get("behavior") == "ambiguous":
        return {"type": "order", "as_of": as_of, "candidates": sorted(
            r["order_id"] for r in rows if r["customer"] == case["customer"] and r["status"] == "IN_PROGRESS")}
    row = next(r for r in rows if r["order_id"] == case["order_id"]) | case.get("override", {})

    def valid_day(value):
        try:
            return date.fromisoformat(value).isoformat()
        except (ValueError, TypeError):
            return None

    return {"type": "order", "as_of": as_of, "order_id": row["order_id"], "status": row["status"],
            "stage": row["current_stage"] or None, "due_date": valid_day(row["due_date"]),
            "completed_date": valid_day(row["completed_date"])}


def score(ref: dict, reply: dict) -> list[str]:
    text = "\n".join([reply.get("headline", ""), reply.get("details") or "",
                       reply.get("clarification_question") or ""] + reply.get("followups", []) +
                      [o["label"] + " " + o["value"] for o in reply.get("options", [])])
    text = text.replace("**", "").replace("`", "")
    if ref.get("behavior") == "not_found":
        errors = []
        if reply.get("kind") != "clarify" or not re.search(r"\b(?:no match|not found|does not exist|could not find)",
                                                          text, re.I):
            errors.append("not_found_disclosure")
        if "?" not in text or not re.search(r"\b(?:id|identifier)\b", text, re.I):
            errors.append("request_identifier")
        if re.search(r"\b(?:due|deadline|packing|washing|assembly|knitting|complete|days overdue)\b", text, re.I):
            errors.append("invented_status")
        return errors
    return check_answer(ref, {"kind": reply.get("kind"), "text": text})
