"""Frozen-rule scoring, independent of agent tools, evidence IDs and grounding flags.

Authors define contextual extraction rules against independently calculated values.
Unrecognized wording is review-required, never an automatic pass. The semantic
judge is an additional veto; it cannot override deterministic fact failures.
"""

from __future__ import annotations

import math
import re
from datetime import date

from answer_contracts import ISO, normalize, percentages

SEMANTIC = ("unsupported_claims", "relevance", "clarity")
BEHAVIOR = {"propose_action": "propose", "reject_action": "reject"}


def answer_text(reply):
    if "text" in reply:
        return reply["text"]
    return "\n".join(
        [reply.get("headline", ""), reply.get("details") or "", reply.get("clarification_question") or ""]
        + reply.get("followups", [])
        + [o["label"] + " " + o["value"] for o in reply.get("options", [])]
        + [str(p) for p in reply.get("proposals", [])]
    )


def normalized(text, as_of):
    return normalize(text.replace("**", "").replace("`", ""), int(as_of[:4]))


def rule(criterion_id, subject, field, expected, pattern, value_type="text", tolerance=0, **extra):
    return {
        "criterion_id": criterion_id,
        "subject": subject,
        "field": field,
        "expected_value": expected,
        "pattern": pattern,
        "value_type": value_type,
        "tolerance": tolerance,
        **extra,
    }


def contract_rules(ref):
    """Public rule factory for two contracts. References are computed separately from CSVs."""
    if ref["type"] == "order":
        oid = ref["order_id"]
        rules = [
            rule("identity", oid, "order_id", oid, r"(?P<value>\bord-\d+\b)"),
            rule(
                "stage",
                oid,
                "stage",
                ref["stage"] or "unknown",
                r"(?:\bis in\s+|current stage\s*:?\s*|stage\s*(?:is|:)\s*)(?P<value>[a-z]+)",
            ),
        ]
        # Status prose can say "ORD-107 is in PACKING"; stage-only labels also accepted.
        due = ref["due_date"]
        rules.append(
            rule(
                "deadline",
                oid,
                "due_date",
                due or "unknown",
                rf"\b(?:due(?: date)?|deadline)(?:\s+is|\s+was)?\s*:?\s*(?:on\s+)?"
                rf"(?P<value>{ISO}|unknown|unavailable|not recorded)",
                "date" if due else "text",
            )
        )
        if due and ref["status"] != "COMPLETE":
            delta = (date.fromisoformat(ref["as_of"]) - date.fromisoformat(due)).days
            if delta:
                direction = "overdue|late" if delta > 0 else "remaining|left"
                pattern = (
                    rf"(?:(?P<prefix>{direction})\s+by\s+)?(?P<value>\d+)\s+(?:calendar\s+)?days?"
                    rf"(?(prefix)|\s+(?:{direction})\b)"
                )
                rules.append(rule("timing", oid, "days", abs(delta), pattern, "number"))
            else:
                rules.append(rule("timing", oid, "days", "due today", r"(?P<value>due today)"))
        return rules
    stage, start, end = ref["stage"], ref["start"], ref["end"]
    subject = stage.lower()
    # A scope is one sentence/line. Dates, unit, stage and percentage must describe the same observation.
    scope = rf"\b{subject}\b"
    dates = [start] if start == end else [start, end]
    rules = []
    if ref["actual"] is None:
        rules.append(
            rule(
                "actual",
                stage,
                "actual",
                "unavailable",
                r"output (?:is )?(?P<value>unknown|unavailable|missing)",
                scope_dates=dates,
                scope_subject=stage,
            )
        )
    else:
        rules.append(
            rule(
                "actual",
                stage,
                "actual",
                ref["actual"],
                r"(?:output\s+(?:was|is|averaged)|produced|averaged)\s+(?P<value>[+-]?\d+(?:\.\d+)?)",
                "number",
                0.05,
                scope_dates=dates,
                scope_subject=stage,
                scope_pattern=scope,
            )
        )
    base = ref["baseline"]
    if base is None:
        rules.append(
            rule(
                "baseline", stage, "baseline", "unavailable", r"baseline (?:is )?(?P<value>unknown|unavailable|missing)"
            )
        )
    else:
        rules.append(
            rule(
                "baseline",
                stage,
                "baseline",
                base,
                r"\bbaseline\b[^.\n]*?\bmedian\b[^!\n]*?(?P<value>\d+(?:\.\d+)?)\s*pieces",
                "number",
                0,
                scope_dates=[ref["baseline_start"], ref["baseline_end"]],
            )
        )
    if base and ref["actual"] is not None:
        rules.append(
            rule(
                "percentage",
                stage,
                "pct_change",
                100 * (ref["actual"] / base - 1),
                r"(?P<value>[+-]?\d+(?:\.\d+)?\s*%)",
                "percentage",
                0.05,
                scope_dates=dates,
                scope_subject=stage,
            )
        )
    else:
        rules.append(
            rule(
                "percentage_unavailable",
                stage,
                "pct_change",
                "percentage change is undefined",
                r"(?P<value>percentage change (?:is undefined|cannot be calculated|cannot be computed))",
                aliases=["percentage change cannot be calculated", "percentage change cannot be computed"],
            )
        )
    if ref["statistic"] == "mean" and ref["actual"] is not None:  # no mean exists to describe when a day is missing
        rules.append(
            rule(
                "statistic",
                stage,
                "statistic",
                "averaged",
                r"(?P<value>averaged|average|mean)",
                aliases=["average", "mean"],
                scope_dates=dates,
                scope_subject=stage,
            )
        )
        rules.append(
            rule(
                "unit",
                stage,
                "unit",
                "pieces per working day",
                r"(?P<value>pieces per working day|pieces/working day)",
                aliases=["pieces/working day"],
            )
        )
    rules.append(
        rule(
            "cause_disclosure",
            stage,
            "cause",
            "the cause is unknown from these data",
            r"(?P<value>the cause is unknown from these data|no cause is recorded|"
            r"these records do not explain why|the data does not establish a cause)",
            aliases=["no cause is recorded", "these records do not explain why", "the data does not establish a cause"],
        )
    )
    return rules


