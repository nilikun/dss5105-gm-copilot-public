"""compare_to_normal — is a stage's output normal? (Judgement; TOOL_SPEC tool 9)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from app.config import NORMAL_WINDOW_WORKING_DAYS
from app.domain.normal import DEFINITION, judge, working_series
from app.tools.base import ErrorCode, ToolContext, ToolResult
from app.tools.registry import tool
from app.tools.retrieval.production import StageArg, log_range, stages_for


class CompareToNormalParams(BaseModel):
    stage: StageArg | None = Field(None, description="One stage or ALL (default)")
    on_date: str | None = Field(None, description="ISO date to judge; default = the latest day in the log")
    value: float | None = Field(None, description="ONLY when the manager quotes a hypothetical number ('is 800 "
                                                  "normal?'). Leave it out to judge the recorded output. Cannot be "
                                                  "combined with on_date.")


@tool("compare_to_normal", "judgement",
      "Judge whether a stage's daily output is normal using the documented robust-z rule (baseline = median of "
      "the previous 20 working days). Returns actual, baseline, z, % vs baseline, tier (normal / briefing / "
      "interrupt), consecutive low days, and the rule itself. Sundays are closed, never abnormal.",
      CompareToNormalParams)
def compare_to_normal(ctx: ToolContext, stage: str | None = None, on_date: str | None = None,
                      value: float | None = None) -> ToolResult:
    stages = stages_for(stage)
    if stages is None:
        return ctx.fail(ErrorCode.INVALID_ARGUMENT, "stage must be KNITTING, ASSEMBLY, WASHING, PACKING or ALL")
    if value is not None and on_date is not None:
        return ctx.fail(ErrorCode.INVALID_ARGUMENT, "give on_date to judge the recorded output of that day, OR value "
                        "to judge a number the manager quoted — not both")
    lo, hi = log_range(ctx)
    if on_date is not None:
        try:
            day = date.fromisoformat(on_date)
        except ValueError:
            return ctx.fail(ErrorCode.INVALID_ARGUMENT, "on_date must be ISO (YYYY-MM-DD); use resolve_time first")
        if day.weekday() == 6:
            return ctx.ok({"date": on_date, "closed": True,
                           "message": "Sunday: the factory is closed, so zero output is expected"},
                          definition=DEFINITION)
        if not (lo <= on_date <= hi):
            return ctx.fail(ErrorCode.INVALID_ARGUMENT, f"the production log covers {lo} to {hi}")
    results, evidence, warnings = [], [], []
    for s in stages:
        series = working_series(ctx.db, s)
        quoted = value is not None
        if quoted:  # a hypothetical number, judged against the latest baseline
            idx, series_ext, label = len(series), series + [("quoted", value)], "quoted value vs the latest baseline"
        else:
            target = on_date or hi
            idx, series_ext, label = [d for d, _ in series].index(target), series, f"output on {target}"
        r = judge(series_ext, idx, quoted=quoted)
        if r is None:
            warnings.append(f"{s}: fewer than 5 prior working days; cannot judge")
            continue
        win_rows = [{"date": d, "stage": s, "pieces_completed": v}
                    for d, v in series[max(0, idx - NORMAL_WINDOW_WORKING_DAYS):idx]]
        ev = ctx.evidence.register("production_log", [f"{w['date']}/{s}" for w in win_rows],
                                   f"{s} baseline window {r['window'][0]}..{r['window'][1]}", win_rows)
        evidence.append(ev)
        results.append({"stage": s, "label": label, "actual": r["actual"], "baseline_median": r["baseline_median"],
                        "robust_sigma": round(r["robust_sigma"], 1), "z": round(r["z"], 2),
                        "pct_vs_baseline": r["pct_vs_baseline"], "tier": r["tier"], "direction": r["direction"],
                        "consecutive_low_days": r["consecutive_low_days"], "window": r["window"],
                        "window_days": r["window_days"], "evidence_id": ev.id})
        if r["window_days"] < NORMAL_WINDOW_WORKING_DAYS:
            warnings.append(f"{s}: baseline uses only {r['window_days']} working days")
    return ctx.ok({"results": results}, evidence, definition=DEFINITION, warnings=warnings)
