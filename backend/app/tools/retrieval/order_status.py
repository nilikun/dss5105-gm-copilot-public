"""Validated order-status facts. Arithmetic stays in tools, presentation in the agent."""

from __future__ import annotations

import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.config import STAGES
from app.domain.names import match
from app.tools.base import ErrorCode, ToolContext, ToolResult
from app.tools.registry import tool
from app.tools.retrieval.orders import normalize_order_id


class StatusFacts(BaseModel):
    order_id: str = Field(pattern=r"^ORD-\d{3}$")
    status: Literal["IN_PROGRESS", "COMPLETE"]
    stage: Literal["KNITTING", "ASSEMBLY", "WASHING", "PACKING", "COMPLETE"] | None
    due_date: date | None
    completed_date: date | None
    as_of: date
    timing: Literal["overdue", "remaining", "due_today", "late", "early", "on_time"] | None
    days: int | None = Field(ge=0)
    unavailable: list[str]


def status_facts(row: dict, today: date) -> StatusFacts:
    """Validate source fields before computing calendar-day timing; never use stale days_late."""
    unavailable = []

    def day(field):
        raw = row.get(field)
        try:
            if not isinstance(raw, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
                raise ValueError
            value = date.fromisoformat(raw)
            if field == "completed_date" and value > today:
                raise ValueError
            return value
        except ValueError:
            unavailable.append(field)
            return None

    due = day("due_date")
    complete = row["status"] == "COMPLETE"
    completed = day("completed_date") if complete else None
    stage = row.get("current_stage")
    if stage not in (("COMPLETE",) if complete else STAGES):
        unavailable.append("current_stage")
        stage = "COMPLETE" if complete else None
    anchor = completed if complete else today
    timing, days = None, None
    if due is not None and anchor is not None:
        delta = (anchor - due).days
        days = abs(delta)
        timing = ("late" if delta > 0 else "early" if delta < 0 else "on_time") if complete else (
            "overdue" if delta > 0 else "remaining" if delta < 0 else "due_today")
    return StatusFacts(order_id=row["order_id"], status=row["status"], stage=stage, due_date=due,
                       completed_date=completed, as_of=today, timing=timing, days=days, unavailable=unavailable)


class OrderStatusParams(BaseModel):
    order_id: str | None = Field(None, description="Explicit order ID, or one uniquely resolved in the conversation")
    customer: str | None = Field(None, description="Customer name when the manager described the order")
    product: str | None = Field(None, description="Product name when given; do not invent a filter")
    status: Literal["IN_PROGRESS", "COMPLETE"] | None = Field(None, description="Only when requested; otherwise null")


@tool("get_order_status", "retrieval",
      "Use for an order's status, stage, deadline or lateness. Resolves an ID or customer/product description, "
      "returning a complete validated status for deterministic display, or clarification candidates. "
      "Does not guess between multiple open orders. Handles missing dates. For notes, activity, risk, actions "
      "or compound questions use the other purpose-built tools and get_order as needed.", OrderStatusParams)
def get_order_status(ctx: ToolContext, order_id: str | None = None, customer: str | None = None,
                     product: str | None = None, status: str | None = None) -> ToolResult:
    if not any((order_id, customer, product)):
        return ctx.fail(ErrorCode.INVALID_ARGUMENT, "An order ID, customer or product is needed; ask the manager.")
    where, params = [], []
    if order_id:
        oid = normalize_order_id(order_id)
        if oid is None:
            return ctx.fail(ErrorCode.INVALID_ARGUMENT, "The order ID is invalid; ask the manager for the ID.")
        where.append("order_id = ?")
        params.append(oid)
    for field, value in (("customer", customer), ("product", product)):
        if value:
            known = [r[0] for r in ctx.db.execute(f"SELECT DISTINCT {field} FROM orders ORDER BY {field}")]
            hits = match(value, known)
            if len(hits) != 1:
                return ctx.fail(ErrorCode.AMBIGUOUS if hits else ErrorCode.NOT_FOUND,
                                f"The {field} description does not identify one known {field}.",
                                candidates=[{field: name} for name in hits])
            where.append(f"{field} = ?")
            params.append(hits[0])
    if status:
        where.append("status = ?")
        params.append(status)
    rows = [dict(r) for r in ctx.db.execute("SELECT * FROM orders WHERE " + " AND ".join(where), params)]
    # Match find_orders' existing convention: unspecified status prefers live matches.
    if not order_id and status is None:
        rows = [r for r in rows if r["status"] == "IN_PROGRESS"] or rows
    if not rows:
        return ctx.fail(ErrorCode.NOT_FOUND, "No order matches the supplied identifier and filters.")
    if len(rows) > 1:
        return ctx.fail(ErrorCode.AMBIGUOUS, "Several orders match. Ask the manager which order.",
                        candidates=[{k: r[k] for k in ("order_id", "customer", "product")}
                                    for r in sorted(rows, key=lambda r: r["order_id"])])
    row = rows[0]
    facts = status_facts(row, ctx.clock.today())
    ev = ctx.evidence.register("orders", [row["order_id"]], "order status and source dates", [row])
    return ctx.ok({"status_facts": facts.model_dump(mode="json")}, [ev],
                  warnings=[f"{field} is unavailable or invalid" for field in facts.unavailable])