def sentence_at(text, start, end):
    # Do not split decimal numbers or ISO dates.
    boundaries = [0] + [m.end() for m in re.finditer(r"[.!?](?:\s+|$)|\n", text)] + [len(text)]
    left = max(x for x in boundaries if x <= start)
    right = min(x for x in boundaries if x >= end)
    return text[left:right]


def validate_rule(fact):
    for key in ("criterion_id", "subject", "field", "pattern", "value_type"):
        if not isinstance(fact.get(key), str) or not fact[key].strip():
            raise ValueError(f"Missing fact field {key}")
    if fact["value_type"] not in {"text", "date", "number", "percentage"}:
        raise ValueError("Unknown value_type")
    if "value" not in re.compile(fact["pattern"]).groupindex:
        raise ValueError("Fact pattern must have a named value group")
    tolerance = fact.get("tolerance", 0)
    if not isinstance(tolerance, (float, int)) or not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("Invalid tolerance")
    expected = fact.get("expected_value")
    if fact["value_type"] in {"number", "percentage"}:
        if isinstance(expected, bool) or not isinstance(expected, (int, float)) or not math.isfinite(expected):
            raise ValueError("Numeric facts require finite numeric expected_value")
    elif not isinstance(expected, str) or not expected:
        raise ValueError("Text/date facts require nonempty expected_value")
    if fact["value_type"] == "date":
        date.fromisoformat(expected)


def hard_score(item, reply, as_of):
    text = normalized(answer_text(reply), as_of)
    criteria = []
    for fact in item["required_facts"]:
        validate_rule(fact)
        matches = list(re.finditer(fact["pattern"], text, re.I))
        issues, observed = [], []
        if not matches:
            issues.append("missing_or_unrecognized")
        for m in matches:
            scope = sentence_at(text, m.start(), m.end())
            value = m["value"].lower().strip()
            if fact.get("scope_subject") and fact["scope_subject"].lower() not in scope:
                issues.append("wrong_subject")
            if "scope_dates" in fact and re.findall(ISO, scope) != fact["scope_dates"]:
                issues.append("wrong_window")
            prefix = text[max(0, m.start() - 12) : m.start()]
            if re.search(r"\b(?:not|never)\s*$", prefix):
                issues.append("negated_fact")
            typ = fact["value_type"]
            if typ == "percentage":
                # Direction is read around the captured percentage, not stripped from the number.
                vals = percentages(text[max(0, m.start() - 24) : m.end() + 35])
                value = vals[0] if len(vals) == 1 else math.nan
            elif typ == "number":
                value = float(value)
            observed.append(value if not isinstance(value, float) or math.isfinite(value) else None)
            if typ in {"number", "percentage"}:
                correct = math.isfinite(value) and abs(value - fact["expected_value"]) <= fact.get("tolerance", 0)
            else:
                allowed = [str(fact["expected_value"]).lower(), *[s.lower() for s in fact.get("aliases", [])]]
                correct = value in allowed
            if not correct:
                issues.append("wrong_value_or_direction")
        criteria.append(
            {
                "criterion_id": fact["criterion_id"],
                "pass": not issues,
                "present": bool(matches),
                "observed": observed,
                "excerpts": [m[0] for m in matches],
                "issues": sorted(set(issues)),
            }
        )
    prohibited = []
    for pattern in item.get("prohibited_claims", []):
        if re.search(pattern, text, re.I):
            prohibited.append(pattern)
    behavior = reply.get("kind") == BEHAVIOR.get(item["expected_behavior"], item["expected_behavior"])
    return {
        "criteria": criteria,
        "behavior": behavior,
        "prohibited_claims": prohibited,
        "facts_pass": all(c["pass"] for c in criteria),
        "pass": all(c["pass"] for c in criteria) and behavior and not prohibited,
    }


def combine(hard, judge):
    """A missing/malformed judge is unscored; even a unanimously favourable judge cannot waive hard failures."""
    valid = isinstance(judge, dict) and judge.get("valid") is True
    decisions = judge.get("decisions", []) if valid else []
    expected_ids = [c["criterion_id"] for c in hard["criteria"]] + list(SEMANTIC)
    valid = valid and sorted(c.get("criterion_id", "") for c in decisions) == sorted(expected_ids)
    valid = valid and all(type(c.get("pass")) is bool for c in decisions)
    unsupported = (
        next((not c["pass"] for c in decisions if c["criterion_id"] == "unsupported_claims"), None) if valid else None
    )
    semantic_ok = valid and all(c.get("pass") is True for c in decisions)
    return {
        "pass": bool(hard["pass"] and semantic_ok),
        "correctness": hard["facts_pass"],
        "completeness": sum(c["present"] for c in hard["criteria"]) / len(hard["criteria"])
        if hard["criteria"]
        else None,
        "behavior": hard["behavior"],
        "unsupported_claims": unsupported,
        "judge_status": "scored" if valid else "unscored",
        "hard": hard,
        "judge": judge,
    }
