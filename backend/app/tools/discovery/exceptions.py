"""scan_exceptions — find what nobody asked about, ranked (Discovery; TOOL_SPEC tool 12).

Detectors: stage output drop, overdue orders, likely-late orders due soon, quiet orders, customers in trouble,
work piling up in front of a stage. Each finding gets severity, urgency and breadth in [0, 1]:
    score = severity^0.5 · urgency^0.3 · max(breadth, 0.05)^0.2
so a severe problem cannot be buried by small breadth, and five items make the page while the rest are counted.
"""

from __future__ import annotations

import statistics
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.config import QUIET_WORKING_DAYS, STAGES, TOP_K_FINDINGS
from app.domain import normal, projection, risk
from app.tools.base import EvidenceRef, ToolContext, ToolResult
from app.tools.registry import tool

DEFINITION = {
    "score": "severity^0.5 * urgency^0.3 * max(breadth, 0.05)^0.2, each in [0, 1]",
    "stage_drop": "latest working day below the briefing tier (robust z); severity = min(1, |z| / 6)",
    "overdue": "open orders past due; severity = min(1, worst days overdue / 14); breadth = their share of open pieces",
    "likely_late_soon": "AT_RISK orders due within 7 days",
    "quiet": f"open orders with no activity for >= {QUIET_WORKING_DAYS} working days",
    "customer": ">= 2 open orders OVERDUE or AT_RISK and a completed-order late rate at or above the overall rate",
    "wip_pileup": "open pieces waiting at a stage / its recent daily output, >= 1.5x the median across stages; "
                  "a ratio, so it is unaffected by the log/orders scale gap",
    "dedupe": "a stage drop absorbs the pile-up at the same stage",
}

Kind = Literal["stage_drop", "overdue", "likely_late_soon", "quiet", "customer", "wip_pileup"]


class ScanParams(BaseModel):
    top_k: int = Field(TOP_K_FINDINGS, ge=1, le=10)
    kinds: list[Kind] | None = Field(None, description="Only these detectors (default: all)")


def _score(sev: float, urg: float, breadth: float) -> float:
    return round(max(sev, 0) ** 0.5 * max(urg, 0) ** 0.3 * max(breadth, 0.05) ** 0.2, 3)


@tool("scan_exceptions", "discovery",
      "Scan the whole factory for exceptions nobody asked about and rank them: stage output drops, overdue "
      "orders, likely-late orders due soon, quiet orders, customers in trouble, work piling up at a stage. "
      "Returns the top findings with scores, entities and evidence, plus how many were suppressed. Use for "
      "'anything I should know?' and for the briefing.", ScanParams)
