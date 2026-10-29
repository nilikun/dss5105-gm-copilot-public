"""HTTP API end to end with a scripted LLM (no network)."""

import pytest
from fastapi.testclient import TestClient

from app.clock import DbClock
from app.db.database import open_db
from app.llm.fake import ScriptedLLM
from app.main import create_app
from app.tools import call
from app.tools.base import ToolContext


def make(tmp_path, steps=(), access_code=""):
    app = create_app(db_path=str(tmp_path / "gm.db"), llm=ScriptedLLM(list(steps)), access_code=access_code,
                     start_ticker=False)
    return app, TestClient(app)


def test_health_and_access_code(tmp_path):
    app, client = make(tmp_path, access_code="s3cret")
    with client:
        assert client.get("/api/health").json() == {"ok": True}
        assert client.get("/api/state").status_code == 401
        r = client.get("/api/state", headers={"X-Access-Code": "s3cret"})
        assert r.status_code == 200 and r.json()["now"] == "2026-04-01T07:00"


def test_briefing_and_tools(tmp_path):
    _, client = make(tmp_path)
    with client:
        b = client.get("/api/briefing").json()
        assert b["date"] == "2026-04-01" and b["structured"]["at_risk"]
        assert len(client.get("/api/tools").json()) == 19


def test_chat_streams_steps_and_reply(tmp_path):
    steps = [[("compare_to_normal", {"stage": "ASSEMBLY", "on_date": "2026-03-31"})],
             lambda inp: [("respond", {"kind": "answer", "headline": "Not normal: 455 pieces vs a usual 761.5."})]]
    _, client = make(tmp_path, steps)
    with client:
        r = client.post("/api/chat", json={"message": "Was assembly normal yesterday?"})
        assert r.status_code == 200
        body = r.text
        assert "event: step" in body and "event: reply" in body and '"kind": "answer"' in body
        turns = client.get("/api/traces").json()
        assert turns and turns[0]["steps"] >= 5
        events = client.get(f"/api/traces/{turns[0]['turn_id']}").json()
        assert {"question", "action", "verifier", "reply"} <= {e["kind"] for e in events}


def test_confirm_cancel_undo(tmp_path):
    app, client = make(tmp_path)
    with client:
        db = open_db(app.state.db_path)
        res, _ = call(ToolContext(db, DbClock(db), "t"), "propose_note", {"order_id": "ORD-114", "text": "ok"})
        aid = res.data["proposal_id"]
        assert [p["action_id"] for p in client.get("/api/proposals").json()] == [aid]
        done = client.post(f"/api/proposals/{aid}/confirm").json()
        assert client.post(f"/api/proposals/{aid}/confirm").status_code == 409
        assert client.post(f"/api/audit/{done['audit_id']}/undo").status_code == 200
        assert client.get("/api/audit").json()[0]["undone_at"]


def test_clock_advance_and_reset(tmp_path):
    _, client = make(tmp_path)
    with client:
        r = client.post("/api/clock/advance", json={"days": 2}).json()
        assert r["to"] == "2026-04-03T07:00"
        assert client.get("/api/clock").json()["data_through"] == "2026-04-02"
        assert client.post("/api/clock/reset", json={"scenario": "packing_drop"}).json()["now"] == "2026-04-01T07:00"
        assert client.get("/api/clock").json()["scenario"] == "packing_drop"
        assert client.post("/api/clock/reset", json={"scenario": "nope"}).status_code == 404


def test_settings_and_evidence_404(tmp_path):
    _, client = make(tmp_path)
    with client:
        assert client.patch("/api/settings", json={"critic_enabled": True}).json()["critic_enabled"] is True
        assert client.get("/api/evidence/E999").status_code == 404


@pytest.mark.parametrize("limit", [1])
def test_rate_limit(tmp_path, limit):
    steps = [lambda inp: [("respond", {"kind": "refuse", "headline": "No price data."})]] * 3
    app, client = make(tmp_path, steps)
    app.state.rate_limit = limit
    with client:
        assert client.post("/api/chat/sync", json={"message": "revenue?"}).status_code == 200
        assert client.post("/api/chat/sync", json={"message": "revenue?"}).status_code == 429


def test_rate_limit_per_visitor_behind_cloudflare(tmp_path):
    steps = [lambda inp: [("respond", {"kind": "refuse", "headline": "No price data."})]] * 3
    app, client = make(tmp_path, steps)
    app.state.rate_limit, app.state.trust_proxy = 1, True
    with client:
        ask = lambda ip: client.post("/api/chat/sync", json={"message": "revenue?"},  # noqa: E731
                                     headers={"CF-Connecting-IP": ip}).status_code
        assert ask("203.0.113.1") == 200
        assert ask("203.0.113.2") == 200   # a different visitor has their own window
        assert ask("203.0.113.1") == 429
