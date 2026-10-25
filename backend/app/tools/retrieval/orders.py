"""Order retrieval tools: get_order, find_orders, summarize_orders (TOOL_SPEC tools 2–4)."""

from __future__ import annotations

import re
import statistics
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.config import FIND_ORDERS_DEFAULT_LIMIT, FIND_ORDERS_MAX_LIMIT, STAGES
from app.domain.calendar import working_days_between
from app.domain.names import match
from app.tools.base import ErrorCode, ToolContext, ToolResult
from app.tools.registry import tool

SORTS = {"due_date": ("due_date", False), "pieces": ("pieces", True), "idle": ("idle_working_days", True),
         "days_late": ("days_late", True), "order_date": ("order_date", False)}
GROUPS = {"customer", "product", "category", "stage", "status", "order_month", "due_week"}
METRICS = {"count", "pieces_sum", "avg_days_late", "median_days_late", "late_rate", "overdue_count"}


# ----------------------------------------------------------------- helpers
def normalize_order_id(raw: str) -> str | None:
    nums = re.findall(r"\d+", raw)
    return f"ORD-{int(nums[0]):03d}" if len(nums) == 1 else None


def _derive(row: dict[str, Any], today: date) -> dict[str, Any]:
    """Facts computed from one order row and the clock — the model never computes these."""
    due = date.fromisoformat(row["due_date"])
    last = date.fromisoformat(row["last_activity_date"])
    is_open = row["status"] == "IN_PROGRESS"
    out = dict(row)
    out["days_to_due"] = (due - today).days
    out["is_overdue"] = is_open and due < today
    out["idle_days"] = (today - last).days if is_open else None
    if is_open:
        out["idle_working_days"] = working_days_between(last, today) if last < today else 0
    else:
        out["idle_working_days"] = None
    out["stages_remaining"] = list(STAGES[STAGES.index(row["current_stage"]):]) if is_open else []
    return out


def _summary(o: dict[str, Any]) -> dict[str, Any]:
    keys = ("order_id", "customer", "product", "pieces", "status", "current_stage", "due_date", "days_to_due",
            "is_overdue", "idle_working_days", "completed_date", "days_late")
    return {k: o[k] for k in keys}


def _canonical(ctx: ToolContext, column: str) -> list[str]:
    return [r[0] for r in ctx.db.execute(f"SELECT DISTINCT {column} FROM orders ORDER BY {column}")]


def _filtered(ctx: ToolContext, customer=None, product=None, category=None, status=None, stage=None,
              due_from=None, due_to=None, ordered_from=None, ordered_to=None, overdue=None,
              min_idle_working_days=None, min_pieces=None, max_pieces=None):
    """Apply filters; returns (orders, matched_as, warnings) or a ToolResult on a naming problem."""
    today = ctx.clock.today()
    where, params, matched, warnings = [], [], {}, []
    for field, value in (("customer", customer), ("product", product)):
        if value is None:
            continue
        hits = match(value, _canonical(ctx, field))
        if not hits:
            return ctx.fail(ErrorCode.NOT_FOUND, f"no {field} matches '{value}'",
                            candidates=[{field: c} for c in _canonical(ctx, field)])
        if len(hits) > 1:
            return ctx.fail(ErrorCode.AMBIGUOUS, f"'{value}' matches several {field}s",
                            candidates=[{field: c} for c in hits])
        matched[field] = hits[0]
        where.append(f"{field} = ?")
        params.append(hits[0])
    for field, value, allowed in (("category", category, {"TOPS", "ACCESSORIES"}),
                                  ("status", status, {"COMPLETE", "IN_PROGRESS"}),
                                  ("current_stage", stage, set(STAGES) | {"COMPLETE"})):
        if value is None:
            continue
        v = value.upper().replace(" ", "_")
        if v == "OPEN":
            v = "IN_PROGRESS"
        if v not in allowed:
            return ctx.fail(ErrorCode.INVALID_ARGUMENT, f"{field} must be one of {sorted(allowed)}")
        where.append(f"{field} = ?")
        params.append(v)
    for field, op, value in (("due_date", ">=", due_from), ("due_date", "<=", due_to),
                             ("order_date", ">=", ordered_from), ("order_date", "<=", ordered_to)):
        if value is not None:
            try:
                date.fromisoformat(value)
            except ValueError:
                return ctx.fail(ErrorCode.INVALID_ARGUMENT, f"{field} bound '{value}' is not an ISO date; "
                                                            "resolve it with resolve_time first")
            where.append(f"{field} {op} ?")
            params.append(value)
    if overdue is not None:
        where.append("(status = 'IN_PROGRESS' AND due_date < ?)" if overdue else
                     "NOT (status = 'IN_PROGRESS' AND due_date < ?)")
        params.append(today.isoformat())
    if min_pieces is not None:
        where.append("pieces >= ?")
        params.append(min_pieces)
    if max_pieces is not None:
        where.append("pieces <= ?")
        params.append(max_pieces)
    sql = "SELECT * FROM orders" + (" WHERE " + " AND ".join(where) if where else "")
    rows = [_derive(dict(r), today) for r in ctx.db.execute(sql, params)]
    if min_idle_working_days is not None:
        rows = [r for r in rows
                if r["idle_working_days"] is not None and r["idle_working_days"] >= min_idle_working_days]
    return rows, matched, warnings


