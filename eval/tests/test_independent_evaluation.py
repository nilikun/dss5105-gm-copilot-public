"""Adversarial scorer, calibration and release-gate checks; only PUBLIC fixtures."""

import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "eval"))
from calibrate import compare, make_packet, rows  # noqa: E402
from frozen_protocol import load_released, validate_package  # noqa: E402
from independent_scoring import SEMANTIC, combine, contract_rules, hard_score, rule  # noqa: E402
from judge import validate_decisions  # noqa: E402
from run_frozen import metrics, schedule  # noqa: E402
from step3_reference import reference  # noqa: E402


def production_item():
    case = json.loads((ROOT / "eval/fixtures/step3_production.json").read_text(encoding="utf-8"))["cases"][0]
    ref = reference(case, "2026-04-01")
    return {
        "question": case["question"],
        "expected_behavior": "refuse",
        "required_facts": contract_rules(ref),
        "prohibited_claims": [r"caused by a machine breakdown"],
    }


GOOD = {
    "kind": "refuse",
    "text": "ASSEMBLY output was 394 pieces on 2026-03-25, 48.6% below baseline.\n"
    "Baseline median: 766.5 pieces/day from 2026-03-02 to 2026-03-24 (20 working days).\n"
    "The cause is unknown from these data.",
}


def favorable(item):
    return {
        "valid": True,
        "decisions": [
            {"criterion_id": f, "pass": True, "excerpt": "ASSEMBLY", "reason": "test"}
            for f in [c["criterion_id"] for c in item["required_facts"]] + list(SEMANTIC)
        ],
    }


def test_equivalent_date_wording_and_signed_percentage_pass():
    for text in (
        GOOD["text"],
        GOOD["text"].replace("2026-03-25", "25 March 2026"),
        GOOD["text"].replace("48.6% below", "-48.6% versus"),
    ):
        assert hard_score(production_item(), GOOD | {"text": text}, "2026-04-01")["pass"]


@pytest.mark.parametrize(
    "before,after",
    [
        ("48.6%", "44.5%"),
        ("below", "above"),
        ("48.6%", "+48.6%"),
        ("2026-03-25", "2026-03-26"),
        ("394 pieces", "395 pieces"),
        (", 48.6% below baseline", ""),
        ("ASSEMBLY", "PACKING"),
        ("The cause is unknown from these data.", "The drop was caused by a machine breakdown."),
    ],
)
def test_favorable_judge_cannot_override_wrong_production_facts(before, after):
    item = production_item()
    hard = hard_score(item, GOOD | {"text": GOOD["text"].replace(before, after)}, "2026-04-01")
    assert not hard["pass"] and not combine(hard, favorable(item))["pass"]


def test_percentage_attached_to_wrong_window_fails_even_if_correct_date_elsewhere():
    bad = GOOD["text"].replace(", 48.6% below baseline", "") + "\nPACKING dropped 48.6% on 2026-03-26."
    assert not hard_score(production_item(), GOOD | {"text": bad}, "2026-04-01")["pass"]


@pytest.mark.parametrize(
    "text", ["Due date 2026-03-17.", "Last activity 2026-03-16.", "Due date 2026-03-16. Deadline 2026-03-17."]
)
def test_wrong_missing_or_contradictory_deadline_cannot_be_rescued(text):
    item = {
        "expected_behavior": "answer",
        "required_facts": [
            rule(
                "deadline",
                "ORD-107",
                "due_date",
                "2026-03-16",
                r"(?:due date|deadline)\s+(?P<value>\d{4}-\d{2}-\d{2})",
                "date",
            )
        ],
    }
    hard = hard_score(item, {"kind": "answer", "text": text, "grounded": True}, "2026-04-01")
    assert not combine(hard, favorable(item))["pass"]


def test_missing_or_invalid_judge_never_passes():
    hard = hard_score(production_item(), GOOD, "2026-04-01")
    for judge in (None, {"valid": False}):
        assert not combine(hard, judge)["pass"]
    item = production_item()
    with pytest.raises(ValueError):
        validate_decisions({"decisions": []}, item, GOOD["text"])
    fake = favorable(item)
    fake["decisions"][0]["excerpt"] = "This quote does not exist"
    with pytest.raises(ValueError):
        validate_decisions(fake, item, GOOD["text"])


