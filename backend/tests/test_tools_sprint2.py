"""Sprint 2 tools, checked against the independent pandas ground truth in eval/ground_truth/dev_truth.py."""

import importlib.util
from datetime import datetime

import pytest

from app.actions import gateway
from app.clock import SimClock
from app.config import DATA_DIR, DATASET_TODAY, REPO_DIR
from app.db.database import connect, loads
from app.domain import watches
from app.tools import REGISTRY, call, function_schemas
from app.tools.base import ErrorCode, ToolContext

_spec = importlib.util.spec_from_file_location("dev_truth", REPO_DIR / "eval" / "ground_truth" / "dev_truth.py")
gt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gt)


@pytest.fixture
def fresh():
    """A private database for tests that change state."""
    return ToolContext(db=connect(DATA_DIR), clock=SimClock.at(DATASET_TODAY))


def run(ctx, name, **args):
    res, _ = call(ctx, name, args)
    return res


# ----------------------------------------------------------------- registry
def test_all_18_tools_registered_with_schemas():
    assert len(REGISTRY) == 19
    kinds = {}
    for s in REGISTRY.values():
        kinds[s.kind] = kinds.get(s.kind, 0) + 1
    assert kinds == {"retrieval": 9, "judgement": 2, "tracing": 1, "discovery": 1, "feasibility": 1, "action": 5}
    for schema in function_schemas():
        assert schema["type"] == "function" and schema["parameters"]["type"] == "object" and schema["description"]


def test_invalid_arguments_become_results_not_exceptions(ctx):
    res = run(ctx, "estimate_feasibility", pieces=-5, due_date="2026-04-25")
    assert not res.ok and res.error.code == ErrorCode.INVALID_ARGUMENT
    res = run(ctx, "no_such_tool")
    assert not res.ok


# ----------------------------------------------------------------- get_workshops
def test_accessory_workshops_exclude_suspended(ctx):
    res = run(ctx, "get_workshops", makes="ACCESSORIES")
    assert {w["name"] for w in res.data["workshops"]} == set(gt.gt_accessory_shops()["active"])
    res = run(ctx, "get_workshops", makes="ACCESSORIES", include_suspended=True)
    assert "OldMill" in {w["name"] for w in res.data["workshops"]} and res.warnings


def test_workshop_by_name(ctx):
    res = run(ctx, "get_workshops", name_or_id="freshstart")
    assert res.data["workshops"][0]["max_batch_pieces"] == 300


# ----------------------------------------------------------------- describe_data_coverage
@pytest.mark.parametrize("topic, covered", [("revenue of the TrendCart orders", False),
                                            ("which worker is slowest on assembly", False),
                                            ("why did assembly drop", False),
                                            ("orders due next week", True),
                                            ("the weather in Singapore", "unknown")])
def test_coverage(ctx, topic, covered):
    res = run(ctx, "describe_data_coverage", topic=topic)
    assert res.data["covered"] == covered


def test_cost_is_answerable_margin_is_not(ctx):
    res = run(ctx, "describe_data_coverage", topic="margin if we send it to BudgetWorks")
    assert res.data["covered"] is False and "cost_per_piece" in res.data["closest_available"]


# ----------------------------------------------------------------- assess_order_risk
def test_risk_matches_ground_truth_for_every_open_order(ctx, orders_df):
    for oid in orders_df[orders_df.status == "IN_PROGRESS"].order_id:
        a = run(ctx, "assess_order_risk", order_id=oid).data["assessment"]
        g = gt.gt_risk(oid)
        assert (a["level"], a["p50_finish"], a["p80_finish"]) == (g["risk"], g["p50"], g["p80"]), oid


def test_risk_counts_and_quiet(ctx):
    d = run(ctx, "assess_order_risk").data
    assert d["counts"]["OVERDUE"] == 8 and d["counts"]["QUIET"] == 2
    assert run(ctx, "assess_order_risk", order_id="ORD-058").data["assessment"]["level"] == "COMPLETE"


# ----------------------------------------------------------------- estimate_feasibility
@pytest.mark.parametrize("category, product, pieces, due", [("TOPS", "hoodies", 800, "2026-04-25"),
                                                             ("ACCESSORIES", "scarves", 2000, "2026-04-10"),
                                                             ("ACCESSORIES", "beanies", 300, "2026-04-15"),
                                                             ("TOPS", "vests", 200, "2026-05-10")])
def test_feasibility_matches_ground_truth(ctx, category, product, pieces, due):
    d = run(ctx, "estimate_feasibility", product=product, pieces=pieces, due_date=due).data
    g = gt.gt_feasibility(category, pieces, due)
    assert d["verdict"] == g["verdict"]
    assert (d["in_house"]["p50_finish"], d["in_house"]["p80_finish"]) == (g["in_house_p50"], g["in_house_p80"])
    eligible = [w for w in d["workshops"] if w["eligible"]]
    assert sorted(eligible, key=lambda w: (w["finish_date"], w["defect_rate"]))[0]["finish_date"] == g["best_finish"]
    excluded = {w["workshop"] for w in d["workshops"] if not w["eligible"]}
    assert set(g["excluded"]) <= excluded


def test_fastest_workshop_for_1500_crewnecks(ctx):
    d = run(ctx, "estimate_feasibility", product="crewnecks", pieces=1500, due_date="2026-04-30").data
    g = gt.gt_fastest_workshop("TOPS", 1500)
    assert d["fastest_eligible_workshop"] == g["first"]
    fresh = next(w for w in d["workshops"] if w["workshop"] == "FreshStart")
    assert not fresh["eligible"] and "batch cap" in fresh["reason_ineligible"]


