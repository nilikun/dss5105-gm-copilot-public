"""Watches, alerts and briefings over simulated days: fire on the right day, once, and stay quiet otherwise.

    uv run --project backend python eval/run_scenarios.py --output eval/results/scenarios/v1.json

Deterministic, no LLM and no API cost: this is code, so one run is the result. Expected days are decided here before
the run: from a date stated in the case, or by recomputing the robust-z rule from the logged rows in this file rather
than by asking the tool under test. Never reads held-out files.
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.actions import gateway  # noqa: E402
from app.clock import DbClock  # noqa: E402
from app.db.database import connect, set_setting  # noqa: E402
from app.tools import call  # noqa: E402
from app.tools.base import ToolContext  # noqa: E402
from app.workflows import briefing, scheduler  # noqa: E402

DAYS = 14


def fresh(scenario: str):
    db = connect()
    db.execute("UPDATE clock_state SET scenario = ? WHERE id = 1", (scenario,))
    db.commit()
    return db, DbClock(db)


def propose(db, clock, **args):
    res, _ = call(ToolContext(db, clock, "scenario-eval"), "propose_watch", args)
    return res


def set_watch(db, clock, **args) -> str:
    res = propose(db, clock, **args)
    gateway.confirm(db, clock, res.data["proposal_id"])
    return db.execute("SELECT watch_id FROM watches ORDER BY created_at DESC, rowid DESC").fetchone()[0]


def fired_dates(db, watch_id: str) -> list[str]:
    rows = db.execute("SELECT created_at FROM notifications WHERE kind = 'watch' AND source_id = ? "
                      "ORDER BY notification_id", (watch_id,)).fetchall()
    return [str(r[0])[:10] for r in rows]


def status(db, watch_id: str) -> str:
    return db.execute("SELECT status FROM watches WHERE watch_id = ?", (watch_id,)).fetchone()[0]


def low_days(db, stage: str) -> list[str]:
    """Days from 1 Apr below the briefing tier, recomputed here: median and 1.4826 x MAD of 20 prior days."""
    rows = db.execute("SELECT date, pieces_completed FROM production_log WHERE stage = ? ORDER BY date",
                      (stage,)).fetchall()
    series = [(r[0], r[1]) for r in rows if date.fromisoformat(r[0]).weekday() != 6]
    low = []
    for i, (day, value) in enumerate(series):
        if day < "2026-04-01":
            continue
        window = [v for _, v in series[i - 20:i]]
        median = statistics.median(window)
        sigma = 1.4826 * statistics.median(abs(v - median) for v in window)
        if sigma and (value - median) / sigma < -1.75:
            low.append(day)
    return low


def next_boundary_after(day: str) -> str:
    """Data for a day arrives at 07:00 on the next day."""
    return date.fromordinal(date.fromisoformat(day).toordinal() + 1).isoformat()


def case(name, passed, expected, observed):
    return {"case": name, "pass": bool(passed), "expected": expected, "observed": observed}


# ------------------------------------------------------------------------------------------- watches


def stuck_order_fires_on_the_date():
    db, clock = fresh("packing_drop")
    w = set_watch(db, clock, type="order_stage_unchanged", order_id="ORD-120", by="2026-04-03")
    scheduler.advance(db, days=DAYS)
    seen = fired_dates(db, w)
    return case("Stuck order: fires on the stated date, once", seen == ["2026-04-03"], ["2026-04-03"], seen)


def moving_order_does_not_fire():
    control, _ = fresh("assembly_recovers")
    open_orders = {r[0]: r[1] for r in control.execute("SELECT order_id, current_stage FROM orders "
                                                       "WHERE status = 'IN_PROGRESS'")}
    scheduler.advance(control, days=5)
    moved = [o for o, s in open_orders.items()
             if control.execute("SELECT current_stage FROM orders WHERE order_id = ?", (o,)).fetchone()[0] != s]
    order = sorted(moved)[0]
    db, clock = fresh("assembly_recovers")
    w = set_watch(db, clock, type="order_stage_unchanged", order_id=order, by="2026-04-06")
    scheduler.advance(db, days=DAYS)
    seen = fired_dates(db, w)
    return case(f"Moving order ({order}): stays silent", not seen, [], seen)


def order_not_complete_fires_only_if_open():
    db, clock = fresh("packing_drop")
    w = set_watch(db, clock, type="order_not_complete", order_id="ORD-120", by="2026-04-04")
    scheduler.advance(db, days=DAYS)
    seen = fired_dates(db, w)
    return case("Order not complete by the date: fires then, once", seen == ["2026-04-04"], ["2026-04-04"], seen)


def stage_watch_matches_recomputed_low_days(scenario, stage):
    db, clock = fresh(scenario)
    w = set_watch(db, clock, type="stage_below_normal", stage=stage, tier="briefing")
    scheduler.advance(db, days=DAYS)
    expected = [next_boundary_after(d) for d in low_days(db, stage)]
    seen = fired_dates(db, w)
    return case(f"{scenario}: {stage} watch fires once per low day, on the morning its data arrives", seen == expected,
                expected, seen)


def reminder_fires_at_its_time_once():
    db, clock = fresh("baseline")
    w = set_watch(db, clock, type="reminder", at="2026-04-02T15:00", text="Call the customer")
    scheduler.advance(db, days=1, hours=7)  # 2 Apr 14:00: not yet
    before = fired_dates(db, w)
    scheduler.advance(db, hours=2)  # 2 Apr 16:00
    scheduler.advance(db, days=3)
    seen = fired_dates(db, w)
    return case("Timed reminder: not before its time, then once", not before and seen == ["2026-04-02"],
                {"before": [], "after": ["2026-04-02"]}, {"before": before, "after": seen})


def conditional_reminder(scenario, stage, should_fire):
    db, clock = fresh(scenario)
    # packing_drop lowers PACKING from 2 Apr, so its data shows the drop on the morning of 3 Apr
    w = set_watch(db, clock, type="reminder", at="2026-04-03", stage=stage, text=f"{stage} still behind")
    scheduler.advance(db, days=4)
    seen = fired_dates(db, w)
    ok = bool(seen) == should_fire and len(seen) <= 1
    verb = "fires" if should_fire else "stays silent"
    return case(f"Reminder 'if {stage} is still behind' in {scenario}: {verb}", ok, should_fire, seen)


def watch_on_completed_order_is_refused():
    db, clock = fresh("baseline")
    res = propose(db, clock, type="order_stage_unchanged", order_id="ORD-058", by="2026-04-03")
    count = db.execute("SELECT COUNT(*) FROM watches").fetchone()[0]
    return case("Watch on a completed order (ORD-058): refused at the proposal", not res.ok and count == 0,
                {"ok": False, "watches": 0}, {"ok": res.ok, "watches": count})


def unconfirmed_watch_never_fires():
    db, clock = fresh("packing_drop")
    propose(db, clock, type="order_stage_unchanged", order_id="ORD-120", by="2026-04-03")
    scheduler.advance(db, days=5)
    seen = db.execute("SELECT COUNT(*) FROM notifications WHERE kind = 'watch'").fetchone()[0]
    return case("Proposed but not confirmed: never fires", seen == 0, 0, seen)


def cancelled_watch_never_fires():
    db, clock = fresh("packing_drop")
    w = set_watch(db, clock, type="order_stage_unchanged", order_id="ORD-120", by="2026-04-03")
    gateway.cancel_watch_by_manager(db, clock, w)
    scheduler.advance(db, days=5)
    seen = fired_dates(db, w)
    return case("Cancelled before its date: never fires", not seen and status(db, w) == "cancelled", [], seen)


def rewind_does_not_repeat_a_fired_watch():
    db, clock = fresh("packing_drop")
    w = set_watch(db, clock, type="order_stage_unchanged", order_id="ORD-120", by="2026-04-03")
    scheduler.advance(db, days=5)
    scheduler.goto(db, datetime.fromisoformat("2026-04-02T07:00"))
    gone = db.execute("SELECT COUNT(*) FROM watches WHERE watch_id = ?", (w,)).fetchone()[0]
    scheduler.goto(db, datetime.fromisoformat("2026-04-06T07:00"))
    repeats = db.execute("SELECT COUNT(*) FROM notifications WHERE kind = 'watch'").fetchone()[0]
    return case("Rewind then replay: a watch set 'in the future' does not fire again", gone == 0 and repeats == 0,
                {"watch_after_rewind": 0, "alerts_after_replay": 0}, {"watch_after_rewind": gone,
                                                                     "alerts_after_replay": repeats})


# ------------------------------------------------------------------------------------------- alert load


def alert_load(scenario: str) -> dict:
    db, _clock = fresh(scenario)
    set_setting(db, "interrupt_cap", 3)
    scheduler.advance(db, days=DAYS)
    rows = db.execute("SELECT priority, kind, created_at FROM notifications WHERE kind != 'watch'").fetchall()
    by_day: dict[str, int] = {}
    for r in rows:
        if r["priority"] == "P1":
            by_day[str(r["created_at"])[:10]] = by_day.get(str(r["created_at"])[:10], 0) + 1
    return {"scenario": scenario, "days": DAYS, "interrupts": sum(r["priority"] == "P1" for r in rows),
            "to_the_briefing": sum(r["priority"] != "P1" for r in rows), "days_interrupted": len(by_day),
            "most_interrupts_in_one_day": max(by_day.values(), default=0)}


# ------------------------------------------------------------------------------------------- briefings


def items(structured: dict) -> list[str]:
    return [i["text"] for section in ("yesterday", "at_risk") for i in structured[section]]


SIGNALS_DAY_0 = {
    "ASSEMBLY output drop": ("ASSEMBLY",),
    "Overdue orders, worst first (ORD-107)": ("past due", "ORD-107"),
    "Due today and likely late (ORD-029)": ("ORD-029",),
    "Customer slipping (TrendCart)": ("TrendCart",),
    "Orders gone quiet (ORD-002, ORD-005)": ("ORD-002", "ORD-005"),
}
SIGNALS_SCENARIO = [
    ("packing_drop", 1, "PACKING drop reported the next morning", ("PACKING",), True),
    ("trendcart_reorder", 3, "New TrendCart reorder (ORD-121) among the risks", ("ORD-121",), None),
    ("assembly_recovers", 6, "ASSEMBLY drop no longer reported after recovery", ("ASSEMBLY made",), False),
]


def briefing_day_0() -> dict:
    db, clock = fresh("baseline")
    b = briefing.ensure(db, clock)["structured"]
    all_text = " ".join(items(b) + [i["text"] for i in b["decisions"]])
    found = {name: all(word in all_text for word in words) for name, words in SIGNALS_DAY_0.items()}
    listed = items(b)
    matched = sum(any(all(w in t for w in words) or any(w in t for w in words) for words in SIGNALS_DAY_0.values())
                  for t in listed)
    return {"found": found, "recall": f"{sum(found.values())}/{len(found)}", "items_on_the_page": len(listed),
            "items_tied_to_a_planted_signal": matched, "suppressed": b.get("suppressed_findings")}


def briefing_scenarios() -> list[dict]:
    out = []
    for scenario, days, name, words, in_yesterday in SIGNALS_SCENARIO:
        db, clock = fresh(scenario)
        scheduler.advance(db, days=days)
        b = briefing.ensure(db, clock)["structured"]
        text = " ".join(items(b) + [i["text"] for i in b["decisions"]])
        present = any(w in text for w in words)
        passed = present if in_yesterday is not False else not present
        out.append({"case": name, "scenario": scenario, "briefing_date": b["date"], "pass": passed})
    return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    watches = [
        stuck_order_fires_on_the_date(),
        moving_order_does_not_fire(),
        order_not_complete_fires_only_if_open(),
        stage_watch_matches_recomputed_low_days("packing_drop", "PACKING"),
        stage_watch_matches_recomputed_low_days("baseline", "ASSEMBLY"),
        stage_watch_matches_recomputed_low_days("assembly_recovers", "ASSEMBLY"),
        reminder_fires_at_its_time_once(),
        conditional_reminder("packing_drop", "PACKING", True),
        conditional_reminder("baseline", "PACKING", False),
        watch_on_completed_order_is_refused(),
        unconfirmed_watch_never_fires(),
        cancelled_watch_never_fires(),
        rewind_does_not_repeat_a_fired_watch(),
    ]
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                            cwd=ROOT).stdout.strip()
    result = {"commit": commit, "days_simulated": DAYS, "watch_cases": watches,
              "watch_cases_passed": f"{sum(c['pass'] for c in watches)}/{len(watches)}",
              "alert_load": [alert_load(s) for s in ("baseline", "assembly_recovers", "packing_drop",
                                                     "trendcart_reorder")],
              "briefing_day_0": briefing_day_0(), "briefing_scenarios": briefing_scenarios()}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for c in watches:
        detail = "" if c["pass"] else f"| expected {c['expected']} observed {c['observed']}"
        print("PASS" if c["pass"] else "FAIL", c["case"], detail)
    print(result["watch_cases_passed"])
    for row in result["alert_load"]:
        print(row)
    print(json.dumps(result["briefing_day_0"], ensure_ascii=False))
    for row in result["briefing_scenarios"]:
        print(row)


if __name__ == "__main__":
    main()