def test_blank_authoring_template_and_freeze_are_rejected(tmp_path):
    with pytest.raises(ValueError, match="filled and frozen"):
        validate_package(yaml.safe_load((ROOT / "eval/questions_heldout.template.yaml").read_text(encoding="utf-8")))
    manifest = tmp_path / "freeze.json"
    manifest.write_text((ROOT / "eval/heldout_freeze.template.json").read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="not releasable"):
        load_released(manifest, ROOT, ROOT)


def test_blind_packet_has_twenty_candidates_and_no_filled_human_labels(tmp_path):
    make_packet(tmp_path / "packet")
    candidates = rows(tmp_path / "packet/candidates.jsonl")
    labels = rows(tmp_path / "packet/human_labels.template.jsonl")
    assert len(candidates) == len(labels) == 20
    assert all(not h["reviewer"] and all(c["pass"] is None for c in h["decisions"]) for h in labels)
    predictions = tmp_path / "predictions.jsonl"
    predictions.write_text(
        "".join(json.dumps({"id": e["id"], "judge": favorable(e["item"])}) + "\n" for e in candidates)
    )
    with pytest.raises(ValueError, match="Human identity"):
        compare(
            tmp_path / "packet/candidates.jsonl",
            tmp_path / "packet/human_labels.template.jsonl",
            predictions,
            tmp_path / "report.json",
        )
    assert not (tmp_path / "report.json").exists()


def test_schedule_pairs_versions_and_metrics_keep_failures():
    items = [{"id": "PUBLIC1"}, {"id": "PUBLIC2"}]
    plan = schedule(items, 3, 5105)
    assert len(plan) == 12 and plan == schedule(items, 3, 5105)
    attempted = [
        {
            "id": "PUBLIC1",
            "version": "baseline",
            "category": "lookup",
            "expected_behavior": "answer",
            "wall_seconds": 1,
            "api_calls": [{"usage": None}],
            "error": {"type": "Timeout"},
            "pass": False,
        }
    ]
    result = metrics(attempted, 12)
    assert result["unattempted"] == 11 and result["baseline"]["unknown_usage_calls"] == 1
    assert result["baseline"]["passed"] == 0 and result["baseline"]["planned"] == 6
    assert result["paired_pass_delta_95pct_cluster_bootstrap"] is None


def test_independent_modules_cannot_import_agent_truth():
    import ast

    for name in ("independent_scoring.py", "step3_reference.py", "judge.py"):
        tree = ast.parse((ROOT / "eval" / name).read_text(encoding="utf-8"))
        imports = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        assert not any(n and n.startswith("app") for n in imports)


def test_call_journal_preserves_inflight_unknown_usage(tmp_path):
    from run_frozen import read_call_journal

    path = tmp_path / "calls.jsonl"
    records = [
        {"call_index": 0, "usage": None, "pending": True},
        {"call_index": 0, "usage": {"input_tokens": 5}, "pending": False},
        {"call_index": 1, "usage": None, "pending": True},
    ]
    path.write_text("".join(json.dumps(r) + "\n" for r in records))
    result = read_call_journal(path)
    assert len(result) == 2 and result[0]["usage"]["input_tokens"] == 5
    assert result[1]["usage"] is None and result[1]["pending"] is True


