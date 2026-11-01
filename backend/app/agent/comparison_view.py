"""Render a comparison reply from compare_to_normal's validated fields, so a figure cannot be dropped (dev D35).

The route owns a turn only when the question is about one stage's recorded output: the single comparison was made
with supporting lookups at most, and the model drafted an answer, or a refusal of a "why?" question. A refusal of
anything else, an action reply or a clarification stays with the model: a lookup made on the way to those must not
replace them with a report. The wording follows eval/answer-contracts.md; the verifier still checks the result.
"""

from __future__ import annotations

import re
from typing import Any

from app.agent.respond import RespondArgs

SUPPORT_TOOLS = {"compare_to_normal", "resolve_time", "describe_data_coverage", "get_stage_output"}
CAUSE_QUESTION = re.compile(r"\b(why|cause[ds]?|reasons?|because|explain)\b", re.I)
CAUSE_UNKNOWN = "The cause is unknown from these data."


def _num(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else f"{x:.1f}"


def _change(pct: float | None) -> str:
    if pct is None:
        return "."
    if pct == 0:
        return ", 0.0% versus baseline."
    return f", {abs(pct):.1f}% {'below' if pct < 0 else 'above'} baseline."


def _verdict(r: dict[str, Any]) -> str:
    """The judgement in words. No z when the baseline did not vary: it says nothing then."""
    if r["tier"] is None or not r["robust_sigma"]:
        return ""
    if r["tier"] != "normal" and r["direction"] == "below":
        streak = r["consecutive_low_days"]
        run = f", {streak} low working days in a row" if streak > 1 else ""
        return f" Judged not normal: {r['tier']} tier, z = {r['z']}{run}."
    if r["direction"] == "above":
        return f" Judged unusually high: z = {r['z']}."
    return f" Judged normal: z = {r['z']}."


def _single_comparison(results: list[tuple[str, dict[str, Any]]]) -> dict[str, Any] | None:
    """The one recorded comparison of this turn, or None if the turn did anything else."""
    if any(name not in SUPPORT_TOOLS for name, _ in results):
        return None
    done = [r for name, r in results if name == "compare_to_normal" and r.get("ok") and r["data"].get("results")]
    if len(done) != 1 or len(done[0]["data"]["results"]) != 1:
        return None
    return done[0] if done[0]["data"]["results"][0]["statistic"] != "quoted" else None


def apply(draft: RespondArgs, results: list[tuple[str, dict[str, Any]]], user_text: str) -> RespondArgs:
    asks_cause = bool(CAUSE_QUESTION.search(user_text))
    if not (draft.kind == "answer" or (draft.kind == "refuse" and asks_cause)):
        return draft
    result = _single_comparison(results)
    if result is None:
        return draft
    r = result["data"]["results"][0]
    name, start, end = r["stage"].capitalize(), r["start"], r["end"]
    if r["actual"] is None:
        head = (f"{name} output is unavailable on {start}." if r["statistic"] == "daily"
                else f"{name} output is unavailable from {start} to {end}.")
    elif r["statistic"] == "mean":
        head = f"{name} averaged {_num(r['actual'])} pieces per working day from {start} to {end}"
        head += _change(r["pct_vs_baseline"])
    else:
        head = f"{name} output was {_num(r['actual'])} pieces on {start}" + _change(r["pct_vs_baseline"])
    parts = []
    if r["baseline_median"] is None:
        parts.append("The baseline is unavailable.")
    else:
        parts.append(f"The baseline was the median of {r['window_days']} working days from {r['window'][0]} to "
                     f"{r['window'][1]}: {_num(r['baseline_median'])} pieces/day.")
    if r["pct_vs_baseline"] is None:
        parts.append("Percentage change cannot be computed.")
    parts.append(CAUSE_UNKNOWN)
    return RespondArgs(kind="refuse" if asks_cause else "answer", headline=head + _verdict(r),
                       details=" ".join(parts), evidence_ids=[e["id"] for e in result.get("evidence", [])])
