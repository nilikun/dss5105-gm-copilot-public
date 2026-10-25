"""Agent loop, verifier, repair, fallback, proposals, critic and budget — with a scripted LLM (no API calls)."""

import json

import pytest

from app.agent.runtime import Agent
from app.clock import SimClock
from app.config import DATA_DIR, DATASET_TODAY
from app.db.database import connect
from app.llm.base import BudgetExceeded
from app.llm.fake import ScriptedLLM


@pytest.fixture
def env():
    return connect(DATA_DIR), SimClock.at(DATASET_TODAY)


def outputs(inp):
    return [json.loads(i["output"]) for i in inp if i.get("type") == "function_call_output" and
            i["output"].startswith("{")]


def evidence_of(inp):
    return [e["id"] for o in outputs(inp) for e in o.get("evidence", [])]


ASSEMBLY_STEPS = [
    [("resolve_time", {"expression": "yesterday"})],
    [("compare_to_normal", {"stage": "ASSEMBLY", "on_date": "2026-03-31"})],
]


def grounded_reply(inp):
    return [("respond", {"kind": "answer",
                         "headline": "Not normal: 455 pieces on 31 Mar, 40.2% below the usual 761.5 — the 6th low "
                                     "day in a row.", "evidence_ids": evidence_of(inp)})]


def test_happy_path_and_trace(env):
    db, clock = env
    llm = ScriptedLLM(ASSEMBLY_STEPS + [grounded_reply])
    r = Agent(db, clock, llm).run("Was assembly's output yesterday normal?")
    assert r.kind == "answer" and r.grounded and r.verifier_rejections == 0 and r.evidence_ids
    assert [t["tool"] for t in r.tool_calls] == ["resolve_time", "compare_to_normal"]
    kinds = [row[0] for row in db.execute("SELECT kind FROM traces WHERE turn_id = ? ORDER BY seq", (r.turn_id,))]
    assert kinds[0] == "question" and kinds[-1] == "reply"
    assert {"plan", "action", "llm", "draft", "verifier"} <= set(kinds)
    assert db.execute("SELECT COUNT(*) FROM llm_usage").fetchone()[0] == 3


def test_unsupported_number_is_repaired(env):
    db, clock = env
    bad = [("respond", {"kind": "answer", "headline": "Assembly made about 300 fewer pieces than normal."})]
    llm = ScriptedLLM(ASSEMBLY_STEPS + [bad, grounded_reply])
    r = Agent(db, clock, llm).run("Was assembly's output yesterday normal?")
    assert r.kind == "answer" and r.verifier_rejections == 1
    rejection = llm.requests[3]["input"][0]["output"]
    assert "REJECTED" in rejection and "300" in rejection


def test_two_bad_drafts_fall_back_to_tool_output(env):
    db, clock = env
    bad = [("respond", {"kind": "answer", "headline": "Assembly made about 300 fewer pieces than normal."})]
    llm = ScriptedLLM(ASSEMBLY_STEPS + [bad, bad])
    r = Agent(db, clock, llm).run("Was assembly's output yesterday normal?")
    assert r.kind == "fallback" and "compare_to_normal" in r.details and "300" not in r.headline


def test_proposal_and_false_execution_claim(env):
    db, clock = env

    def claim_done(inp):
        pid = outputs(inp)[-1]["data"]["proposal_id"]
        return [("respond", {"kind": "propose", "headline": "The watch has been set.", "proposal_ids": [pid]})]

    def honest(inp):
        pid = db.execute("SELECT action_id FROM pending_actions").fetchone()[0]
        headline = "Proposed: alert you on 3 Apr if ORD-120 is still in ASSEMBLY. Confirm to activate it."
        return [("respond", {"kind": "propose", "headline": headline, "proposal_ids": [pid]})]

    llm = ScriptedLLM([[("resolve_time", {"expression": "Friday"})],
                       [("propose_watch", {"type": "order_stage_unchanged", "order_id": "ORD-120",
                                           "by": "2026-04-03"})], claim_done, honest])
    r = Agent(db, clock, llm).run("Tell me if ORD-120 hasn't moved by Friday.")
    assert r.kind == "propose" and r.verifier_rejections == 1 and r.proposals[0]["status"] == "pending"
    assert db.execute("SELECT COUNT(*) FROM watches").fetchone()[0] == 0  # nothing executed without confirmation


def test_clarify_needs_options(env):
    db, clock = env

    def ask(inp):
        cands = [c["order_id"] for o in outputs(inp) if o.get("error") for c in o["error"]["candidates"]]
        return [("respond", {"kind": "clarify", "headline": "TrendCart has 6 open orders — which one?",
                             "options": [{"label": c, "value": f"How is {c} doing?"} for c in cands]})]

    llm = ScriptedLLM([[("find_orders", {"customer": "TrendCart", "status": "OPEN", "expect_single": True})], ask])
    r = Agent(db, clock, llm).run("How is the TrendCart order doing?")
    assert r.kind == "clarify" and len(r.options) == 6


def test_respond_with_other_tools_is_ignored(env):
    db, clock = env
    llm = ScriptedLLM([[("resolve_time", {"expression": "yesterday"}),
                        ("respond", {"kind": "answer", "headline": "It was 2026-03-31."})],
                       lambda inp: [("respond", {"kind": "answer", "headline": "Yesterday was 31 March.",
                                                 "evidence_ids": []})]])
    r = Agent(db, clock, llm).run("What date was yesterday?")
    assert r.kind == "answer" and "IGNORED" in llm.requests[1]["input"][1]["output"]


def test_critic_revision(env):
    db, clock = env
    llm = ScriptedLLM(ASSEMBLY_STEPS + [grounded_reply, {"verdict": "revise", "issues": ["Say it is not normal."]},
                                        grounded_reply])
    r = Agent(db, clock, llm, critic_enabled=True).run("Was assembly's output yesterday normal?")
    assert r.kind == "answer" and r.critic["verdict"] == "revise" and r.llm_calls == 5


def test_budget_cap(env):
    db, clock = env
    with pytest.raises(BudgetExceeded):
        Agent(db, clock, ScriptedLLM(ASSEMBLY_STEPS), daily_budget=0).run("Was assembly normal yesterday?")


def test_history_and_focus(env):
    db, clock = env
    a = Agent(db, clock, ScriptedLLM(ASSEMBLY_STEPS + [grounded_reply]))
    r1 = a.run("Was assembly's output yesterday normal?")
    llm2 = ScriptedLLM([lambda inp: [("respond", {"kind": "refuse", "headline": "The data has no causes."})]])
    a2 = Agent(db, clock, llm2)
    a2.run("why?", conversation_id=r1.conversation_id)
    first = llm2.requests[0]["input"]
    assert first[0]["role"] == "user" and first[1]["role"] == "assistant" and first[-1]["content"] == "why?"


def test_negated_execution_wording_is_not_a_false_claim():
    from app.agent.verifier import claims_execution
    assert claims_execution("The watch has been set.")
    assert not claims_execution("Nothing has been sent yet — confirm to send it.")
    assert not claims_execution("It will be sent once you confirm; it has not been sent.")
    assert not claims_execution("8 chase-ups are drafted for confirmation; none has been sent.")  # red-team R11
    assert not claims_execution("The note hasn't been added; it is waiting for you.")
