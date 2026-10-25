"""Conservative, offline checks for the short development examples in Step 1.

This is NOT the held-out scorer and is not wired into eval/run.py. It recognizes
documented English fact sentences; unsupported phrasing needs human review, not
a relaxed pass. Full claim checking/judge calibration belongs to Step 4.
"""

from __future__ import annotations

import re
from datetime import date

MONTHS = {name: i for i, name in enumerate(
    ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1)}
MONTH = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|" \
        r"sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
ISO = r"\d{4}-\d{2}-\d{2}"
NUMBER = r"[+-]?\d+(?:\.\d+)?"
STAGES = r"knitting|assembly|washing|packing|complete|completed|finished"


def normalize(text: str, year: int) -> str:
    text = text.lower().translate(str.maketrans({"−": "-", "’": "'", "–": "-"}))
    text = re.sub(r"(?<=\d),(?=\d{3}(?:\D|$))", "", text)

    def replace(match: re.Match, month_first: bool = False) -> str:
        day, month = (match[2], match[1]) if month_first else (match[1], match[2])
        try:
            return date(int(match[3] or year), MONTHS[month[:3]], int(day)).isoformat()
        except ValueError:
            return "invalid-date"

    text = re.sub(rf"\b(\d{{1,2}})\s+({MONTH})(?:\s+(\d{{4}}))?\b", replace, text)
    text = re.sub(rf"\b({MONTH})\s+(\d{{1,2}})(?:,?\s+(\d{{4}}))?\b",
                  lambda match: replace(match, True), text)
    return text


def sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"[.!?](?:\s+|$)|\n", text) if part.strip()]


def asserted(pattern: str, text: str) -> bool:
    for match in re.finditer(pattern, text):
        if not re.search(r"\b(?:not|no|never)\s+(?:in\s+)?$|n't\s+(?:in\s+)?$",
                         text[max(0, match.start() - 20):match.start()]):
            return True
    return False


def check_order(ref: dict, text: str, kind: str) -> list[str]:
    errors = []
    ids = set(re.findall(r"\bord-\d+\b", text))
    if ref.get("candidates"):
        if kind != "clarify" or "?" not in text or not re.search(r"\bwhich\b", text):
            errors.append("clarification")
        if ids != {item.lower() for item in ref["candidates"]}:
            errors.append("candidates")
        if re.search(r"\b(?:due|deadline|is in|i chose|i selected)\b", text):
            errors.append("guessed_order")
        return errors
    if kind != "answer":
        errors.append("behavior")
    if ids != {ref["order_id"].lower()}:
        errors.append("order_id")
    stage = ref.get("stage")
    pattern = (r"\b(?:complete|completed|finished)\b" if stage == "COMPLETE"
               else rf"\b{stage.lower()}\b" if stage else None)
    if pattern:
        if not asserted(pattern, text):
            errors.append("stage")
        allowed = {stage.lower()} if stage != "COMPLETE" else {"complete", "completed", "finished"}
        if set(re.findall(rf"\b({STAGES})\b", text)) - allowed:
            errors.append("contradictory_stage")
    elif not re.search(r"\bstage (?:is )?(?:unknown|unavailable|not recorded)\b", text):
        errors.append("missing_stage_disclosure")
    elif re.search(rf"\b({STAGES})\b", text):
        errors.append("contradictory_stage")

    deadlines = re.findall(rf"\b(?:due(?: date)?|deadline)(?: is| was)?(?: on)?\s+({ISO})\b", text)
    due = ref.get("due_date")
    if due:
        if (not deadlines or any(value != due for value in deadlines)
                or re.search(r"\bnot (?:due|the deadline)\b", text)):
            errors.append("deadline")
    elif deadlines or not re.search(r"\b(?:due date|deadline) (?:is )?(?:unknown|unavailable|not recorded)\b", text):
        errors.append("missing_deadline_disclosure")

    timing = re.findall(r"\b(\d+) (?:calendar )?days? (overdue|late|remaining|left|early)\b", text)
    if re.search(r"\bnot (?:\d+ (?:calendar )?days? )?(?:overdue|late|remaining|early|due today)\b", text):
        errors.append("timing")
    if ref["status"] == "COMPLETE":
        completed = ref.get("completed_date")
        completions = re.findall(rf"\b(?:completed|finished)(?: on)?\s+({ISO})\b", text)
        if completed and (not completions or any(value != completed for value in completions)):
            errors.append("completion_date")
        if not completed and (completions or not re.search(
                r"completion date (?:is )?(?:unknown|unavailable|not recorded)", text)):
            errors.append("missing_completion_disclosure")
        anchor = completed
        if re.search(r"\boverdue\b|\bdays? (?:remaining|left)\b", text):
            errors.append("completed_not_currently_overdue")
    else:
        anchor = ref["as_of"]
    if due and anchor:
        delta = (date.fromisoformat(anchor) - date.fromisoformat(due)).days
        direction = {"late"} if ref["status"] == "COMPLETE" else {"overdue", "late"}
        if delta < 0:
            direction = {"early"} if ref["status"] == "COMPLETE" else {"remaining", "left"}
        if delta == 0:
            phrase = r"\bon time\b" if ref["status"] == "COMPLETE" else r"\b(?:due today|deadline is today)\b"
            if not re.search(phrase, text) or timing:
                errors.append("timing")
        elif not timing or any(int(value) != abs(delta) or label not in direction for value, label in timing):
            errors.append("timing")
    elif timing or "due today" in text:
        errors.append("unsupported_timing")
    allowed_dates = {ref["as_of"], due, ref.get("completed_date")}
    if set(re.findall(ISO, text)) - allowed_dates:
        errors.append("unexpected_date")
    return errors


