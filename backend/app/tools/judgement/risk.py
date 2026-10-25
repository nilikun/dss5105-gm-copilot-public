"""assess_order_risk — one consistent definition of 'at risk' (Judgement; TOOL_SPEC tool 10, D13–D14)."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.domain import projection, risk
from app.domain.names import match
from app.tools.base import ErrorCode, ToolContext, ToolResult
from app.tools.registry import tool
from app.tools.retrieval.orders import normalize_order_id


class AssessRiskParams(BaseModel):
    order_id: str | None = Field(None, description="Assess one order; omit to assess all open orders")
    customer: str | None = Field(None, description="With no order_id: only this customer's open orders")
    level: Literal["OVERDUE", "AT_RISK", "WATCH", "OK"] | None = Field(None, description="Only orders at this level")
    limit: int = Field(40, ge=1, le=60)


@tool("assess_order_risk", "judgement",
      "Risk level of an open order using the documented definition: OVERDUE (past due), AT_RISK (P50 projected "
      "finish after due date — likely late), WATCH (only P80 after due — could slip), OK; plus a QUIET flag "
      "(no activity for 3+ working days). Returns projected P50/P80 finish dates and the reasons. Without "
      "order_id it assesses all open orders and returns counts per level.", AssessRiskParams)
def assess_order_risk(ctx: ToolContext, order_id: str | None = None, customer: str | None = None,
                      level: str | None = None, limit: int = 40) -> ToolResult:
    today = ctx.clock.today()
    proj = projection.fit(ctx.db, today)
    definition = {**risk.DEFINITION, "projection_model": projection.DEFINITION,
                  "fitted_on_completed_orders": proj.n if proj else 0}
    if order_id:
        oid = normalize_order_id(order_id)
        row = ctx.db.execute("SELECT * FROM orders WHERE order_id = ?", (oid,)).fetchone() if oid else None
        if row is None:
            return ctx.fail(ErrorCode.NOT_FOUND, f"order '{order_id}' does not exist")
        c = risk.classify(dict(row), today, proj)
        ev = ctx.evidence.register("orders", [oid], f"order row {oid} (risk assessment)", [dict(row)])
        warnings = [f"{oid} is already COMPLETE"] if c["level"] == "COMPLETE" else []
        return ctx.ok({"assessment": c}, [ev], definition=definition, warnings=warnings)

    sql, params = "SELECT * FROM orders WHERE status = 'IN_PROGRESS'", []
    if customer:
        names = [r[0] for r in ctx.db.execute("SELECT DISTINCT customer FROM orders")]
        hits = match(customer, names)
        if len(hits) != 1:
            return ctx.fail(ErrorCode.AMBIGUOUS if hits else ErrorCode.NOT_FOUND,
                            f"customer '{customer}' matched {len(hits)} customers",
                            candidates=[{"customer": h} for h in (hits or names)])
        sql += " AND customer = ?"
        params.append(hits[0])
    rows = [dict(r) for r in ctx.db.execute(sql, params)]
    assessed = [risk.classify(r, today, proj) for r in rows]
    counts = {lv: sum(a["level"] == lv for a in assessed) for lv in ("OVERDUE", "AT_RISK", "WATCH", "OK")}
    counts["QUIET"] = sum(a["quiet"] for a in assessed)
    if level:
        assessed = [a for a in assessed if a["level"] == level]
    assessed.sort(key=lambda a: (risk.LEVEL_ORDER[a["level"]], a["due_date"]))
    ev = ctx.evidence.register("orders", [a["order_id"] for a in assessed], "open orders assessed for risk", rows)
    return ctx.ok({"as_of": date.isoformat(today), "total_open_orders": len(rows), "counts": counts,
                   "orders": assessed[:limit],
                   "truncated": len(assessed) > limit}, [ev], definition=definition)
