"""get_workshops — outside workshops' profile cards (Retrieval; TOOL_SPEC tool 6)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.domain.names import match
from app.tools.base import ErrorCode, ToolContext, ToolResult
from app.tools.registry import tool


class GetWorkshopsParams(BaseModel):
    makes: Literal["TOPS", "ACCESSORIES"] | None = Field(None, description="Only workshops equipped for this category")
    name_or_id: str | None = Field(None, description="A workshop name or id, e.g. QuickStitch or W1")
    include_suspended: bool = Field(False, description="Also list workshops that may not take new work")
    max_queue_days: float | None = Field(None, description="Only workshops whose current queue is at most this")


@tool("get_workshops", "retrieval",
      "Profile cards of the outside workshops: what they make, capacity per day, pickup lead days, current queue "
      "days, defect rate, cost per piece, status (ACTIVE / SUSPENDED) and batch cap. Suspended workshops are "
      "excluded unless asked for. Does not allocate or estimate delivery dates (use estimate_feasibility).",
      GetWorkshopsParams)
def get_workshops(ctx: ToolContext, makes: str | None = None, name_or_id: str | None = None,
                  include_suspended: bool = False, max_queue_days: float | None = None) -> ToolResult:
    rows = [dict(r) for r in ctx.db.execute("SELECT * FROM workshops ORDER BY workshop_id")]
    if name_or_id:
        key = name_or_id.strip().upper()
        by_id = [r for r in rows if r["workshop_id"] == key]
        hits = by_id or [r for r in rows if r["name"] in match(name_or_id, [w["name"] for w in rows])]
        if not hits:
            return ctx.fail(ErrorCode.NOT_FOUND, f"no workshop matches '{name_or_id}'",
                            candidates=[{"workshop_id": r["workshop_id"], "name": r["name"]} for r in rows])
        rows = hits
        include_suspended = True  # a workshop asked for by name is shown whatever its status
    if makes:
        rows = [r for r in rows if makes in r["makes"].split("+")]
    if not include_suspended:
        rows = [r for r in rows if r["status"] == "ACTIVE"]
    if max_queue_days is not None:
        rows = [r for r in rows if r["current_queue_days"] <= max_queue_days]
    for r in rows:
        r["makes_list"] = r["makes"].split("+")
        r["available_for_new_work"] = r["status"] == "ACTIVE"
        r["defect_rate_pct"] = round(r["defect_rate"] * 100, 1)  # display-ready, so the model never converts
    ev = ctx.evidence.register("workshops", [r["workshop_id"] for r in rows], "workshop profile cards", rows)
    warnings = [f"{r['name']} ({r['workshop_id']}) is {r['status']} and may not take new work"
                for r in rows if r["status"] != "ACTIVE"]
    return ctx.ok({"count": len(rows), "workshops": rows}, [ev], warnings=warnings)