def _urgency_key(o: dict[str, Any]):
    return (not o["is_overdue"], o["status"] != "IN_PROGRESS", o["due_date"])


# ----------------------------------------------------------------- parameter models (become the LLM's schemas)
class GetOrderParams(BaseModel):
    order_id: str = Field(description="Order id such as ORD-058 (\"58\" or \"ord 58\" also work)")


class OrderFilters(BaseModel):
    customer: str | None = Field(None, description="Customer name; partial or informal names are matched")
    product: str | None = Field(None, description="Product, e.g. Hoodie, Scarf; plural or partial is fine")
    category: Literal["TOPS", "ACCESSORIES"] | None = None
    status: Literal["IN_PROGRESS", "COMPLETE", "OPEN"] | None = Field(None, description="OPEN = IN_PROGRESS")
    stage: Literal["KNITTING", "ASSEMBLY", "WASHING", "PACKING", "COMPLETE"] | None = None
    due_from: str | None = Field(None, description="ISO date, inclusive; resolve relative dates with resolve_time")
    due_to: str | None = Field(None, description="ISO date, inclusive")
    ordered_from: str | None = Field(None, description="ISO date, inclusive")
    ordered_to: str | None = Field(None, description="ISO date, inclusive")
    overdue: bool | None = Field(None, description="True = open orders past their due date")
    min_idle_working_days: int | None = Field(None, description="Open orders idle for at least N working days")
    min_pieces: int | None = None
    max_pieces: int | None = None


class FindOrdersParams(OrderFilters):
    sort_by: Literal["due_date", "pieces", "idle", "days_late", "order_date"] = "due_date"
    limit: int = Field(FIND_ORDERS_DEFAULT_LIMIT, ge=1, le=FIND_ORDERS_MAX_LIMIT)
    expect_single: bool = Field(False, description="True when the manager means ONE order (\"the TrendCart "
                                                   "order\"); several matches then return AMBIGUOUS + candidates")


class SummarizeOrdersParams(OrderFilters):
    group_by: Literal["customer", "product", "category", "stage", "status", "order_month", "due_week"] | None = None
    metrics: list[Literal["count", "pieces_sum", "avg_days_late", "median_days_late", "late_rate",
                          "overdue_count"]] = Field(default_factory=lambda: ["count"])


# ----------------------------------------------------------------- tools
@tool("get_order", "retrieval",
      "The complete current fact sheet for ONE order: customer, product, pieces, stage, dates, days to due, "
      "overdue flag, idle working days, notes. Does not judge risk (use assess_order_risk).", GetOrderParams)
