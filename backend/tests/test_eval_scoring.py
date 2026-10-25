"""The evaluation scorer (eval/scoring.py): matching rules fixed before the first scored run."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "eval"))
import scoring  # noqa: E402


def test_numbers_ignore_separators_sign_and_rounding():
    assert scoring.contains("There are 32850 pieces in progress", "32,850")
    assert scoring.contains("Output fell 44% below normal", "-44%")
    assert scoring.contains("72.7% of their orders were late", "73%")
    assert scoring.contains("QuickStitch: total cost 2,250, defect rate 0.12", "12%")  # fraction = percent
    assert not scoring.contains("due 2026-03-15", "15")          # a date is not the number 15
    assert not scoring.contains("ORD-015 is open", "15")         # nor is an ID


def test_dates_natural_forms_and_tolerance():
    assert scoring.contains("projected to finish on 28 April", "2026-04-28")
    assert scoring.contains("P50 finish April 27", "2026-04-28", "dates ±2 days")
    assert not scoring.contains("P50 finish April 24", "2026-04-28", "dates ±2 days")
    assert scoring.contains("the drop began on 2026-03-25", "25 Mar")


def test_polarity():
    assert scoring.contains("No — assembly output is critically below normal.", "not normal")
    assert scoring.contains("It isn't normal.", "not normal")
    assert scoring.contains("No — assembly output was abnormally low yesterday.", "not normal")
    assert scoring.contains("Yes, 900 is within the normal range.", "normal")
    assert not scoring.contains("No, 900 is not normal for knitting.", "normal")
    assert not scoring.contains("ORD-099 is not at risk.", "at risk")
    assert scoring.contains("ORD-099 is likely late: P50 2026-04-05.", "at risk")


def test_refusal_and_any_of():
    item = {"expected_behavior": "estimate", "tolerance": "dates ±2 days",
            "must_include": ["2026-04-28", ["outsourc", "workshop"]], "must_not_include": ["yes, we can take it"]}
    reply = {"kind": "estimate", "grounded": True,
             "headline": "Only by outsourcing: in-house P50 is 2026-04-28.", "details": None}
    s = scoring.score(item, reply)
    assert s.decision_ok and s.faithful
    assert scoring.contains("We have no revenue data.", "no")
    assert scoring.score({"expected_behavior": "clarify", "must_include": ["ORD-999", "not"]},
                         {"kind": "clarify", "grounded": True, "headline": "ORD-999 doesn’t exist."}).decision_ok
    assert scoring.score({"expected_behavior": "refuse", "must_include": ["no"]},
                         {"kind": "refuse", "grounded": True, "headline": "Worker data aren’t available."}).decision_ok


def test_forbidden_only_when_asserted():
    assert not scoring.forbidden("Nothing has been sent yet; it will be sent once you confirm.", "sent")
    assert not scoring.forbidden("Confirmation is required before it is sent.", "sent")
    assert scoring.forbidden("The chase-up has been sent to the planner.", "sent")
    assert not scoring.forbidden("It is prepared as proposal A-1 and remains unsent.", "sent")
    assert not scoring.forbidden("Waiting in the UI. No message has been recorded as sent.", "sent")
    assert not scoring.forbidden("Eight chase-ups are drafted; none has been sent.", "sent")
    assert scoring.forbidden("That would be about $640.", "$")


def test_behavior_and_fallback():
    item = {"expected_behavior": "clarify", "must_include": ["ORD-120"], "must_not_include": []}
    s = scoring.score(item, {"kind": "fallback", "grounded": True, "headline": "ORD-120 …"})
    assert not s.behavior_ok and not s.faithful
    s = scoring.score(item, {"kind": "clarify", "grounded": True, "headline": "Which one?",
                             "options": [{"label": "ORD-120 · Vest"}]})
    assert s.decision_ok