def test_no_deadline_ranks_by_earliest_and_gives_cost(ctx):
    d = run(ctx, "estimate_feasibility", product="crewnecks", pieces=1500).data
    assert d["verdict"] == "no deadline given" and d["request"]["due_date"] is None
    assert d["fastest_eligible_workshop"] == gt.gt_fastest_workshop("TOPS", 1500)["first"]
    budget = next(w for w in run(ctx, "estimate_feasibility", product="hoodies", pieces=800).data["workshops"]
                  if w["workshop"] == "BudgetWorks")
    assert budget["cost"] == gt.gt_subcontract_cost("BudgetWorks", 800)["cost"]
    quick = next(w for w in d["workshops"] if w["workshop"] == "QuickStitch")
    assert quick["defect_rate_pct"] == 12.0  # data card: 0.12


def test_unknown_product(ctx):
    res = run(ctx, "estimate_feasibility", product="jackets", pieces=500, due_date="2026-04-30")
    assert not res.ok and res.error.code == ErrorCode.OUT_OF_COVERAGE


# ----------------------------------------------------------------- scan_exceptions
def test_scan_finds_the_planted_signals(ctx):
    d = run(ctx, "scan_exceptions").data
    top = d["findings"]
    kinds = [f["kind"] for f in top]
    titles = " ".join(f["title"] + " " + f["detail"] for f in top)
    planted = {"assembly drop": "stage_drop" in kinds and "ASSEMBLY" in titles,
               "overdue orders": "overdue" in kinds,
               "quiet orders": "quiet" in kinds or ("ORD-002" in titles and "ORD-005" in titles),
               "TrendCart": "TrendCart" in titles,
               "assembly pile-up": "ASSEMBLY" in titles and "open pieces" in titles}
    assert sum(planted.values()) >= 4, planted
    assert len(top) == 5 and top == sorted(top, key=lambda f: -f["score"])
    overdue = next(f for f in top if f["kind"] == "overdue")
    assert set(overdue["entities"]) == set(gt.gt_overdue()["ids"])


# ----------------------------------------------------------------- get_evidence / get_activity
def test_evidence_roundtrip(ctx):
    eid = run(ctx, "get_order", order_id="ORD-120").evidence[0].id
    d = run(ctx, "get_evidence", evidence_ids=[eid]).data
    assert d["evidence"][0]["rows"][0]["order_id"] == "ORD-120"
    assert not run(ctx, "get_evidence", evidence_ids=["E999999"]).ok


def test_activity_empty_is_an_answer(fresh):
    d = run(fresh, "get_activity").data
    assert all(v == 0 for v in d["counts"].values())


# ----------------------------------------------------------------- actions: propose → confirm → undo
def test_watch_on_completed_order_is_rejected(fresh):
    res = run(fresh, "propose_watch", type="order_stage_unchanged", order_id="ORD-058", by="2026-04-02")
    assert not res.ok and res.error.code == ErrorCode.PRECONDITION_FAILED and "2026-03-12" in res.error.message


def test_watch_full_lifecycle(fresh):
    res = run(fresh, "propose_watch", type="order_stage_unchanged", order_id="ORD-120", by="2026-04-03")
    assert res.ok and res.data["requires_confirmation"] and "ASSEMBLY" in res.data["preview"]
    aid = res.data["proposal_id"]
    assert fresh.db.execute("SELECT COUNT(*) FROM watches").fetchone()[0] == 0  # nothing happens before confirm
    done = gateway.confirm(fresh.db, fresh.clock, aid)
    w = dict(fresh.db.execute("SELECT * FROM watches").fetchone())
    w["params"], w["snapshot"] = loads(w["params"]), loads(w["snapshot"])
    assert w["status"] == "active"
    assert watches.evaluate(fresh.db, w, datetime(2026, 4, 2, 7))["action"] == "none"
    fired = watches.evaluate(fresh.db, w, datetime(2026, 4, 3, 7))
    assert fired["action"] == "fire" and "ORD-120" in fired["body"]
    with pytest.raises(gateway.GatewayError):
        gateway.confirm(fresh.db, fresh.clock, aid)
    gateway.undo(fresh.db, fresh.clock, done["audit_id"])
    assert fresh.db.execute("SELECT status FROM watches").fetchone()[0] == "cancelled"


def test_message_draft_must_be_grounded(fresh):
    bad = run(fresh, "propose_message", order_id="ORD-002", body="ORD-002 is 300 pieces behind, due 2026-03-29.")
    assert not bad.ok and "300" in bad.error.message
    good = run(fresh, "propose_message", order_id="ORD-002")
    assert good.ok and "WASHING" in good.data["preview"] and "2026-03-23" in good.data["preview"]
    done = gateway.confirm(fresh.db, fresh.clock, good.data["proposal_id"])
    assert fresh.db.execute("SELECT status FROM outbox").fetchone()[0] == "in_outbox"
    gateway.undo(fresh.db, fresh.clock, done["audit_id"])
    assert fresh.db.execute("SELECT status FROM outbox").fetchone()[0] == "retracted"


def test_note_and_cancel(fresh):
    res = run(fresh, "propose_note", order_id="ORD-114", text="Customer agreed to a one-week delay")
    gateway.cancel(fresh.db, fresh.clock, res.data["proposal_id"])
    assert fresh.db.execute("SELECT COUNT(*) FROM notes").fetchone()[0] == 0
    res = run(fresh, "propose_note", order_id="ORD-114", text="Customer agreed to a one-week delay")
    gateway.confirm(fresh.db, fresh.clock, res.data["proposal_id"])
    notes = run(fresh, "get_order", order_id="ORD-114").data["notes"]
    assert notes and notes[0]["text"].startswith("Customer agreed")