def get_order(ctx: ToolContext, order_id: str) -> ToolResult:
    """The complete, current fact sheet for one order. No risk judgement (that is assess_order_risk)."""
    oid = normalize_order_id(order_id)
    if oid is None:
        return ctx.fail(ErrorCode.INVALID_ARGUMENT, f"'{order_id}' is not an order id like ORD-058")
    row = ctx.db.execute("SELECT * FROM orders WHERE order_id = ?", (oid,)).fetchone()
    if row is None:
        n = int(oid[4:])
        near = ctx.db.execute("SELECT order_id FROM orders ORDER BY ABS(CAST(SUBSTR(order_id, 5) AS INTEGER) - ?) "
                              "LIMIT 3", (n,)).fetchall()
        return ctx.fail(ErrorCode.NOT_FOUND, f"{oid} does not exist", candidates=[{"order_id": r[0]} for r in near])
    o = _derive(dict(row), ctx.clock.today())
    o["notes"] = [dict(r) for r in ctx.db.execute(
        "SELECT note_id, text, created_at FROM notes WHERE order_id = ? AND deleted_at IS NULL", (oid,))]
    ev = ctx.evidence.register("orders", [oid], f"order row {oid}", [dict(row)])
    warnings = []
    if o["status"] == "COMPLETE":
        warnings.append(f"{oid} is COMPLETE (finished {o['completed_date']}); it is not an open order")
    return ctx.ok(o, [ev], warnings=warnings)


@tool("find_orders", "retrieval",
      "List orders matching filters (customer, product, status, stage, due range, overdue, idle days, size). "
      "Use expect_single=true when the manager refers to one order. Lists only; for counts or rates use "
      "summarize_orders. Results may be truncated (see total_matches).", FindOrdersParams)
def find_orders(ctx: ToolContext, customer: str | None = None, product: str | None = None,
                category: str | None = None, status: str | None = None, stage: str | None = None,
                due_from: str | None = None, due_to: str | None = None, ordered_from: str | None = None,
                ordered_to: str | None = None, overdue: bool | None = None,
                min_idle_working_days: int | None = None, min_pieces: int | None = None,
                max_pieces: int | None = None, sort_by: str = "due_date",
                limit: int = FIND_ORDERS_DEFAULT_LIMIT, expect_single: bool = False) -> ToolResult:
    """Orders matching a description. Lists only — counting and aggregating is summarize_orders."""
    if sort_by not in SORTS:
        return ctx.fail(ErrorCode.INVALID_ARGUMENT, f"sort_by must be one of {sorted(SORTS)}")
    res = _filtered(ctx, customer, product, category, status, stage, due_from, due_to, ordered_from, ordered_to,
                    overdue, min_idle_working_days, min_pieces, max_pieces)
    if isinstance(res, ToolResult):
        return res
    rows, matched, warnings = res
    key, desc = SORTS[sort_by]
    present = sorted((o for o in rows if o[key] is not None), key=lambda o: o[key], reverse=desc)
    rows = present + [o for o in rows if o[key] is None]
    if expect_single and len(rows) > 1:
        open_rows = [o for o in rows if o["status"] == "IN_PROGRESS"]
        if status is None and len(open_rows) == 1:
            rows = open_rows  # "the X order" with exactly one live match means that one
        else:
            # a singular reference usually means a live order: offer open ones first, completed only if none open
            cands = sorted(open_rows or rows, key=_urgency_key)
            return ctx.fail(ErrorCode.AMBIGUOUS,
                            f"{len(rows)} orders match, {len(open_rows)} of them open; ask which one "
                            f"(candidates: the {'open' if open_rows else 'matching'} ones, most urgent first)",
                            candidates=[_summary(o) for o in cands[:FIND_ORDERS_MAX_LIMIT]])
    limit = max(1, min(limit, FIND_ORDERS_MAX_LIMIT))
    shown = rows[:limit]
    if not rows:
        warnings.append("no orders match these filters")
    ev = ctx.evidence.register("orders", [o["order_id"] for o in rows], "orders matching the filters",
                               [{k: o[k] for k in ("order_id", "customer", "product", "status", "due_date")}
                                for o in rows])
    return ctx.ok({"total_matches": len(rows), "orders": [_summary(o) for o in shown],
                   "matched_as": matched, "truncated": len(rows) > limit}, [ev], warnings=warnings)