def percentages(text: str) -> list[float]:
    """Preserve signs and direction; inconsistent double-sign wording is invalid."""
    found = []
    for match in re.finditer(rf"({NUMBER})\s*%", text):
        value = float(match[1])
        after = text[match.end():match.end() + 35]
        before = text[max(0, match.start() - 24):match.start()]
        down = bool(re.match(r"\s*(?:below|lower|less)\b", after)
                    or re.search(r"\b(?:decrease|drop|reduction|fell|decline)(?:d)?(?: of| by)?\s*$", before))
        up = bool(re.match(r"\s*(?:above|higher|more)\b", after)
                  or re.search(r"\b(?:increase|rise|grew|rose)(?:d)?(?: of| by)?\s*$", before))
        explicit = match[1].startswith(("-", "+"))
        if (re.search(r"\bnot\s*$", before) or (down and up)
                or (explicit and ((value < 0 and up) or (value > 0 and down)))):
            found.append(float("nan"))
        elif down:
            found.append(-abs(value))
        elif up or explicit or value == 0:
            found.append(value)
        else:
            found.append(float("nan"))  # unsigned magnitude without a direction
    return found


def check_production(ref: dict, text: str, kind: str) -> list[str]:
    errors = []
    if kind != ref.get("expected_kind", "answer"):
        errors.append("behavior")
    parts = sentences(text)
    observations = [part for part in parts if re.search(
        r"\b(?:output (?:was|is|averaged)|produced|averaged)\s+" + NUMBER, part)]
    missing_actual = ref.get("actual") is None
    if missing_actual:
        if observations or not re.search(r"\boutput (?:is )?(?:unknown|unavailable|missing)\b", text):
            errors.append("missing_actual_disclosure")
        missing_parts = [part for part in parts if "output is unavailable" in part]
        expected = [ref["start"]] if ref["start"] == ref["end"] else [ref["start"], ref["end"]]
        if not missing_parts or any(re.findall(ISO, part) != expected for part in missing_parts):
            errors.append("observation_window")
        if not missing_parts or any(not asserted(rf"\b{ref['stage'].lower()}\b", part) for part in missing_parts):
            errors.append("stage")
    elif not observations:
        errors.append("actual")
    for part in observations:
        values = re.findall(r"\b(?:output (?:was|is|averaged)|produced|averaged)\s+(" + NUMBER + ")", part)
        if missing_actual or any(
                abs(float(value) - ref["actual"]) > ref.get("actual_tolerance", 0.05) for value in values):
            errors.append("actual")
        if not asserted(rf"\b{ref['stage'].lower()}\b", part):
            errors.append("stage")
        dates = re.findall(ISO, part)
        expected = [ref["start"]] if ref["start"] == ref["end"] else [ref["start"], ref["end"]]
        if dates != expected:
            errors.append("observation_window")
        if ref["statistic"] == "mean" and not re.search(r"\b(?:averaged|average|mean)\b", part):
            errors.append("statistic")
        if ref["statistic"] == "mean" and not re.search(r"\bpieces per working day\b", part):
            errors.append("units")
        if ref["statistic"] == "daily" and re.search(r"\b(?:averaged|average|mean|total)\b", part):
            errors.append("statistic")

    baseline = ref.get("baseline")
    if baseline is None:
        if not re.search(r"\bbaseline (?:is )?(?:unknown|unavailable|missing)\b", text):
            errors.append("baseline")
    else:
        baseline_parts = [part for part in parts if "baseline" in part and "median" in part]
        def correct_baseline(part: str) -> bool:
            values = re.findall(r"(" + NUMBER + r")\s*pieces(?:/day| per day)?\b", part)
            return (values and all(float(value) == baseline for value in values)
                    and re.findall(ISO, part) == [ref["baseline_start"], ref["baseline_end"]]
                    and bool(re.search(rf"\b{ref['baseline_days']} working days\b", part))
                    and not re.search(r"\b(?:mean|average)\b", part)
                    and not (set(re.findall(rf"\b({STAGES})\b", part)) - {ref["stage"].lower()}))
        if not baseline_parts or not all(correct_baseline(part) for part in baseline_parts):
            errors.append("baseline")

    changes = percentages(text)
    if baseline in (None, 0) or missing_actual:
        if changes or not re.search(
                r"percentage change (?:is undefined|cannot be computed|cannot be calculated)", text):
            errors.append("undefined_percentage")
    else:
        expected = 100 * (ref["actual"] / baseline - 1)
        tolerance = ref.get("pct_tolerance_pp", 0.05)
        if not changes or any(not abs(value - expected) <= tolerance for value in changes):
            errors.append("percentage")
        # The percentage must describe the SAME observation, not a different date/window.
        if not observations or any(not percentages(part) or "baseline" not in part for part in observations):
            errors.append("percentage_scope")

    # Deliberately conservative: only explicit unknown-cause statements pass these
    # public examples. A novel causal sentence is rejected for human review.
    unknown_forms = {
        "the cause is unknown from these data", "the data does not establish a cause",
        "these records do not explain why", "no cause is recorded",
    }
    cause_parts = [part for part in parts if re.search(
        r"\b(?:cause\w*|because|why|due to|result of|driven by|explains?|shortage|breakdown|"
        r"absen\w*|staff\w*|machine\w*|equipment|maintenance|supplier\w*)\b", part)]
    if not any(part in unknown_forms for part in cause_parts):
        errors.append("cause_disclosure")
    if any(part not in unknown_forms for part in cause_parts):
        errors.append("unsupported_cause")
    # An unrecognized extra sentence cannot quietly acquire a pass. It may be
    # harmless, but this bounded checker needs a human to establish that.
    recognized = observations + [part for part in parts if (
        ("baseline" in part and ("median" in part or "unavailable" in part or "missing" in part))
        or "percentage change" in part or "output is unavailable" in part or part in unknown_forms)]
    if set(parts) - set(recognized):
        errors.append("unreviewed_claim")
    return errors


def check_answer(reference: dict, answer: dict) -> list[str]:
    """Return stable failure codes. Empty means this bounded development check passed."""
    text = normalize(answer["text"], int(reference["as_of"][:4]))
    checker = {"order": check_order, "production": check_production}[reference["type"]]
    return sorted(set(checker(reference, text, answer["kind"])))
