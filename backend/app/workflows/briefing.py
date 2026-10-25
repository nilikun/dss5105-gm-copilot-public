"""Morning briefing: a deterministic pipeline; the LLM only narrates (docs/PLAN.md §7).

collect → detect → rank (scan_exceptions) → structured JSON in three sections → LLM narrates the JSON only →
grounding check against the JSON → stored. If narration fails or is rejected, the structured briefing stands.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from typing import Any

from app.agent import prompts
from app.clock import Clock
from app.config import STAGES
from app.db.database import dumps, loads
from app.domain import grounding
from app.domain.calendar import days, previous_working_day
from app.llm import budget
from app.llm.base import LLMClient, LLMError
from app.tools import call
from app.tools.base import ToolContext


def build(db: sqlite3.Connection, clock: Clock) -> dict[str, Any]:
    now = clock.now()
    today = now.date()
    ctx = ToolContext(db, clock, f"briefing-{today.isoformat()}")
    yday = previous_working_day(today)
    evidence: list[str] = []

    def run(name: str, **args):
        res, _ = call(ctx, name, args)
        evidence.extend(e.id for e in res.evidence)
        return res

    yesterday: list[dict[str, Any]] = []
    last_log = db.execute("SELECT MAX(date) FROM production_log").fetchone()[0]
    day = yday.isoformat() if yday.isoformat() <= last_log else last_log
    normal = run("compare_to_normal", stage="ALL", on_date=day)
    abnormal = [r for r in normal.data.get("results", []) if r["tier"] != "normal" and r["direction"] == "below"]
    for r in abnormal:
        yesterday.append({"type": "stage", "text": f"{r['stage']} made {r['actual']:.0f} pieces on {day} vs a normal "
                          f"{r['baseline_median']:.0f} ({r['pct_vs_baseline']}%, {r['tier']} tier, "
                          f"{r['consecutive_low_days']} low working days in a row).", "evidence_id": r["evidence_id"]})
    if not abnormal and normal.ok:
        outputs = ", ".join(f"{r['stage']} {r['actual']:.0f}" for r in normal.data["results"])
        yesterday.append({"type": "stage", "text": f"All {len(STAGES)} stages were within their normal range on "
                          f"{day} ({outputs})."})
    completed = db.execute("SELECT order_id FROM orders WHERE completed_date = ?", (day,)).fetchall()
    if completed:
        noun = "order" if len(completed) == 1 else "orders"
        yesterday.append({"type": "completed", "text": f"{len(completed)} {noun} completed on {day}: "
                          f"{', '.join(r[0] for r in completed)}."})
    since = (db.execute("SELECT MAX(created_at) FROM briefings WHERE date < ?", (today.isoformat(),)).fetchone()[0]
             or "0000")
    for n in db.execute("SELECT * FROM notifications WHERE kind = 'watch' AND created_at > ? ORDER BY created_at",
                        (since,)):
        yesterday.append({"type": "watch", "text": f"Watch alert — {n['title']}: {n['body']}"})

    scan = run("scan_exceptions", top_k=5)
    at_risk = [{"type": f["kind"], "text": f"{f['title']}. {f['detail']}.", "score": f["score"],
                "evidence_id": f["evidence_id"]}
               for f in scan.data.get("findings", []) if not (f["kind"] == "stage_drop" and abnormal)]

    decisions: list[dict[str, Any]] = []
    for p in db.execute("SELECT * FROM pending_actions WHERE status = 'pending' ORDER BY created_at"):
        decisions.append({"type": "pending_action", "text": f"Awaiting your confirmation: {p['preview']}",
                          "action_id": p["action_id"]})
    risk = run("assess_order_risk")
    for a in [x for x in risk.data.get("orders", []) if x["level"] == "OVERDUE"][:2]:
        decisions.append({"type": "overdue", "text": f"{a['order_id']} ({a['customer']}, {a['pieces']} pieces) is "
                          f"{days(-a['days_to_due'])} overdue in {a['stage']}: chase, re-plan, or tell the customer?"})
    for a in [x for x in risk.data.get("orders", []) if x["level"] == "AT_RISK" and 0 <= x["days_to_due"] <= 1]:
        decisions.append({"type": "due_now", "text": f"{a['order_id']} is due {a['due_date']} but projected to "
                          f"finish {a['p50_finish']} (P50): warn the customer or outsource?"})
    return {"date": today.isoformat(), "generated_at": now.isoformat(timespec="minutes"), "data_through": last_log,
            "yesterday": yesterday, "at_risk": at_risk, "decisions": decisions,
            "suppressed_findings": scan.data.get("suppressed_count", 0),
            "evidence_ids": sorted(set(evidence), key=lambda e: int(e[1:]))}


def ensure(db: sqlite3.Connection, clock: Clock, rebuild: bool = False) -> dict[str, Any]:
    today = clock.now().date().isoformat()
    row = db.execute("SELECT * FROM briefings WHERE date = ?", (today,)).fetchone()
    if row and not rebuild:
        return _row(row)
    structured = build(db, clock)
    db.execute("INSERT INTO briefings (date, created_at, structured, narrative, narrative_status) "
               "VALUES (?, ?, ?, NULL, 'pending') ON CONFLICT(date) DO UPDATE SET "
               "created_at = excluded.created_at, structured = excluded.structured, narrative = NULL, "
               "narrative_status = 'pending'",
               (today, clock.now().isoformat(timespec="minutes"), dumps(structured)))
    db.commit()
    return _row(db.execute("SELECT * FROM briefings WHERE date = ?", (today,)).fetchone())


def narrate(db: sqlite3.Connection, clock: Clock, llm: LLMClient) -> dict[str, Any]:
    b = ensure(db, clock)
    if b["narrative_status"] in ("ok",):
        return b
    s = b["structured"]
    text_json = json.dumps({k: s[k] for k in ("date", "yesterday", "at_risk", "decisions")}, ensure_ascii=False,
                           indent=1)
    prompt = prompts.load("briefing_narrate").render(date=s["date"], structured=text_json)
    try:
        budget.check(db)
        resp = llm.create(instructions=None, input=[{"role": "user", "content": prompt}], tools=None)
        budget.record(db, resp.model, "briefing", f"briefing-{s['date']}", resp.usage, resp.latency_ms)
        allowed = grounding.Allowed()
        allowed.absorb(s, datetime.fromisoformat(s["generated_at"]).year)
        problems = grounding.violations(resp.text, allowed, date.fromisoformat(s["date"]).year)
        status = "ok" if not problems and resp.text.strip() else "rejected"
        narrative = resp.text.strip() if status == "ok" else None
        detail = "; ".join(problems)[:500] if problems else None
    except LLMError as e:
        status, narrative, detail = "unavailable", None, str(e)[:300]
    db.execute("UPDATE briefings SET narrative = ?, narrative_status = ? WHERE date = ?",
               (narrative, status if not detail else f"{status}: {detail}", s["date"]))
    db.commit()
    return _row(db.execute("SELECT * FROM briefings WHERE date = ?", (s["date"],)).fetchone())


def _row(r: sqlite3.Row) -> dict[str, Any]:
    status = r["narrative_status"]
    return {"date": r["date"], "created_at": r["created_at"], "structured": loads(r["structured"]),
            "narrative": r["narrative"], "narrative_status": status.split(":")[0], "narrative_note": status}
