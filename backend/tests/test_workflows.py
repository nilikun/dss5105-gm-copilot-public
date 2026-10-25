"""Clock, data advancer, alert policy, watch engine and briefing — end to end on a scenario."""

import pytest

from app.actions import gateway
from app.clock import DbClock
from app.clock.advancer import list_scenarios
from app.config import DATA_DIR
from app.db.database import connect, set_setting
from app.tools import call
from app.tools.base import ToolContext
from app.workflows import briefing, scheduler


def fresh(scenario: str = "baseline"):
    db = connect(DATA_DIR)
    db.execute("UPDATE clock_state SET scenario = ? WHERE id = 1", (scenario,))
    db.commit()
    return db, DbClock(db)


def test_scenarios_load():
    names = {s.name for s in list_scenarios()}
    assert {"baseline", "assembly_recovers", "packing_drop", "trendcart_reorder"} <= names


def test_initial_briefing_covers_the_planted_signals():
    db, clock = fresh()
    b = briefing.ensure(db, clock)["structured"]
    text = " ".join(i["text"] for sec in ("yesterday", "at_risk", "decisions") for i in b[sec])
    assert "ASSEMBLY" in text and "past due" in text and "TrendCart" in text and "ORD-107" in text
    assert b["date"] == "2026-04-01" and b["evidence_ids"]


def test_watch_fires_and_packing_alert_in_scenario():
    db, clock = fresh("packing_drop")
    ctx = ToolContext(db, clock, "t1")
    res, _ = call(ctx, "propose_watch", {"type": "order_stage_unchanged", "order_id": "ORD-120", "by": "2026-04-03"})
    gateway.confirm(db, clock, res.data["proposal_id"])
    report = scheduler.advance(db, days=2)  # → Fri 2026-04-03 07:00
    assert report["to"] == "2026-04-03T07:00"
    days = [g["date"] for b in report["boundaries"] for g in b["generated"]]
    assert days == ["2026-04-01", "2026-04-02"]
    alerts = db.execute("SELECT priority, kind, title FROM notifications ORDER BY notification_id").fetchall()
    kinds = [(a["priority"], a["kind"], a["title"]) for a in alerts]
    assert any(k[1] == "stage_drop" and "PACKING" in k[2] and k[0] == "P1" for k in kinds), kinds
    assert any(k[1] == "watch" and "ORD-120" in k[2] and k[0] == "P1" for k in kinds), kinds
    assert db.execute("SELECT status FROM watches").fetchone()[0] == "fired"
    stage = db.execute("SELECT current_stage FROM orders WHERE order_id = 'ORD-120'").fetchone()[0]
    assert stage == "ASSEMBLY"  # the scenario holds it
    assert briefing.ensure(db, clock)["date"] == "2026-04-03"


def test_advancer_is_deterministic():
    outs = []
    for _ in range(2):
        db, _clock = fresh("baseline")
        scheduler.advance(db, days=3)
        outs.append(db.execute("SELECT date, stage, pieces_completed FROM production_log WHERE date >= '2026-04-01' "
                               "ORDER BY date, stage").fetchall())
    assert [tuple(r) for r in outs[0]] == [tuple(r) for r in outs[1]] and len(outs[0]) == 12


def test_sunday_is_zero_and_orders_complete_over_time():
    db, _clock = fresh("assembly_recovers")
    scheduler.advance(db, days=8)  # through Sun 5 Apr
    sunday = db.execute("SELECT SUM(pieces_completed) FROM production_log WHERE date = '2026-04-05'").fetchone()[0]
    assert sunday == 0
    done = db.execute("SELECT COUNT(*) FROM orders WHERE completed_date >= '2026-04-01'").fetchone()[0]
    assert done > 0


def test_new_order_arrives_in_reorder_scenario():
    db, _clock = fresh("trendcart_reorder")
    scheduler.advance(db, days=3)
    row = db.execute("SELECT * FROM orders WHERE order_id = 'ORD-121'").fetchone()
    assert row["customer"] == "TrendCart" and row["pieces"] == 1200 and row["order_date"] == "2026-04-02"


@pytest.mark.parametrize("cap", [0])
def test_interrupt_cap_downgrades_system_alerts(cap):
    db, _clock = fresh("packing_drop")
    set_setting(db, "interrupt_cap", cap)
    scheduler.advance(db, days=2)
    sys_p1 = db.execute("SELECT COUNT(*) FROM notifications WHERE priority = 'P1' AND kind != 'watch'").fetchone()[0]
    assert sys_p1 == 0
    assert db.execute("SELECT COUNT(*) FROM notifications WHERE body LIKE '%cap%'").fetchone()[0] > 0
