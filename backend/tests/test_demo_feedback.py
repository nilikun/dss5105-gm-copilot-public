"""Fixes from the demo usability review (29 Oct): briefing refresh, deleting chats, read/unread
alerts, jumping the clock (also backwards), cancelling watches from the UI, outsourcing as an action, and a fixed
layout for feasibility answers. Independent checks use the CSVs (pandas) or the database directly."""

import sys
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.agent import feasibility_view
from app.agent.respond import RespondArgs
from app.agent.runtime import Agent
from app.agent.verifier import verify
from app.clock import DbClock, SimClock
from app.db.database import connect, reset_in_place
from app.llm import budget
from app.llm.base import Usage
from app.llm.fake import ScriptedLLM
from app.main import create_app
from app.tools import call
from app.tools.base import ErrorCode, ToolContext
from app.workflows import scheduler

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "eval" / "ground_truth"))
import dev_truth as gt  # noqa: E402

H = {"X-Access-Code": ""}


def make(tmp_path, steps=()):
    app = create_app(db_path=str(tmp_path / "gm.db"), llm=ScriptedLLM(list(steps)), access_code="",
                     start_ticker=False)
    return app, TestClient(app)


def snapshot(db):
    return ([tuple(r) for r in db.execute("SELECT * FROM production_log ORDER BY date, stage")],
            [tuple(r) for r in db.execute("SELECT * FROM orders ORDER BY order_id")])


# ----------------------------------------------------------------- resets keep spend; rewinds keep chats
def test_reset_keeps_spend_traces_and_settings():
    db = connect()
    budget.record(db, "m", "agent", "t1", Usage(1000, 0, 100), 5)
    db.execute("INSERT INTO settings (key, value) VALUES ('interrupt_cap', '2')")
    db.execute("INSERT INTO conversations (conversation_id, created_at, title) VALUES ('c1', 0, 'hi')")
    db.commit()
    spent = budget.summary(db)["cost_usd"]
    reset_in_place(db, "baseline")
    assert budget.summary(db)["cost_usd"] == spent > 0          # the daily cap cannot be lifted by a reset
    assert db.execute("SELECT value FROM settings WHERE key = 'interrupt_cap'").fetchone()[0] == "2"
    assert db.execute("SELECT COUNT(*) FROM conversations").fetchone()[0] == 0   # a scenario start clears chats
    assert db.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == len(gt.orders)


def test_goto_forward_back_replays_identically():
    db = connect()
    scheduler.start_day(db)
    db.execute("INSERT INTO conversations (conversation_id, created_at, title) VALUES ('c1', 0, 'hi')")
    db.commit()
    scheduler.goto(db, datetime(2026, 4, 6, 9, 30))
    first = snapshot(db)
    back = scheduler.goto(db, datetime(2026, 4, 2, 7, 0))
    assert back["rewound"] and DbClock(db).now() == datetime(2026, 4, 2, 7, 0)
    assert db.execute("SELECT MAX(date) FROM production_log").fetchone()[0] == "2026-04-01"
    assert db.execute("SELECT COUNT(*) FROM conversations").fetchone()[0] == 1   # chats survive a rewind
    scheduler.goto(db, datetime(2026, 4, 6, 9, 30))
    assert snapshot(db) == first                                    # seeded days replay byte for byte
    with pytest.raises(ValueError):
        scheduler.goto(db, datetime(2026, 3, 31, 7, 0))            # nothing is simulated before the dataset's today


def test_rewind_never_reuses_evidence_ids():
    db = connect()
    scheduler.start_day(db)
    ctx = ToolContext(db, DbClock(db), "t1")
    old = call(ctx, "compare_to_normal", {"stage": "ASSEMBLY"})[0].evidence[0].id
    scheduler.goto(db, datetime(2026, 4, 3, 7, 0))
    scheduler.goto(db, datetime(2026, 4, 1, 7, 0))
    new = call(ToolContext(db, DbClock(db), "t2"), "compare_to_normal", {"stage": "ASSEMBLY"})[0].evidence[0].id
    assert new != old and db.execute("SELECT 1 FROM evidence WHERE evidence_id = ?", (old,)).fetchone()


def test_clock_api_goto_and_real_mode_info(tmp_path):
    _, client = make(tmp_path)
    with client:
        r = client.post("/api/clock/goto", json={"when": "2026-04-03T07:00"})
        assert r.status_code == 200 and r.json()["now"] == "2026-04-03T07:00" and not r.json()["rewound"]
        r = client.post("/api/clock/goto", json={"when": "2026-04-01T12:00"})
        assert r.json()["rewound"] and r.json()["data_through"] == "2026-03-31"
        assert client.post("/api/clock/goto", json={"when": "2026-01-15T07:00"}).status_code == 422
        info = client.post("/api/clock/mode", json={"mode": "real"}).json()
        assert info["mode"] == "real" and info["next_boundary"] == "2026-04-02T07:00"
        assert client.post("/api/clock/goto", json={"when": "2026-04-02T08:00"}).json()["mode"] == "sim"


