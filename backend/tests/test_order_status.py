"""Status completeness with adversarial drafts and independent public CSV references."""

import json
import sys
from datetime import date
from pathlib import Path

import pytest

from app.agent.runtime import Agent
from app.clock import SimClock
from app.config import DATA_DIR
from app.db.database import connect
from app.llm.fake import ScriptedLLM
from app.tools.base import ToolContext
from app.tools.retrieval.order_status import get_order_status, status_facts

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "eval"))
from step2_reference import reference, score  # noqa: E402

SUITE = json.loads((ROOT / "eval" / "fixtures" / "step2_order_status.json").read_text(encoding="utf-8"))
BAD_DRAFT = [("respond", {"kind": "answer", "headline": "Packing, 16 days late."})]


def patch_order(db, case):
    for field, value in case.get("override", {}).items():
        assert field in {"due_date", "current_stage", "completed_date"}
        db.execute(f"UPDATE orders SET {field} = ? WHERE order_id = ?", (value, case["order_id"]))
    db.commit()


@pytest.mark.parametrize("case", SUITE["cases"], ids=lambda case: case["id"])
@pytest.mark.parametrize("repeat", range(3))
def test_complete_status_despite_incomplete_draft(case, repeat):
    db, clock = connect(DATA_DIR), SimClock.at(SUITE["clock"])
    patch_order(db, case)
    context = []
    if case.get("context"):
        context = [[("get_order_status", {"order_id": case["context_order_id"]})], BAD_DRAFT]
    llm = ScriptedLLM(context + [[("get_order_status", case["tool_args"])], BAD_DRAFT])
    agent = Agent(db, clock, llm)
    cid = agent.run(case["context"]).conversation_id if context else None
    reply = agent.run(case["question"], cid)
    assert score(reference(case, SUITE["clock"]), reply.model_dump()) == []
    assert reply.grounded and reply.verifier_rejections == 0
    assert db.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == 0
    db.close()


@pytest.mark.parametrize("draft", [
    {"kind": "answer", "headline": "ORD-120 is in assembly, due 2026-03-17. 15 days overdue."},
    {"kind": "answer", "headline": "ORD-107 is complete.", "details": "Due date 2026-04-05.",
     "followups": ["Why is ORD-107 in washing?"]},
    {"kind": "refuse", "headline": "There is no data about this order."},
])
def test_wrong_order_date_stage_and_refusal_cannot_override_facts(draft):
    db = connect(DATA_DIR)
    llm = ScriptedLLM([[('get_order', {"order_id": "ORD-120"}),
                        ('get_order_status', {"order_id": "ORD-107"})], [("respond", draft)]])
    reply = Agent(db, SimClock.at(SUITE["clock"]), llm).run("Status of ORD-107?")
    assert score(reference(SUITE["cases"][0], SUITE["clock"]), reply.model_dump()) == []
    assert not reply.followups and reply.evidence_ids == ["E2"]
    db.close()


def test_critic_cannot_remove_deadline():
    db = connect(DATA_DIR)
    llm = ScriptedLLM([[('get_order_status', {"order_id": "ORD-107"})], BAD_DRAFT,
                      {"verdict": "revise", "issues": ["Remove the deadline."]}, BAD_DRAFT])
    reply = Agent(db, SimClock.at(SUITE["clock"]), llm, critic_enabled=True).run("Status of ORD-107?")
    assert score(reference(SUITE["cases"][0], SUITE["clock"]), reply.model_dump()) == []
    assert reply.critic["verdict"] == "revise"
    db.close()


def test_ambiguous_lookup_cannot_be_resolved_by_model_guess():
    db = connect(DATA_DIR)
    llm = ScriptedLLM([[('get_order_status', {"customer": "TrendCart"})],
                      [('get_order_status', {"order_id": "ORD-120"})], BAD_DRAFT])
    reply = Agent(db, SimClock.at(SUITE["clock"]), llm).run("How is the TrendCart order doing?")
    assert score(reference(SUITE["cases"][5], SUITE["clock"]), reply.model_dump()) == []
    db.close()


def test_wrong_explicit_identifier_requests_clarification():
    db = connect(DATA_DIR)
    llm = ScriptedLLM([[('get_order_status', {"order_id": "ORD-120"})], BAD_DRAFT])
    reply = Agent(db, SimClock.at(SUITE["clock"]), llm).run("Status of ORD-107?")
    assert reply.kind == "clarify" and "due" not in reply.headline.lower()
    db.close()


@pytest.mark.parametrize("as_of, days, direction", [("2026-03-15", 1, "remaining"),
                                                    ("2026-03-16", 0, "due_today"),
                                                    ("2026-03-17", 1, "overdue"),
                                                    ("2027-04-01", 381, "overdue")])
def test_timing_uses_dataset_clock(as_of, days, direction):
    db = connect(DATA_DIR)
    res = get_order_status(ToolContext(db, SimClock.at(as_of)), order_id="107")
    facts = res.data["status_facts"]
    assert (facts["days"], facts["timing"], facts["as_of"]) == (days, direction, as_of)
    db.close()


