"""compare_to_normal — is a stage's output normal? (Judgement; TOOL_SPEC tool 9)."""

from __future__ import annotations

import statistics
from datetime import date, timedelta

from pydantic import BaseModel, Field

from app.config import NORMAL_WINDOW_WORKING_DAYS
from app.domain.normal import DEFINITION, baseline_before, judge, pct_change, working_series
from app.tools.base import ErrorCode, ToolContext, ToolResult
from app.tools.registry import tool
from app.tools.retrieval.production import StageArg, log_range, stages_for


class CompareToNormalParams(BaseModel):
    stage: StageArg | None = Field(None, description="One stage or ALL (default)")
    on_date: str | None = Field(None, description="ISO date to judge; default = the latest day in the log. With "
                                                  "through_date, the first day of the period")
    through_date: str | None = Field(None, description="ISO last day of a period: compares the mean per working day "
                                                       "from on_date to through_date with the baseline before on_date")
    value: float | None = Field(None, description="ONLY when the manager quotes a hypothetical number ('is 800 "
                                                  "normal?'). Leave it out to judge the recorded output. Cannot be "
                                                  "combined with on_date.")


def _unavailable(stage: str, label: str, start: str, end: str, statistic: str, base: dict | None) -> dict:
    """A comparison that cannot be completed: known facts stay, nothing is invented."""
    return {"stage": stage, "label": label, "statistic": statistic, "start": start, "end": end, "observed_days": 0,
            "actual": None, "baseline_median": base["baseline_median"] if base else None, "robust_sigma": None,
            "z": None, "pct_vs_baseline": None, "tier": None, "direction": None, "consecutive_low_days": 0,
            "window": base["window"] if base else None, "window_days": base["window_days"] if base else 0}


def _daily(stage: str, series: list, target: str, value: float | None, warnings: list[str]) -> tuple[dict, list]:
    quoted = value is not None
    if quoted:  # a hypothetical number, judged against the latest baseline
        idx, series_ext, label = len(series), series + [("quoted", value)], "quoted value vs the latest baseline"
    else:
        idx, series_ext, label = [d for d, _ in series].index(target), series, f"output on {target}"
    r = judge(series_ext, idx, quoted=quoted)
    observed = [] if quoted else [series[idx]]
    statistic = "quoted" if quoted else "daily"
    if r is None:
        warnings.append(f"{stage}: fewer than 5 prior working days; cannot judge")
        row = _unavailable(stage, label, target, target, statistic, None)
        row.update(actual=series_ext[idx][1], observed_days=0 if quoted else 1)
        return row, observed
    if r["window_days"] < NORMAL_WINDOW_WORKING_DAYS:
        warnings.append(f"{stage}: baseline uses only {r['window_days']} working days")
    return ({"stage": stage, "label": label, "statistic": statistic, "start": target, "end": target,
             "observed_days": 0 if quoted else 1, "actual": r["actual"], "baseline_median": r["baseline_median"],
             "robust_sigma": round(r["robust_sigma"], 1), "z": round(r["z"], 2),
             "pct_vs_baseline": r["pct_vs_baseline"], "tier": r["tier"], "direction": r["direction"],
             "consecutive_low_days": r["consecutive_low_days"], "window": r["window"],
             "window_days": r["window_days"]}, observed)


def _period(stage: str, series: list, start: str, end: str, warnings: list[str]) -> dict:
    """Mean per working day against the baseline before the period. A gap means no mean: a missing day is not zero."""
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    expected = [d for d in (first + timedelta(days=i) for i in range((last - first).days + 1)) if d.weekday() != 6]
    values = [v for d, v in series if start <= d <= end]
    base = baseline_before(series, start)
    row = _unavailable(stage, f"mean output {start}..{end}", start, end, "mean", base)
    if not expected or len(values) < len(expected):
        warnings.append(f"{stage}: {len(values)} of {len(expected)} working days recorded for {start}..{end}; "
                        "no mean is computed for an incomplete period")
        return row
    mean = statistics.fmean(values)
    pct = pct_change(mean, base["baseline_median"]) if base else None
    row.update(actual=round(mean, 1), observed_days=len(values), pct_vs_baseline=pct,
               direction=None if pct is None else "below" if pct < 0 else "above" if pct > 0 else "within")
    if base is None:
        warnings.append(f"{stage}: fewer than 5 working days before {start}; cannot compare")
    return row