# ----------------------------------------------------------------- chats, alerts, briefing
def test_delete_conversations(tmp_path):
    steps = [lambda inp: [("respond", {"kind": "refuse", "headline": "No price data."})]] * 2
    _, client = make(tmp_path, steps)
    with client:
        a = client.post("/api/chat/sync", json={"message": "revenue?"}).json()["conversation_id"]
        client.post("/api/chat/sync", json={"message": "margin?"})
        assert client.delete(f"/api/conversations/{a}").json() == {"deleted": a}
        assert [c["conversation_id"] for c in client.get("/api/conversations").json()] != [a]
        assert client.get(f"/api/conversations/{a}").json() == []
        assert client.delete(f"/api/conversations/{a}").status_code == 404
        assert client.get("/api/traces").json()                      # the AI execution log is kept
        assert client.delete("/api/conversations").json() == {"deleted": 1}


def test_alerts_can_be_marked_unread_again(tmp_path):
    _, client = make(tmp_path)
    with client:
        client.post("/api/clock/advance", json={"days": 2})
        ids = [n["notification_id"] for n in client.get("/api/notifications").json()]
        assert ids
        client.post("/api/notifications/read", json={})
        assert client.get("/api/state").json()["unread_alerts"] == 0
        client.post("/api/notifications/read", json={"ids": ids[:1], "read": False})
        assert client.get("/api/state").json()["unread_alerts"] == 1


def test_briefing_rebuild_clears_summary_and_force_rewrites(tmp_path):
    def summary(_inp):
        return "ASSEMBLY made 455 pieces on 2026-03-31."
    _, client = make(tmp_path, [summary, summary])
    with client:
        assert client.post("/api/briefing/narrate").json()["narrative_status"] == "ok"
        assert client.post("/api/briefing/narrate").json()["narrative_status"] == "ok"   # kept, no new call
        assert client.post("/api/briefing/narrate?force=true").json()["narrative"]       # second scripted step
        b = client.post("/api/briefing/rebuild").json()
        assert b["narrative"] is None and b["narrative_status"] == "pending"


# ----------------------------------------------------------------- watches: confirm or cancel without the chat
def test_cancel_watch_from_the_ui_is_audited_and_undoable(tmp_path):
    app, client = make(tmp_path)
    with client:
        from app.db.database import open_db
        db = open_db(app.state.db_path)
        r, _ = call(ToolContext(db, DbClock(db), "t1"), "propose_watch",
                    {"type": "order_stage_unchanged", "order_id": "ORD-120", "by": "2026-04-03"})
        pid = r.data["proposal_id"]
        assert client.get("/api/proposals").json()[0]["kind"] == "watch"   # shown on the Watches page as pending
        wid = client.post(f"/api/proposals/{pid}/confirm").json()["after"]["watch_id"]
        res = client.post(f"/api/watches/{wid}/cancel").json()
        assert res["kind"] == "cancel_watch" and client.get("/api/watches").json()[0]["status"] == "cancelled"
        assert client.post(f"/api/watches/{wid}/cancel").status_code == 409
        client.post(f"/api/audit/{res['audit_id']}/undo")
        assert client.get("/api/watches").json()[0]["status"] == "active"


# ----------------------------------------------------------------- outsourcing is an action
@pytest.fixture
def ctx():
    db = connect()
    return ToolContext(db, SimClock.at("2026-04-01"), "t1")


def test_propose_outsourcing_uses_the_workshop_card(ctx):
    r, _ = call(ctx, "propose_outsourcing", {"workshop": "SteadyHands", "pieces": 800, "product": "hoodies",
                                             "due_date": "2026-04-25"})
    assert r.ok and r.data["kind"] == "outsourcing" and r.evidence
    g = gt.gt_subcontract_cost("SteadyHands", 800)
    assert r.data["option"]["cost"] == g["cost"] and "1,040.00" in r.data["preview"]
    assert r.data["option"]["finish_date"] == next(o for o in call(ctx, "estimate_feasibility", {
        "pieces": 800, "product": "hoodies", "due_date": "2026-04-25"})[0].data["workshops"]
        if o["workshop"] == "SteadyHands")["finish_date"]


