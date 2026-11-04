"""Make an authored held-out package runnable by fixed rules, without anyone reading it through this tool.

    uv run --project backend python eval/prepare_heldout.py --input <private>/authored.yaml --check-only
    uv run --project backend python eval/prepare_heldout.py --input <private>/authored.yaml \
        --output <private>/heldout.yaml

Authors state facts and values; writing a context-aware pattern for each one proved too much to ask. So each fact gets
a check by rule, decided by its type and never by what the system answers:

- a whole number, a non-negative decimal with zero tolerance, or an ISO date: the literal value must appear;
- a single token (an order ID, a stage) that also appears in the author's reference answer: the same;
- anything else (yes/no, phrases, signed or tolerant numbers): judge-only.

A literal check says the value is present, not that it is attached to the right thing. The judge checks that, and a
person reviews unrecognised wording (eval/protocol/rubric.md). Facts that already have a pattern are left alone.

Output is ids, counts and error codes only, never question, answer, value or pattern text, so a developer can run it
on a package they must not read. It writes only with --output and never over an existing file.
"""

from __future__ import annotations

import argparse
import copy
import math
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from frozen_protocol import validate_package  # noqa: E402
from independent_scoring import JUDGE_ONLY, hard_score  # noqa: E402

ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
TOKEN = re.compile(r"[A-Za-z0-9_-]+")
BEHAVIOR_KIND = {"propose_action": "propose", "reject_action": "reject"}


def _tolerance(value) -> float:
    """Authors may write a tolerance as text ("exact", "+/- 0.5 pieces"): the first number in it, or 0."""
    if isinstance(value, str):
        found = re.search(r"\d+(?:\.\d+)?", value)
        return float(found[0]) if found else 0
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else 0


def _number_pattern(value: float) -> str:
    whole = value == int(value)
    text = str(int(value)) if whole else re.escape(repr(float(value)))
    if whole:
        return rf"(?<![\d.])(?P<value>{text}(?:\.0+)?)(?![\d.]*\d)"
    return rf"(?<![\d.])(?P<value>{text}0*)(?!\d)"  # 12.5 also reads as 12.50, not as 12.55


def convert_fact(fact: dict, reference_answer: str) -> tuple[dict, str]:
    """The fact with a value_type and, where the rule allows, a literal pattern; plus how it was treated."""
    out = dict(fact)
    out["unit"] = out.get("unit") or "not_applicable"
    out["calculation"] = out.get("calculation") or "not_applicable"
    if out.get("pattern") and out.get("value_type"):
        out["tolerance"] = _tolerance(out.get("tolerance"))
        return out, "kept"
    expected, tolerance = out.get("expected_value"), _tolerance(out.get("tolerance"))
    out["tolerance"] = tolerance
    is_number = isinstance(expected, (int, float)) and not isinstance(expected, bool) and math.isfinite(expected)
    if is_number and expected >= 0 and not tolerance:
        out.update(value_type="number", pattern=_number_pattern(expected))
        return out, "number"
    if isinstance(expected, str) and ISO_DATE.fullmatch(expected):
        out.update(value_type="date", pattern=rf"(?P<value>{expected})")
        return out, "date"
    if (isinstance(expected, str) and TOKEN.fullmatch(expected)
            and re.search(rf"(?<!\w){re.escape(expected)}(?!\w)", reference_answer, re.I)):
        out.update(value_type="text", pattern=rf"(?<!\w)(?P<value>{re.escape(expected)})(?!\w)")
        return out, "token"
    out.update(value_type=JUDGE_ONLY, expected_value=str(expected))
    out.pop("pattern", None)
    return out, "judge"


def convert(package: dict) -> tuple[dict, Counter, dict]:
    pkg = copy.deepcopy(package)
    treated: Counter = Counter()
    changes = {"feasibility_behavior_set_to_estimate": []}
    for item in pkg["items"]:
        if item.get("category") == "feasibility" and item.get("expected_behavior") == "answer":
            item["expected_behavior"] = "estimate"  # a feasibility reply is an estimate with assumptions (the brief)
            changes["feasibility_behavior_set_to_estimate"].append(item["id"])
        facts = []
        for fact in item.get("required_facts") or []:
            new, how = convert_fact(fact, str(item.get("reference_answer") or ""))
            treated[how] += 1
            facts.append(new)
        item["required_facts"] = facts
    return pkg, treated, changes


def self_check(pkg: dict) -> list[str]:
    """Each reference answer must pass its own checks; ids and codes only."""
    lines = []
    for item in pkg["items"]:
        kind = BEHAVIOR_KIND.get(item["expected_behavior"], item["expected_behavior"])
        hard = hard_score(item, {"kind": kind, "text": item["reference_answer"]}, str(pkg["as_of"]))
        bad = [(n, c["issues"]) for n, c in enumerate(hard["criteria"]) if c["issues"]]
        hits = len(hard["prohibited_claims"])
        lines.append(f"{item['id']} {item['category']} " + ("OK" if hard["pass"] else f"FAIL {bad} prohibited={hits}"))
    return lines


def warnings_for(pkg: dict) -> list[str]:
    behaviors = Counter(i["expected_behavior"] for i in pkg["items"])
    notes = []
    if not behaviors["reject_action"]:
        notes.append("no reject_action item (the guide asks for one action that should be rejected)")
    tracing = [i["id"] for i in pkg["items"] if i["category"] == "tracing" and not i.get("context_turns")]
    if tracing:
        notes.append(f"tracing items without context_turns: {tracing}")
    return notes


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--output", type=Path)
    ap.add_argument("--check-only", action="store_true")
    a = ap.parse_args()
    package = yaml.safe_load(a.input.read_text(encoding="utf-8"))
    pkg, treated, changes = convert(package)
    print("facts by treatment:", dict(treated))
    print("changes:", changes)
    try:
        validate_package({**pkg, "status": "frozen"})
        print("package structure: valid")
    except ValueError as e:  # the validator's fixed wording, plus an item id at most
        print("package structure: INVALID:", str(e)[:120])
    except (KeyError, TypeError) as e:
        print("package structure: INVALID:", type(e).__name__)
    report = self_check(pkg)
    print("\n".join(report))
    passing = sum(line.endswith(" OK") for line in report)
    print("reference answers passing their own checks:", passing, "of", len(report))
    for note in warnings_for(pkg):
        print("note:", note)
    if a.output and not a.check_only:
        with a.output.open("x", encoding="utf-8") as stream:
            yaml.safe_dump(pkg, stream, allow_unicode=True, sort_keys=False)
        print("written to the path you gave")


if __name__ == "__main__":
    main()