def scan_exceptions(ctx: ToolContext, top_k: int = TOP_K_FINDINGS, kinds: list[str] | None = None) -> ToolResult:
    today = ctx.clock.today()
    proj = projection.fit(ctx.db, today)
    open_rows = [dict(r) for r in ctx.db.execute("SELECT * FROM orders WHERE status = 'IN_PROGRESS'")]
    assessed = {r["order_id"]: risk.classify(r, today, proj) for r in open_rows}
    open_pieces = sum(r["pieces"] for r in open_rows) or 1
    findings: list[dict[str, Any]] = []
    refs: dict[str, EvidenceRef] = {}

    def add(kind, title, detail, sev, urg, breadth, entities, rows, source="orders"):
        ev = ctx.evidence.register(source, [str(e) for e in entities], f"{kind}: {title}", rows)
        refs[ev.id] = ev
        findings.append({"kind": kind, "title": title, "detail": detail, "severity": round(sev, 2),
                         "urgency": round(urg, 2), "breadth": round(breadth, 2), "score": _score(sev, urg, breadth),
                         "entities": entities, "evidence_id": ev.id})

    # stage drops on the latest working day + WIP pile-up ratios
    wip = {s: sum(r["pieces"] for r in open_rows if r["current_stage"] == s) for s in STAGES}
    drops, backlog = {}, {}
    for s in STAGES:
        series = normal.working_series(ctx.db, s)
        if not series:
            continue
        r = normal.judge(series, len(series) - 1)
        recent = statistics.median(v for _, v in series[-5:]) or 1
        backlog[s] = wip[s] / recent
        if r and r["tier"] != "normal" and r["direction"] == "below":
            drops[s] = (r, series[-1][0])
    med_backlog = statistics.median(backlog.values()) if backlog else 0
    for s, (r, d) in drops.items():
        sev, urg = min(1.0, abs(r["z"]) / 6), (1.0 if r["tier"] == "interrupt" else 0.6)
        detail = (f"{s} made {r['actual']:.0f} pieces on {d} vs a normal {r['baseline_median']:.0f} "
                  f"(z = {r['z']:.2f}, {r['consecutive_low_days']} low working days in a row); "
                  f"{wip[s]} open pieces are at this stage")
        add("stage_drop", f"{s} output {abs(r['pct_vs_baseline']):.1f}% below normal ({r['tier']} tier)", detail,
            sev, urg, wip[s] / open_pieces, [s], [{"stage": s, "date": d, **{k: r[k] for k in
                                                   ("actual", "baseline_median", "z", "tier")}}], "production_log")
    for s, b in backlog.items():
        ratio = b / med_backlog if med_backlog else 0
        if ratio >= 1.5 and s not in drops:
            add("wip_pileup", f"Work piling up at {s}", f"{wip[s]} open pieces at {s}, {ratio:.1f}x the median "
                f"stage backlog", min(1.0, (ratio - 1) / 2), 0.6, wip[s] / open_pieces, [s],
                [{"stage": s, "open_pieces": wip[s], "backlog_ratio": round(ratio, 2)}])

    overdue = [a for a in assessed.values() if a["level"] == "OVERDUE"]
    if overdue:
        overdue.sort(key=lambda a: a["days_to_due"])
        worst = overdue[0]
        pcs = sum(a["pieces"] for a in overdue)
        add("overdue", f"{len(overdue)} open orders are past due",
            f"{pcs:,} pieces across all of them; the most overdue is {worst['order_id']} ({worst['customer']}), "
            f"{-worst['days_to_due']} days late and still in {worst['stage']}",
            min(1.0, -worst["days_to_due"] / 14), 1.0, pcs / open_pieces,
            [a["order_id"] for a in overdue], overdue)

    soon = [a for a in assessed.values() if a["level"] == "AT_RISK" and 0 <= a["days_to_due"] <= 7]
    if soon:
        soon.sort(key=lambda a: a["days_to_due"])
        pcs = sum(a["pieces"] for a in soon)
        add("likely_late_soon", f"{len(soon)} orders due within 7 days are likely late",
            f"next: {soon[0]['order_id']} due {soon[0]['due_date']}, P50 finish {soon[0]['p50_finish']}",
            0.6, 1 - soon[0]["days_to_due"] / 8, pcs / open_pieces, [a["order_id"] for a in soon], soon)

    quiet = [a for a in assessed.values() if a["quiet"]]
    if quiet:
        quiet.sort(key=lambda a: -a["idle_working_days"])
        pcs = sum(a["pieces"] for a in quiet)
        add("quiet", f"{len(quiet)} open orders have gone quiet",
            "; ".join(f"{a['order_id']} idle {a['idle_working_days']} working days" for a in quiet),
            min(1.0, quiet[0]["idle_working_days"] / 10), 0.7, pcs / open_pieces, [a["order_id"] for a in quiet], quiet)

    done = ctx.db.execute("SELECT customer, COUNT(*) n, SUM(days_late > 0) late FROM orders "
                          "WHERE status = 'COMPLETE' GROUP BY customer").fetchall()
    total_done = sum(r["n"] for r in done) or 1
    overall = sum(r["late"] for r in done) / total_done
    history = {r["customer"]: (r["late"], r["n"]) for r in done}
    for cust in sorted({a["customer"] for a in assessed.values()}):
        trouble = [a for a in assessed.values() if a["customer"] == cust and a["level"] in ("OVERDUE", "AT_RISK")]
        late, n = history.get(cust, (0, 0))
        rate = late / n if n else 0
        if len(trouble) >= 2 and rate >= overall:
            pcs = sum(a["pieces"] for a in trouble)
            add("customer", f"{cust}: {len(trouble)} open orders overdue or likely late",
                f"late on {late} of {n} completed orders ({100 * rate:.0f}% vs {100 * overall:.0f}% overall); "
                f"troubled orders: {', '.join(a['order_id'] for a in trouble)}", rate, 0.8, pcs / open_pieces,
                [a["order_id"] for a in trouble], trouble)

    if kinds:
        findings = [f for f in findings if f["kind"] in kinds]
    findings.sort(key=lambda f: -f["score"])
    top = findings[:top_k]
    return ctx.ok({"as_of": date.isoformat(today), "findings": top, "suppressed_count": len(findings) - len(top),
                   "suppressed": [{"kind": f["kind"], "title": f["title"], "score": f["score"]}
                                  for f in findings[top_k:]]},
                  [refs[f["evidence_id"]] for f in top], definition=DEFINITION)