@pytest.mark.parametrize("args,code", [
    ({"workshop": "OldMill", "pieces": 200, "product": "scarves"}, ErrorCode.PRECONDITION_FAILED),     # suspended
    ({"workshop": "FreshStart", "pieces": 800, "product": "hoodies"}, ErrorCode.PRECONDITION_FAILED),  # batch cap
    ({"workshop": "Little Loom", "pieces": 300, "product": "hoodies"}, ErrorCode.PRECONDITION_FAILED), # category
    ({"workshop": "Nowhere", "pieces": 10, "product": "hoodies"}, ErrorCode.NOT_FOUND),
    ({"workshop": "W2", "pieces": 800, "product": "hoodies", "order_id": "ORD-999"}, ErrorCode.NOT_FOUND),
])
def test_propose_outsourcing_rejects_what_the_workshop_cannot_take(ctx, args, code):
    r, _ = call(ctx, "propose_outsourcing", args)
    assert not r.ok and r.error.code == code
    if code == ErrorCode.PRECONDITION_FAILED:
        assert r.error.candidates and all("finish_date" in c for c in r.error.candidates)
    assert ctx.db.execute("SELECT COUNT(*) FROM pending_actions").fetchone()[0] == 0


def test_outsourcing_confirm_goes_to_outbox_and_undo_retracts(tmp_path):
    app, client = make(tmp_path)
    with client:
        from app.db.database import open_db
        db = open_db(app.state.db_path)
        r, _ = call(ToolContext(db, DbClock(db), "t1"), "propose_outsourcing",
                    {"workshop": "GiantWeave", "pieces": 800, "product": "hoodies"})
        res = client.post(f"/api/proposals/{r.data['proposal_id']}/confirm").json()
        m = client.get("/api/outbox").json()[0]
        assert m["intent"] == "outsource" and m["recipient_role"] == "workshop" and m["order_id"] is None
        assert "GiantWeave" in m["body"] and "GiantWeave" in res["summary"]
        client.post(f"/api/audit/{res['audit_id']}/undo")
        assert client.get("/api/outbox").json()[0]["status"] == "retracted"


def test_agent_turns_a_draft_request_into_a_proposal():
    db = connect()
    clock = SimClock.at("2026-04-01")

    def respond(inp):
        pid = next(o for o in inp if o.get("type") == "function_call_output")["output"].split('"proposal_id": "')[1][:3]
        return [("respond", {"kind": "propose", "headline": "Outsourcing request to SteadyHands drafted.",
                             "proposal_ids": [pid]})]
    llm = ScriptedLLM([[("propose_outsourcing", {"workshop": "SteadyHands", "pieces": 800, "product": "hoodies",
                                                 "due_date": "2026-04-25"})], respond])
    reply = Agent(db, clock, llm).run("Draft an outsourcing order with SteadyHands for the 800 hoodies.")
    assert reply.kind == "propose" and reply.proposals[0]["kind"] == "outsourcing"


# ----------------------------------------------------------------- one layout for every estimate
def test_estimate_details_are_rendered_and_still_verified(ctx):
    res, _ = call(ctx, "estimate_feasibility", {"pieces": 800, "product": "hoodies", "due_date": "2026-04-25"})
    dump = res.model_dump(mode="json")
    draft = RespondArgs(kind="estimate", headline="Only with outsourcing: 800 hoodies by 2026-04-25.",
                        details="QuickStitch 1200 12% GiantWeave …")
    out = feasibility_view.apply(draft, [("estimate_feasibility", dump)])
    rows = [ln for ln in out.details.splitlines() if ln.startswith("| ") and not ln.startswith("| Workshop")]
    assert len(rows) == sum(o["eligible"] for o in dump["data"]["workshops"])
    assert "| SteadyHands | " in out.details and "Not eligible:" in out.details and dump["evidence"][0]["id"] \
        in out.evidence_ids
    v = verify(out, [dump], "A customer wants 800 hoodies by the 25th. Can we take it?",
               datetime(2026, 4, 1, 7), {e["id"] for e in dump["evidence"]}, ctx.db, "t1")
    assert v.ok, v.violations
    assert feasibility_view.apply(draft.model_copy(update={"kind": "answer"}), [("estimate_feasibility", dump)]) \
        .details == draft.details                                   # only estimates are rendered


def test_pending_watch_proposal_is_visible_when_asking_about_watches(ctx):
    """Red-team R12: after "tell me if ORD-120 hasn't moved", asking "is the watch set?" must see the proposal."""
    call(ctx, "propose_watch", {"type": "order_stage_unchanged", "order_id": "ORD-120", "by": "2026-04-03"})
    call(ctx, "propose_note", {"order_id": "ORD-120", "text": "Customer called."})
    r, _ = call(ctx, "get_activity", {"order_id": "ORD-120", "kind": "watch"})
    assert [p["kind"] for p in r.data["pending_proposals"]] == ["watch"] and r.data["watches"] == []
    assert [p["kind"] for p in call(ctx, "get_activity", {"order_id": "ORD-120"})[0].data["pending_proposals"]] \
        == ["watch", "note"]
    assert "pending_proposals" not in call(ctx, "get_activity", {"kind": "alert"})[0].data