@tool("compare_to_normal", "judgement",
      "Judge whether a stage's daily output is normal using the documented robust-z rule (baseline = median of "
      "the previous 20 working days). Returns actual, baseline, z, % vs baseline, tier (normal / briefing / "
      "interrupt), consecutive low days, and the rule itself. With through_date, compares the mean per working day "
      "of a period with the baseline before it. Sundays are closed, never abnormal. Missing data is reported as "
      "unavailable, and the percentage is null when it cannot be computed.", CompareToNormalParams)
def compare_to_normal(ctx: ToolContext, stage: str | None = None, on_date: str | None = None,
                      value: float | None = None, through_date: str | None = None) -> ToolResult:
    stages = stages_for(stage)
    if stages is None:
        return ctx.fail(ErrorCode.INVALID_ARGUMENT, "stage must be KNITTING, ASSEMBLY, WASHING, PACKING or ALL")
    if value is not None and on_date is not None:
        return ctx.fail(ErrorCode.INVALID_ARGUMENT, "give on_date to judge the recorded output of that day, OR value "
                        "to judge a number the manager quoted — not both")
    if through_date is not None and on_date is None:
        return ctx.fail(ErrorCode.INVALID_ARGUMENT, "through_date needs on_date as the first day of the period")
    lo, hi = log_range(ctx)
    if on_date is not None:
        try:
            day = date.fromisoformat(on_date)
            last = date.fromisoformat(through_date) if through_date else day
        except ValueError:
            return ctx.fail(ErrorCode.INVALID_ARGUMENT, "dates must be ISO (YYYY-MM-DD); use resolve_time first")
        if through_date is None and day.weekday() == 6:
            return ctx.ok({"date": on_date, "closed": True,
                           "message": "Sunday: the factory is closed, so zero output is expected"},
                          definition=DEFINITION)
        if not (lo <= on_date <= hi and lo <= last.isoformat() <= hi):
            return ctx.fail(ErrorCode.INVALID_ARGUMENT, f"the production log covers {lo} to {hi}")
        if last < day:
            return ctx.fail(ErrorCode.INVALID_ARGUMENT, "through_date is before on_date")
    results, evidence, warnings = [], [], []
    for s in stages:
        series = working_series(ctx.db, s)
        target = on_date or hi
        if through_date is not None:
            row = _period(s, series, on_date, through_date, warnings)
            observed = [(d, v) for d, v in series if on_date <= d <= through_date]
        elif value is None and target not in [d for d, _ in series]:
            warnings.append(f"{s}: no output is recorded for {target}")
            row = _unavailable(s, f"output on {target}", target, target, "daily", baseline_before(series, target))
            observed = []
        else:
            row, observed = _daily(s, series, target, value, warnings)
        window = [(d, v) for d, v in series if row["window"] and row["window"][0] <= d <= row["window"][1]]
        rows = ([{"date": d, "stage": s, "pieces_completed": v, "role": "baseline"} for d, v in window]
                + [{"date": d, "stage": s, "pieces_completed": v, "role": "observed"} for d, v in observed])
        if rows:  # the claim and its baseline: every figure expands to the rows behind it
            what = f"{s} {row['label']}" + (f"; baseline window {row['window'][0]}..{row['window'][1]}"
                                            if row["window"] else "")
            ev = ctx.evidence.register("production_log", [f"{r['date']}/{s}" for r in rows], what, rows)
            evidence.append(ev)
            row["evidence_id"] = ev.id
        results.append(row)
    return ctx.ok({"results": results}, evidence, definition=DEFINITION, warnings=warnings)
