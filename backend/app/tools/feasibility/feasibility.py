"""estimate_feasibility — "can we take N pieces of X by date D?" (Feasibility; TOOL_SPEC tool 13).

In-house: P50 / P80 finish from the log-linear size model (D13). Outsourcing: per eligible workshop,
finish = start + ⌈queue days + ⌈pieces / capacity⌉ + pickup lead days⌉. Ineligible workshops are listed with the
reason (wrong category, suspended, over the batch cap). The verdict is an estimate with stated assumptions,
never a bare yes.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Literal

from pydantic import BaseModel, Field

from app.config import STAGES
from app.domain import normal, projection
from app.domain.products import resolve_product
from app.tools.base import ErrorCode, ToolContext, ToolResult
from app.tools.registry import tool

DEFINITION = {
    "in_house": "start + ceil(cycle days) from the log-linear size model; P50 and P80",
    "workshop": "start + ceil(current_queue_days + ceil(pieces / capacity_per_day) + pickup_lead_days)",
    "eligible_workshop": "ACTIVE, makes the category, and pieces within max_batch_pieces (if any)",
    "verdict": {"comfortable in-house": "P80 on or before the due date",
                "tight in-house": "P50 on or before the due date, P80 after",
                "only with outsourcing": "in-house P50 after the due date, at least one eligible workshop in time",
                "not feasible": "neither in-house P50 nor any eligible workshop meets the due date",
                "no deadline given": "no due date: options are ranked by earliest finish"},
}


class FeasibilityParams(BaseModel):
    pieces: int = Field(gt=0, description="Number of pieces requested")
    due_date: str | None = Field(None, description="ISO due date (resolve 'the 25th' with resolve_time first). "
                                 "Leave null for 'how soon could we…' / 'which workshop is fastest' / cost questions")
    product: str | None = Field(None, description="Product as said, e.g. hoodies, beanies")
    category: Literal["TOPS", "ACCESSORIES"] | None = Field(None, description="If the product is unknown")
    start_date: str | None = Field(None, description="ISO date work could start; default today")


@tool("estimate_feasibility", "feasibility",
      "Estimate a new batch of N pieces: in-house P50/P80 finish dates, every workshop with eligibility, finish "
      "date, total subcontract cost and defect rate, the fastest eligible workshop, the earliest achievable date "
      "and the assumptions. With a due date it also gives a verdict (comfortable in-house / tight in-house / only "
      "with outsourcing / not feasible). Use it for 'can we take…', 'which workshop gets them back first' and "
      "'what would sending N to <workshop> cost'. Does not accept the order or allocate it.", FeasibilityParams)
def estimate_feasibility(ctx: ToolContext, pieces: int, due_date: str | None = None, product: str | None = None,
                         category: str | None = None, start_date: str | None = None) -> ToolResult:
    today = ctx.clock.today()
    try:
        due = date.fromisoformat(due_date) if due_date else None
        start = date.fromisoformat(start_date) if start_date else today
    except ValueError:
        return ctx.fail(ErrorCode.INVALID_ARGUMENT, "dates must be ISO (YYYY-MM-DD); use resolve_time first")
    matched_product = None
    if product:
        matched_product, cat, cands = resolve_product(ctx.db, product)
        if matched_product is None and not category:
            return ctx.fail(ErrorCode.OUT_OF_COVERAGE, f"'{product}' is not a product this factory has made; "
                            "give a category (TOPS or ACCESSORIES) to estimate anyway",
                            candidates=[{"product": c} for c in cands])
        category = category or cat
    if not category:
        return ctx.fail(ErrorCode.INVALID_ARGUMENT, "give a product or a category (TOPS or ACCESSORIES)")

    proj = projection.fit(ctx.db, today)
    if proj is None:
        return ctx.fail(ErrorCode.PRECONDITION_FAILED, "not enough completed orders to project a finish date")
    p50, p80 = proj.finish(start, pieces, 0.5), proj.finish(start, pieces, 0.8)

    options = []
    for w in ctx.db.execute("SELECT * FROM workshops ORDER BY workshop_id"):
        w = dict(w)
        makes = w["makes"].split("+")
        reason = None
        if category not in makes:
            reason = f"does not make {category}"
        elif w["status"] != "ACTIVE":
            reason = f"{w['status']} — may not take new work"
        elif w["max_batch_pieces"] and pieces > w["max_batch_pieces"]:
            reason = (f"batch cap {w['max_batch_pieces']} pieces; would need "
                      f"{math.ceil(pieces / w['max_batch_pieces'])} separate batches")
        processing = math.ceil(pieces / w["capacity_pieces_per_day"])
        total = w["current_queue_days"] + processing + w["pickup_lead_days"]
        finish = start + timedelta(days=math.ceil(total))
        options.append({"workshop_id": w["workshop_id"], "workshop": w["name"], "eligible": reason is None,
                        "reason_ineligible": reason, "queue_days": w["current_queue_days"],
                        "processing_days": processing, "pickup_lead_days": w["pickup_lead_days"],
                        "total_days": total, "finish_date": finish.isoformat(),
                        "meets_due": finish <= due if due else None,
                        "cost": round(pieces * w["cost_per_piece"], 2), "cost_per_piece": w["cost_per_piece"],
                        "defect_rate": w["defect_rate"], "defect_rate_pct": round(w["defect_rate"] * 100, 1)})
    eligible = sorted([o for o in options if o["eligible"]], key=lambda o: (o["finish_date"], o["defect_rate"]))
    in_time = [o for o in eligible if o["meets_due"]]
    if due is None:
        verdict = "no deadline given"
    elif p80 <= due:
        verdict = "comfortable in-house"
    elif p50 <= due:
        verdict = "tight in-house"
    elif in_time:
        verdict = "only with outsourcing"
    else:
        verdict = "not feasible"
    earliest = min([p50] + [date.fromisoformat(o["finish_date"]) for o in eligible])

    warnings, assumptions = [], [
        f"in-house dates come from the log-linear size model fitted on {proj.n} completed orders "
        f"(sizes {proj.pieces_range[0]}–{proj.pieces_range[1]} pieces)",
        "the model does not scale by current load (that made forecasts worse in the backtest)",
        "workshop dates assume the current queue on the profile card and one batch to one workshop",
        "calendar days; the factory is closed on Sundays, workshops are not",
    ]
    if not (proj.pieces_range[0] <= pieces <= proj.pieces_range[1]):
        warnings.append(f"{pieces} pieces is outside the sizes seen in history; the in-house estimate is less reliable")
    if due and due < today:
        warnings.append(f"the due date {due.isoformat()} is already in the past")
    if due and due.weekday() == 6:
        warnings.append(f"{due.isoformat()} is a Sunday")
    open_pcs = ctx.db.execute("SELECT COALESCE(SUM(pieces), 0) FROM orders WHERE status = 'IN_PROGRESS'").fetchone()[0]
    for s in STAGES:
        series = normal.working_series(ctx.db, s)
        r = normal.judge(series, len(series) - 1) if series else None
        if r and r["tier"] == "interrupt":
            warnings.append(f"{s} is running {abs(r['pct_vs_baseline'])}% below normal "
                            f"(latest day {series[-1][0]}): in-house dates may slip further")
    ev = ctx.evidence.register("workshops", [o["workshop_id"] for o in options], "workshop options for the request",
                               options)
    return ctx.ok({
        "request": {"pieces": pieces, "product": matched_product, "category": category,
                    "due_date": due.isoformat() if due else None,
                    "start_date": start.isoformat()},
        "in_house": {"p50_finish": p50.isoformat(), "p80_finish": p80.isoformat(),
                     "meets_due_p50": p50 <= due if due else None, "meets_due_p80": p80 <= due if due else None,
                     "open_pieces_now": open_pcs},
        "workshops": options, "verdict": verdict, "earliest_finish": earliest.isoformat(),
        "best_workshop_in_time": in_time[0]["workshop"] if in_time else None,
        "fastest_eligible_workshop": eligible[0]["workshop"] if eligible else None,
        "assumptions": assumptions,
    }, [ev], definition=DEFINITION, warnings=warnings)