@pytest.mark.parametrize("due", [None, "", "not-a-date", "2026-02-30"])
def test_missing_invalid_due_is_not_overdue(due):
    row = {"order_id": "ORD-107", "status": "IN_PROGRESS", "current_stage": "PACKING", "due_date": due}
    facts = status_facts(row, date(2026, 4, 1))
    assert facts.due_date is None and facts.days is None and facts.timing is None
    assert "due_date" in facts.unavailable


@pytest.mark.parametrize("completed, direction, days", [(None, None, None), ("2026-04-02", None, None),
    ("2026-03-15", "early", 1), ("2026-03-16", "on_time", 0), ("2026-03-17", "late", 1)])
def test_completion_uses_dates_not_stale_days_late(completed, direction, days):
    row = {"order_id": "ORD-107", "status": "COMPLETE", "current_stage": "COMPLETE", "due_date": "2026-03-16",
           "completed_date": completed, "days_late": 999}
    facts = status_facts(row, date(2026, 4, 1))
    assert (facts.timing, facts.days) == (direction, days)


def test_id_and_description_must_agree():
    db = connect(DATA_DIR)
    res = get_order_status(ToolContext(db, SimClock.at(SUITE["clock"])), order_id="107", customer="TrendCart")
    assert not res.ok and res.error.code.value == "NOT_FOUND"
    db.close()


def test_all_source_orders_match_independent_contracts():
    from app.agent.order_status import render

    db = connect(DATA_DIR)
    clock = SimClock.at(SUITE["clock"])
    for row in db.execute("SELECT order_id FROM orders"):
        oid = row[0]
        result = get_order_status(ToolContext(db, clock), order_id=oid)
        reply = render([("get_order_status", result.model_dump(mode="json"))], f"Status of {oid}?", clock.today())
        assert score(reference({"order_id": oid}, SUITE["clock"]), reply.model_dump()) == [], oid
    db.close()


def test_more_than_six_candidates_remain_visible():
    from app.agent.order_status import clarification

    candidates = [{"order_id": f"ORD-{i:03d}"} for i in range(1, 10)]
    reply = clarification(candidates)
    assert len(reply.options) == 6
    assert all(c["order_id"] in reply.details for c in candidates)


def test_missing_completion_is_disclosed_in_final_answer():
    db = connect(DATA_DIR)
    db.execute("UPDATE orders SET completed_date = NULL WHERE order_id = 'ORD-058'")
    db.commit()
    llm = ScriptedLLM([[('get_order_status', {"order_id": "ORD-058"})], BAD_DRAFT])
    reply = Agent(db, SimClock.at(SUITE["clock"]), llm).run("Status of ORD-058?")
    case = {"order_id": "ORD-058", "override": {"completed_date": None}}
    assert score(reference(case, SUITE["clock"]), reply.model_dump()) == []
    assert "20" not in reply.headline.replace("2026-02-20", "")
    db.close()


def test_invalid_model_drafts_still_leave_verified_status_available():
    from app.config import MAX_REPAIRS, MAX_TOOL_STEPS

    db = connect(DATA_DIR)
    invalid = [("respond", {"kind": "not-a-valid-kind", "headline": "irrelevant"})]
    llm = ScriptedLLM([[('get_order_status', {"order_id": "ORD-107"})]] +
                      [invalid] * (MAX_TOOL_STEPS + MAX_REPAIRS + 1))
    reply = Agent(db, SimClock.at(SUITE["clock"]), llm).run("Status of ORD-107?")
    assert score(reference(SUITE["cases"][0], SUITE["clock"]), reply.model_dump()) == []
    db.close()


def test_mixed_action_turn_keeps_proposal_confirmation():
    db = connect(DATA_DIR)

    def propose_reply(inp):
        pid = db.execute("SELECT action_id FROM pending_actions").fetchone()[0]
        return [("respond", {"kind": "propose", "headline": "Confirm to add the note.", "proposal_ids": [pid]})]

    llm = ScriptedLLM([[('get_order_status', {"order_id": "ORD-107"})],
                      [('propose_note', {"order_id": "ORD-107", "text": "Customer called."})], propose_reply])
    reply = Agent(db, SimClock.at(SUITE["clock"]), llm).run("Check ORD-107 and add a note that the customer called.")
    assert reply.kind == "propose" and reply.proposals[0]["status"] == "pending"
    assert db.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == 0
    db.close()


def test_historical_d02_omission_is_repaired_on_status_route():
    """Replay the actual published failing prose, not just a made-up incomplete sentence."""
    archive = ROOT / 'eval/results/20261015-2219-dev-gpt-5.6-luna-base-final1/results.jsonl'
    old = next(json.loads(line)["reply"] for line in archive.read_text(encoding="utf-8").splitlines()
               if json.loads(line)["id"] == "D02")
    ref = reference(SUITE["cases"][0], SUITE["clock"])
    assert "deadline" in score(ref, old)
    draft = {k: old[k] for k in ("kind", "headline", "details", "evidence_ids", "followups")}
    db = connect(DATA_DIR)
    llm = ScriptedLLM([[('get_order_status', SUITE["cases"][0]["tool_args"])], [("respond", draft)]])
    reply = Agent(db, SimClock.at(SUITE["clock"]), llm).run(SUITE["cases"][0]["question"])
    assert score(ref, reply.model_dump()) == []
    assert "Due date 2026-03-16" in reply.headline and reply.evidence_ids == ["E1"]
    db.close()
