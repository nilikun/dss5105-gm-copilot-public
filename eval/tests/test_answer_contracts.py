"""Executable Step 1 acceptance examples; no live agent or judge calls."""

import copy
import json
import sys
from pathlib import Path

import pytest

EVAL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVAL))
from answer_contracts import check_answer, percentages  # noqa: E402
from contract_reference import order_reference, production_reference  # noqa: E402
from record_step1_baseline import has_commit, verify  # noqa: E402

CASES = json.loads((EVAL / "fixtures/answer_contracts.json").read_text(encoding="utf-8"))["cases"]
MANIFEST = json.loads((EVAL / "baselines/step1.json").read_text(encoding="utf-8"))
# The baseline commit lives in the development repo's history; the public export is a single commit, so there
# only the data files are checked against the manifest.
HISTORY = has_commit(MANIFEST["baseline_commit"])


@pytest.mark.parametrize("case,answer", [(case, answer) for case in CASES for answer in case["accepted"]],
                         ids=[f"{case['id']}-equivalent-{i}" for case in CASES for i, _ in enumerate(case["accepted"])])
def test_equivalent_complete_answers(case, answer):
    assert check_answer(case["reference"], answer) == []


@pytest.mark.parametrize("case,example", [(case, bad) for case in CASES for bad in case["rejected"]],
                         ids=[f"{case['id']}-{bad['label']}" for case in CASES for bad in case["rejected"]])
def test_deliberate_errors_are_rejected_for_the_right_reason(case, example):
    assert example["must_fail"] in check_answer(case["reference"], example["answer"])


def test_d02_reference_from_csv():
    assert order_reference("ORD-107") == CASES[0]["reference"]
    assert CASES[0]["reference"]["due_date"] == "2026-03-16"


def test_day_and_period_are_different_comparisons():
    day = production_reference("ASSEMBLY", "2026-03-25", "2026-03-25")
    period = production_reference("ASSEMBLY", "2026-03-25", "2026-03-31")
    assert day["baseline"] == period["baseline"] == 766.5
    assert (day["baseline_start"], day["baseline_end"], day["baseline_days"]) == ("2026-03-02", "2026-03-24", 20)
    assert day["actual"] == 394
    assert period["actual"] == 425.5 and period["observed_days"] == 6
    assert day["pct_change"] == pytest.approx(-48.5975212)
    assert period["pct_change"] == pytest.approx(-44.4879322)


@pytest.mark.parametrize("case", [case for case in CASES if case["source"].startswith("data/")],
                         ids=lambda case: case["id"])
def test_public_reference_values_are_reproducible_from_raw_csv(case):
    ref = case["reference"]
    expected = (order_reference(ref["order_id"]) if ref["type"] == "order" else
                production_reference(ref["stage"], ref["start"], ref["end"]))
    for key, value in expected.items():
        assert ref[key] == value


def test_invalid_or_unobserved_window_is_not_silently_averaged():
    with pytest.raises(ValueError):
        production_reference("ASSEMBLY", "2026-03-29", "2026-03-29")  # Sunday only
    with pytest.raises(ValueError):
        production_reference("ASSEMBLY", "2026-03-31", "2026-04-02")  # unknown future
    with pytest.raises(ValueError):
        production_reference("ASSEMBLY", "2026-03-25", "2026-03-25", baseline_before="2026-03-26")


def test_sign_and_direction_are_preserved():
    assert percentages("-48.6% versus baseline") == [-48.6]
    assert percentages("48.6% below baseline") == [-48.6]
    assert percentages("an increase of 48.6% relative to baseline") == [48.6]
    assert percentages("+48.6% versus baseline") == [48.6]
    import math
    assert math.isnan(percentages("-48.6% above baseline")[0])
    assert math.isnan(percentages("48.6% versus baseline")[0])


def test_correct_date_on_wrong_order_cannot_rescue_wrong_answer():
    case = CASES[0]
    answer = copy.deepcopy(case["accepted"][0])
    answer["text"] = answer["text"].replace("2026-03-16", "2026-03-17") + " ORD-120 was due 2026-03-16."
    errors = check_answer(case["reference"], answer)
    assert "deadline" in errors and "order_id" in errors


def test_percentage_in_another_sentence_is_not_credit_for_observation():
    case = next(case for case in CASES if case["id"] == "D35")
    answer = copy.deepcopy(case["accepted"][0])
    answer["text"] = answer["text"].replace(", 48.6% below baseline", "") + " On 2026-03-26 output fell 48.6%."
    assert "percentage_scope" in check_answer(case["reference"], answer)


def test_grounding_flag_cannot_override_a_bad_answer():
    case = CASES[0]
    answer = dict(case["rejected"][0]["answer"], grounded=True, judge_score=1.0)
    assert "deadline" in check_answer(case["reference"], answer)


def test_contradictory_timing_cannot_pass_with_correct_number():
    case = CASES[0]
    answer = copy.deepcopy(case["accepted"][0])
    answer["text"] += " It is not overdue."
    assert "timing" in check_answer(case["reference"], answer)


def test_baseline_of_a_different_stage_is_wrong_even_when_value_matches():
    case = next(case for case in CASES if case["id"] == "D35")
    answer = copy.deepcopy(case["accepted"][0])
    answer["text"] = answer["text"].replace("The baseline", "The packing baseline")
    assert "baseline" in check_answer(case["reference"], answer)


def test_baseline_manifest_and_current_data_match():
    assert verify(copy.deepcopy(MANIFEST), history=HISTORY) == []


def test_manifest_tampering_is_detected():
    manifest = copy.deepcopy(MANIFEST)
    manifest["files"]["data/orders.csv"]["sha256"] = "0" * 64
    assert verify(manifest, history=HISTORY)
