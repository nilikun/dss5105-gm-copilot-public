"""get_stage_output — factory-wide output per stage (Retrieval; TOOL_SPEC tool 5)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Literal

from pydantic import BaseModel, Field

from app.config import STAGES
from app.tools.base import ErrorCode, ToolContext, ToolResult
from app.tools.registry import tool

StageArg = Literal["KNITTING", "ASSEMBLY", "WASHING", "PACKING", "ALL"]


def stages_for(stage: str | None) -> list[str] | None:
    if stage is None or stage.upper() in ("ALL", "ANY"):
        return list(STAGES)
    s = stage.upper()
    return [s] if s in STAGES else None


def log_range(ctx: ToolContext) -> tuple[str, str]:
    lo, hi = ctx.db.execute("SELECT MIN(date), MAX(date) FROM production_log").fetchone()
    return lo, hi


class StageOutputParams(BaseModel):
    date_from: str = Field(description="ISO date, inclusive (resolve relative dates with resolve_time)")
    date_to: str = Field(description="ISO date, inclusive")
    stage: StageArg | None = Field(None, description="One stage or ALL (default)")
    granularity: Literal["day", "week"] = "day"


@tool("get_stage_output", "retrieval",
      "Pieces completed per stage per day or per week (Mon–Sun), with totals and working-day counts. Facts only: "
      "use compare_to_normal to judge whether a number is normal. The log is factory-wide, not per order.",
      StageOutputParams)
def get_stage_output(ctx: ToolContext, date_from: str, date_to: str, stage: str | None = None,
                     granularity: str = "day") -> ToolResult:
    stages = stages_for(stage)
    if stages is None:
        return ctx.fail(ErrorCode.INVALID_ARGUMENT, f"stage must be one of {list(STAGES)} or 'all'")
    if granularity not in ("day", "week"):
        return ctx.fail(ErrorCode.INVALID_ARGUMENT, "granularity must be 'day' or 'week'")
    try:
        lo_d, hi_d = date.fromisoformat(date_from), date.fromisoformat(date_to)
    except ValueError:
        return ctx.fail(ErrorCode.INVALID_ARGUMENT, "dates must be ISO (YYYY-MM-DD); use resolve_time first")
    lo, hi = log_range(ctx)
    if hi_d < date.fromisoformat(lo) or lo_d > date.fromisoformat(hi) or lo_d > hi_d:
        return ctx.fail(ErrorCode.INVALID_ARGUMENT, f"the production log covers {lo} to {hi}")
    warnings = []
    if lo_d < date.fromisoformat(lo) or hi_d > date.fromisoformat(hi):
        warnings.append(f"range clipped to the log's coverage {lo} to {hi}")
    marks = ",".join("?" for _ in stages)
    rows = [dict(r) for r in ctx.db.execute(
        f"SELECT date, stage, pieces_completed FROM production_log WHERE date BETWEEN ? AND ? AND stage IN ({marks}) "
        "ORDER BY date, stage", [date_from, date_to, *stages])]
    for r in rows:
        r["is_sunday"] = date.fromisoformat(r["date"]).weekday() == 6
    ev = ctx.evidence.register("production_log", [f"{r['date']}/{r['stage']}" for r in rows],
                               f"production log {date_from}..{date_to}", rows)
    if granularity == "day":
        series = rows
    else:
        weeks: dict[tuple[str, str], dict] = {}
        for r in rows:
            d = date.fromisoformat(r["date"])
            monday = (d - timedelta(days=d.weekday())).isoformat()
            w = weeks.setdefault((monday, r["stage"]), {"week_start": monday, "stage": r["stage"],
                                                        "pieces_completed": 0, "days": 0})
            w["pieces_completed"] += r["pieces_completed"]
            w["days"] += 1
        series = list(weeks.values())
        for w in series:
            w["partial_week"] = w["days"] < 7
    totals = {s: sum(r["pieces_completed"] for r in rows if r["stage"] == s) for s in stages}
    working_days = len({r["date"] for r in rows if not r["is_sunday"]})
    return ctx.ok({"granularity": granularity, "series": series, "totals": totals, "working_days": working_days,
                   "from": max(date_from, lo), "to": min(date_to, hi)}, [ev], warnings=warnings)
