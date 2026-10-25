"""Build an order-status reply from this turn's validated tool result, never LLM prose.

The purpose-built status route owns the whole short answer so an omitted deadline,
wrong-order date, contradictory follow-up or critic revision cannot leak through.
Mixed analytical/action turns keep the existing general response path.
"""

from __future__ import annotations

import re
from datetime import date

from app.agent.respond import Option, RespondArgs
from app.tools.retrieval.order_status import StatusFacts

SUPPORT_TOOLS = {"get_order_status", "get_order", "find_orders", "resolve_time"}


def clarification(candidates: list[dict], *, missing: bool = False) -> RespondArgs:
    labels = [c.get("order_id") or c.get("customer") or c.get("product") for c in candidates]
    labels = list(dict.fromkeys(label for label in labels if label))
    if missing:
        headline = "No matching order was found. Please provide the order ID or its customer and product."
    else:
        headline = "Which order do you mean? Please select a candidate or provide its order ID."
    # All candidates remain visible even when more than six fit the button limit.
    details = "Candidates: " + ", ".join(labels) + "." if labels else None
    options = [Option(label=label, value=f"What is the status of {label}?") for label in labels[:6]]
    if len(options) < 2:
        options = []
    return RespondArgs(kind="clarify", headline=headline, details=details,
                       clarification_question="Which order ID should I check?", options=options)


def render(results: list[tuple[str, dict]], user_text: str, today: date) -> RespondArgs | None:
    if not results or any(name not in SUPPORT_TOOLS for name, _ in results):
        return None
    status_results = [result for name, result in results if name == "get_order_status"]
    if not status_results:
        return None
    # A model cannot resolve an ambiguous lookup by choosing a candidate itself later in this turn.
    for _, result in results:
        error = result.get("error") or {}
        if error.get("code") == "AMBIGUOUS":
            return clarification(error.get("candidates", []))
    result = status_results[-1]
    if not result.get("ok"):
        return clarification([], missing=(result.get("error") or {}).get("code") == "NOT_FOUND")
    facts = StatusFacts.model_validate(result["data"]["status_facts"])
    explicit = {f"ORD-{int(n):03d}" for n in re.findall(r"\b(?:ord[ -]*|order\s*#?\s*)(\d+)\b", user_text, re.I)}
    resolved = {r["data"]["status_facts"]["order_id"] for r in status_results if r.get("ok")}
    if facts.as_of != today or len(resolved) != 1 or (explicit and explicit != {facts.order_id}):
        return clarification([])
    if facts.status == "COMPLETE":
        parts = [f"{facts.order_id} is complete."]
    else:
        parts = [f"{facts.order_id} is in {facts.stage.lower()}." if facts.stage
                 else f"{facts.order_id} is in progress; stage is unavailable."]
    parts.append(f"Due date {facts.due_date.isoformat()}." if facts.due_date else "Due date is unavailable.")
    if facts.status == "COMPLETE":
        parts.append(f"Completed on {facts.completed_date.isoformat()}." if facts.completed_date
                     else "Completion date is unavailable.")
    if facts.timing == "due_today":
        parts.append("Due today.")
    elif facts.timing == "on_time":
        parts.append("Completed on time.")
    elif facts.timing:
        parts.append(f"{facts.days} calendar days {facts.timing}.")
    else:
        parts.append("Timing cannot be calculated from the available dates.")
    return RespondArgs(kind="answer", headline=" ".join(parts),
                       details=f"As of {facts.as_of.isoformat()} (dataset clock).",
                       evidence_ids=[e["id"] for e in result.get("evidence", [])])