def _group_key(o: dict[str, Any], group_by: str | None) -> str:
    if group_by is None:
        return "all"
    if group_by == "stage":
        return o["current_stage"]
    if group_by == "order_month":
        return o["order_date"][:7]
    if group_by == "due_week":
        iso = date.fromisoformat(o["due_date"]).isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    return o[group_by]


def _metrics(rows: list[dict[str, Any]], metrics: list[str]) -> dict[str, Any]:
    done = [o for o in rows if o["status"] == "COMPLETE"]
    late = [o for o in done if o["days_late"] > 0]
    out: dict[str, Any] = {}
    for m in metrics:
        if m == "count":
            out[m] = len(rows)
        elif m == "pieces_sum":
            out[m] = sum(o["pieces"] for o in rows)
        elif m == "avg_days_late":
            out[m] = round(statistics.fmean(o["days_late"] for o in done), 1) if done else None
        elif m == "median_days_late":
            out[m] = statistics.median(o["days_late"] for o in done) if done else None
        elif m == "late_rate":
            out[m] = {"late": len(late), "completed": len(done),
                      "pct": round(100 * len(late) / len(done)) if done else None}
        elif m == "overdue_count":
            out[m] = sum(o["is_overdue"] for o in rows)
    return out


@tool("summarize_orders", "retrieval",
      "Exact counts, pieces, lateness (avg/median days late, late rate on completed orders) and overdue counts "
      "over filtered orders, optionally grouped by customer, product, category, stage, status, month or due week.",
      SummarizeOrdersParams)
def summarize_orders(ctx: ToolContext, group_by: str | None = None, metrics: list[str] | None = None,
                     customer: str | None = None, product: str | None = None, category: str | None = None,
                     status: str | None = None, stage: str | None = None, due_from: str | None = None,
                     due_to: str | None = None, ordered_from: str | None = None, ordered_to: str | None = None,
                     overdue: bool | None = None, min_idle_working_days: int | None = None,
                     min_pieces: int | None = None, max_pieces: int | None = None) -> ToolResult:
    """Exact aggregates over orders (counts, pieces, lateness), optionally grouped."""
    metrics = metrics or ["count"]
    bad = [m for m in metrics if m not in METRICS]
    if bad or (group_by is not None and group_by not in GROUPS):
        return ctx.fail(ErrorCode.INVALID_ARGUMENT, f"group_by must be one of {sorted(GROUPS)}; "
                                                    f"metrics must be from {sorted(METRICS)}")
    res = _filtered(ctx, customer, product, category, status, stage, due_from, due_to, ordered_from, ordered_to,
                    overdue, min_idle_working_days, min_pieces, max_pieces)
    if isinstance(res, ToolResult):
        return res
    rows, matched, warnings = res
    groups: dict[str, list[dict[str, Any]]] = {}
    for o in rows:
        groups.setdefault(_group_key(o, group_by), []).append(o)
    table, evidence = [], []
    for g, members in sorted(groups.items()):
        ev = ctx.evidence.register("orders", [o["order_id"] for o in members], f"orders in group '{g}'",
                                   [{k: o[k] for k in ("order_id", "status", "pieces", "days_late", "due_date")}
                                    for o in members])
        evidence.append(ev)
        table.append({"group": g, **_metrics(members, metrics), "evidence_id": ev.id})
    if {"avg_days_late", "median_days_late", "late_rate"} & set(metrics):
        open_n = sum(o["status"] == "IN_PROGRESS" for o in rows)
        if open_n:
            warnings.append(f"lateness metrics use completed orders only; {open_n} open orders excluded")
    return ctx.ok({"group_by": group_by, "groups": table, "totals": _metrics(rows, metrics),
                   "matched_as": matched}, evidence, warnings=warnings)