def test_orchestration_smoke_preserves_all_paired_attempts(tmp_path, monkeypatch):
    """PUBLIC fake transport: exercise persistence/reporting without calling it held-out evidence."""
    from types import SimpleNamespace

    import run_frozen

    item = production_item() | {
        "id": "PUBLIC",
        "category": "judgement",
        "reference_answer": GOOD["text"],
        "reference_evidence": [{"source": "public fixture"}],
    }
    package = {"as_of": "2026-04-01T07:00:00", "items": [item]}
    rates = {"input_per_million": 1, "cached_input_per_million": 1, "output_per_million": 1}
    manifest = {
        "execution": {
            "repetitions_per_item_per_version": 3,
            "randomization_seed": 5105,
            "budget_usd": 10,
            "timeout_seconds": 30,
            "max_api_calls_per_attempt": 10,
        },
        "agent_settings": {},
        "judge_settings": {
            "model": "FAKE",
            "reasoning_effort": "low",
            "max_output_tokens": 1000,
            "timeout_seconds": 30,
        },
        "pricing": {"agent": rates, "judge": rates},
    }
    usage = {"input_tokens": 5, "cached_input_tokens": 0, "output_tokens": 4, "reasoning_tokens": 0}

    def fake_worker(command, **kwargs):
        output = Path(command[command.index("--output") + 1])
        output.write_text(
            json.dumps({"reply": GOOD, "api_calls": [{"usage": usage}], "error": None, "unconfirmed_actions": 0})
        )
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr(run_frozen.subprocess, "run", fake_worker)
    monkeypatch.setattr(run_frozen, "evaluate", lambda *a, **k: favorable(item) | {"usage": usage})
    out = tmp_path / "public-smoke"
    summary = run_frozen.execute(manifest, package, {"baseline": ROOT, "improved": ROOT}, out, "fake-test-key")
    assert summary["attempted"] == summary["planned"] == 6
    assert summary["baseline"]["passed"] == summary["improved"]["passed"] == 3
    assert summary["baseline"]["reported_usage"]["input_tokens"] == 30
    assert len((out / "results.jsonl").read_text(encoding="utf-8").splitlines()) == 6
    assert (out / "REPORT.md").exists()
    with pytest.raises(FileExistsError):
        run_frozen.execute(manifest, package, {"baseline": ROOT, "improved": ROOT}, out, "fake-test-key")


