"""Render the details of a feasibility answer from the tool result, so every estimate has the same layout.

The model still writes the headline (the verdict in its words, checked by the verifier); the supporting block —
in-house dates, the workshop options, exclusions, assumptions — is built here from estimate_feasibility's
output. Choosing "fastest" and "lowest defect rate in time" is a sort in code, not model arithmetic.
"""

from __future__ import annotations

from typing import Any

from app.agent.respond import RespondArgs


def _latest_estimate(results: list[tuple[str, dict[str, Any]]]) -> dict[str, Any] | None:
    for name, result in reversed(results):
        if name == "estimate_feasibility" and result.get("ok"):
            return result
    return None


def _money(x: float) -> str:
    return f"{x:,.2f}"


def details(result: dict[str, Any]) -> str:
    d = result["data"]
    req, inh = d["request"], d["in_house"]
    due = req["due_date"]
    what = f"{req['pieces']} × {req['product'] or req['category']}"
    lines = [f"**Request:** {what}" + (f", due {due}" if due else ", no deadline given")
             + f" · verdict **{d['verdict']}**", ""]
    inhouse = f"**In-house:** P50 {inh['p50_finish']} · P80 {inh['p80_finish']}"
    if due:
        inhouse += (" — meets the due date" if inh["meets_due_p80"] else
                    " — meets it only at P50" if inh["meets_due_p50"] else " — misses the due date")
    lines += [inhouse, ""]
    eligible = sorted((o for o in d["workshops"] if o["eligible"]), key=lambda o: (o["finish_date"], o["defect_rate"]))
    if eligible:
        head = "| Workshop | Back by | Total cost | Defect rate |" + (" In time |" if due else "")
        rule = "|---|---|---|---|" + ("---|" if due else "")
        lines += ["**Outside workshops** (fastest first)", "", head, rule]
        for o in eligible:
            row = f"| {o['workshop']} | {o['finish_date']} | {_money(o['cost'])} | {o['defect_rate_pct']:g}% |"
            lines.append(row + ((" yes |" if o["meets_due"] else " no |") if due else ""))
        lines.append("")
        in_time = [o for o in eligible if o["meets_due"]] if due else eligible
        if in_time:
            best = min(in_time, key=lambda o: (o["defect_rate"], o["finish_date"]))
            pick = f"Fastest: **{eligible[0]['workshop']}** ({eligible[0]['finish_date']})"
            if best["workshop"] != eligible[0]["workshop"]:
                pick += (f" · lowest defect rate{' in time' if due else ''}: **{best['workshop']}** "
                         f"({best['defect_rate_pct']:g}%)")
            lines += [pick, ""]
    else:
        lines += ["**Outside workshops:** none can take this batch.", ""]
    excluded = [o for o in d["workshops"] if not o["eligible"]]
    if excluded:
        lines += ["**Not eligible:** " + "; ".join(f"{o['workshop']} ({o['reason_ineligible']})" for o in excluded),
                  ""]
    notes = list(d.get("assumptions", [])) + list(result.get("warnings", []))
    if notes:
        lines += ["**Assumptions and cautions**", ""] + [f"- {n}" for n in notes]
    return "\n".join(lines).strip()


def apply(draft: RespondArgs, results: list[tuple[str, dict[str, Any]]]) -> RespondArgs:
    """For an estimate, replace the model's details with the rendered block and cite its evidence."""
    if draft.kind != "estimate":
        return draft
    est = _latest_estimate(results)
    if est is None:
        return draft
    ev = [e["id"] for e in est.get("evidence", [])]
    return draft.model_copy(update={"details": details(est),
                                    "evidence_ids": list(dict.fromkeys(list(draft.evidence_ids) + ev))})