def test_full_release_gate_then_changed_hash_blocks_before_questions(tmp_path, monkeypatch):
    """Synthetic custody metadata tests mechanics only; this is not human calibration."""
    import platform
    from datetime import UTC, datetime, timedelta
    from importlib.metadata import version

    import frozen_protocol as protocol

    package = yaml.safe_load((ROOT / "eval/questions_heldout.template.yaml").read_text(encoding="utf-8"))
    package.update(
        status="frozen",
        author="SYNTHETIC TEST AUTHOR",
        written_on="2026-10-20",
        exposure_declaration="Synthetic test only; no unseen claim",
    )
    for item in package["items"]:
        item.update(
            question="PUBLIC MECHANICS TEST",
            expected_behavior="answer",
            reference_answer="value 1",
            verification="synthetic test",
            reference_evidence=[
                {
                    "source_file": "synthetic",
                    "row_filter": "all",
                    "calculation": "identity",
                    "result": 1,
                    "workbook_cells_or_script": "synthetic",
                }
            ],
            required_facts=[
                rule(
                    "value", "test", "count", 1, r"value (?P<value>\d+)", "number", unit="count", calculation="identity"
                )
            ],
        )
    questions = tmp_path / "questions.yaml"
    questions.write_text(yaml.safe_dump(package))
    hashes = {p: protocol.sha(ROOT / p) for p in protocol.SCORING_FILES}
    settings = {
        "model": "FAKE",
        "reasoning_effort": "low",
        "max_output_tokens": 1000,
        "timeout_seconds": 30,
        "max_retries": 0,
    }
    now = datetime.now(UTC)
    report = {
        "accepted": True,
        "human_reviewers": ["SYNTHETIC TEST ONLY"],
        "sample_count": 20,
        "scoring_files_sha256": hashes,
        "judge_settings": settings,
        "completed_utc": (now - timedelta(minutes=1)).isoformat(),
    }
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(report))
    calc = tmp_path / "synthetic.txt"
    calc.write_text("synthetic calculation")
    manifest = json.loads((ROOT / "eval/heldout_freeze.template.json").read_text(encoding="utf-8"))
    manifest.update(
        status="frozen",
        authored_before_outputs=True,
        author=package["author"],
        custodian="TEST",
        exposure_declaration="SYNTHETIC ONLY",
        frozen_at_with_timezone=now.isoformat(),
    )
    manifest["release"].update(
        scorer_and_settings_frozen_before_question_release=True,
        operator="TEST",
        released_at=(now + timedelta(minutes=1)).isoformat(),
    )
    commit = "a" * 40
    manifest["versions"].update(
        scoring_files_sha256=hashes,
        rubric_sha256=protocol.sha(ROOT / "eval/protocol/rubric.md"),
        python_version=platform.python_version(),
        sdk_versions={k: version(k) for k in ("openai", "pydantic", "pandas", "PyYAML")},
        scorer_commit=commit,
        baseline_commit=commit,
        improved_commit=commit,
        baseline_prompts_sha256={},
        improved_prompts_sha256={},
    )
    manifest["judge_settings"] = settings | {"prompt_sha256": protocol.sha(ROOT / "eval/protocol/judge_prompt.md")}
    manifest["calibration"].update(
        accepted_before_release=True, report={"filename": report_path.name, "sha256": protocol.sha(report_path)}
    )
    manifest["independent_calculations"] = [
        {"filename": calc.name, "sha256": protocol.sha(calc), "method": "synthetic", "checked_by": "SYNTHETIC TEST"}
    ]
    manifest["execution"].update(
        repetitions_per_item_per_version=3,
        concurrency=1,
        timeout_seconds=30,
        max_api_calls_per_attempt=10,
        budget_usd=1,
        retry_policy="no automatic retries; retain every attempt",
    )
    manifest["agent_settings"].update(
        model="FAKE",
        reasoning_effort="low",
        max_output_tokens=1000,
        critic_enabled=False,
        max_tool_steps=6,
        repair_limit=1,
    )
    rates = {"input_per_million": 1, "cached_input_per_million": 1, "output_per_million": 1}
    manifest["pricing"] = {"source_and_date": "SYNTHETIC TEST", "agent": rates, "judge": rates}
    manifest["questions_and_references"].update(filename=questions.name, sha256=protocol.sha(questions))
    path = tmp_path / "freeze.json"
    path.write_text(json.dumps(manifest))
    monkeypatch.setattr(protocol, "check_checkout", lambda *a: None)
    monkeypatch.setattr(protocol.subprocess, "check_output", lambda *a, **k: commit)
    _, loaded = protocol.load_released(path, ROOT, ROOT)
    assert len(loaded["items"]) == 20
    manifest["versions"]["scoring_files_sha256"] = {}
    path.write_text(json.dumps(manifest))
    questions.write_text("This must never be parsed when the scoring hash is wrong")
    with pytest.raises(ValueError, match="Scoring implementation changed"):
        protocol.load_released(path, ROOT, ROOT)


def test_invalid_criterion_set_is_unscored_not_no_unsupported_claims():
    hard = hard_score(production_item(), GOOD, "2026-04-01")
    result = combine(hard, {"valid": True, "decisions": [{"criterion_id": "unsupported_claims", "pass": True}]})
    assert not result["pass"] and result["judge_status"] == "unscored" and result["unsupported_claims"] is None


# ---------------------------------------------------------------- facts checked by rule, or by the judge alone


def _fact(**kw):
    return {"criterion_id": "c", "subject": "s", "field": "f", "unit": "", "calculation": "x", **kw}


def _item(fact, answer):
    return {"id": "P", "category": "lookup", "expected_behavior": "answer", "reference_answer": answer,
            "required_facts": [fact]}


def test_prepare_uses_literal_checks_only_where_a_rule_allows():
    from prepare_heldout import convert_fact

    answer = "ORD-999 is due on 2026-05-10; 1200 pieces, on time."
    assert convert_fact(_fact(expected_value=1200, tolerance=0), answer)[1] == "number"
    assert convert_fact(_fact(expected_value="2026-05-10", tolerance=0), answer)[1] == "date"
    assert convert_fact(_fact(expected_value="ORD-999", tolerance=0), answer)[1] == "token"
    for expected in (True, "on time, with margin", "ORD-123", -25.0):  # yes/no, a phrase, absent, a signed number
        fact, how = convert_fact(_fact(expected_value=expected, tolerance=0), answer)
        assert how == "judge" and "pattern" not in fact and fact["value_type"] == "judge"
    assert convert_fact(_fact(expected_value=12.5, tolerance=0.5), answer)[1] == "judge"


def test_a_literal_number_is_not_found_inside_another_number():
    from prepare_heldout import convert_fact

    fact, _ = convert_fact(_fact(expected_value=120, tolerance=0), "120")
    item = _item(fact, "120")
    for text, ok in (("120 pieces", True), ("120.0 pieces", True), ("1,200 pieces", False), ("1120 pieces", False),
                     ("120.5 pieces", False), ("Total: 120.", True)):
        assert hard_score(item, {"kind": "answer", "text": text}, "2026-04-01")["pass"] is ok, text


def test_prepare_never_prints_or_needs_the_content_and_fixes_feasibility_behavior(capsys, tmp_path):
    import prepare_heldout

    secret = "SECRETWORD"
    item = _item(_fact(expected_value=f"{secret} phrase", tolerance=0), f"{secret} 1")
    item.update(category="feasibility", question=f"{secret}?")
    path = tmp_path / "authored.yaml"
    path.write_text(yaml.safe_dump({"version": 2, "as_of": "2026-04-01T07:00:00", "items": [item]}), encoding="utf-8")
    argv = sys.argv
    sys.argv = ["prepare_heldout.py", "--input", str(path), "--check-only"]
    try:
        prepare_heldout.main()
    finally:
        sys.argv = argv
    out = capsys.readouterr().out
    assert secret not in out and "feasibility_behavior_set_to_estimate" in out and "['P']" in out


def test_judge_only_fact_needs_the_judge_to_pass_and_counts_as_absent_otherwise():
    fact = _fact(expected_value="a reason", value_type="judge", tolerance=0)
    item = _item(fact, "x")
    hard = hard_score(item, {"kind": "answer", "text": "anything"}, "2026-04-01")
    assert hard["pass"]  # the scorer cannot veto it, so the decision is the judge's alone

    def verdict(ok):
        return {"valid": True, "decisions": [{"criterion_id": c, "pass": ok or c != "c", "excerpt": "", "reason": "r"}
                                             for c in ("c", *SEMANTIC)]}

    good, bad = combine(hard, verdict(True)), combine(hard, verdict(False))
    assert good["pass"] and good["correctness"] and good["completeness"] == 1
    assert not bad["pass"] and not bad["correctness"] and bad["completeness"] == 0
    missing = combine(hard, None)
    assert not missing["pass"] and not missing["correctness"] and missing["judge_status"] == "unscored"


def test_merging_reviewers_needs_a_record_for_every_disagreement():
    from import_labels import merge

    def row(who, ok):
        return [{"id": "C1", "reviewer": who, "reviewed_at": "2026-11-02T00:00:00", "decisions": [
            {"criterion_id": "a", "pass": True, "excerpt": "", "reason": "same"},
            {"criterion_id": "b", "pass": ok, "excerpt": "", "reason": who}]}]

    with pytest.raises(ValueError, match="no adjudication"):
        merge(row("X", True), row("Y", False), {"decisions": []})
    done = merge(row("X", True), row("Y", False),
                 {"decisions": [{"id": "C1", "criterion_id": "b", "pass": False, "rule": "the rule"}]})
    decisions = {d["criterion_id"]: d for d in done[0]["decisions"]}
    assert decisions["a"]["pass"] is True and decisions["b"]["pass"] is False
    assert "the rule" in decisions["b"]["reason"] and done[0]["reviewer"] == "X + Y (adjudicated)"


def test_a_literal_decimal_allows_trailing_zeros_only_and_text_tolerance_is_read():
    from prepare_heldout import convert_fact

    fact, how = convert_fact(_fact(expected_value=12.5, tolerance="exact"), "12.50")
    assert how == "number" and fact["tolerance"] == 0
    item = _item(fact, "12.50")
    for text, ok in (("12.5 each", True), ("12.50 each", True), ("12.55 each", False), ("112.5 each", False)):
        assert hard_score(item, {"kind": "answer", "text": text}, "2026-04-01")["pass"] is ok, text
    assert convert_fact(_fact(expected_value=12.5, tolerance="+/- 0.5 pieces"), "12.5")[1] == "judge"
