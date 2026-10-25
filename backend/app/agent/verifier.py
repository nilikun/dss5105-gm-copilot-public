"""The deterministic verifier — the code gate every reply passes before the manager sees it (Definition 1).

Checks: (1) every number, date and id is supported by this turn's tool outputs (or the manager's own words);
(2) cited evidence was produced this turn; (3) the headline is at most 3 lines; (4) clarifications offer
options; (5) proposals exist and are still pending; (6) the reply does not claim an action was executed.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.agent.respond import RespondArgs
from app.domain import grounding

EXECUTED_CLAIM = re.compile(r"\b(i(?:'ve| have)|has been|have been|was|were|is now|are now)\s+"
                            r"(sent|added|set|scheduled|created|cancelled|canceled|posted|emailed|done)\b", re.I)
NEGATION = re.compile(r"n't|\b(not|nothing|none|no|never|neither|until|once|when|after|before|if|unless|yet)\b",
                      re.I)
MAX_HEADLINE_LINES = 3


def claims_execution(text: str) -> bool:
    """A positive claim that an action happened ('the watch has been set'), ignoring negated or conditional
    phrasing ('nothing has been sent yet', 'it will be sent once you confirm')."""
    for m in EXECUTED_CLAIM.finditer(text):
        window = text[max(0, m.start() - 30):m.end() + 12]
        if not NEGATION.search(window):
            return True
    return False
MAX_HEADLINE_CHARS = 420


@dataclass
class Verdict:
    ok: bool
    violations: list[str] = field(default_factory=list)
    checked_tokens: int = 0


def allowed_tokens(tool_outputs: list[Any], user_text: str, now: datetime) -> grounding.Allowed:
    allowed = grounding.Allowed()
    for out in tool_outputs:
        allowed.absorb(out, now.year)
    allowed.absorb(user_text, now.year)
    allowed.absorb(now.date().isoformat(), now.year)
    return allowed


def reply_text(r: RespondArgs) -> str:
    parts = [r.headline, r.details or "", r.clarification_question or ""]
    parts += [o.label + " " + o.value for o in r.options] + r.followups
    return "\n".join(parts)


def verify(r: RespondArgs, tool_outputs: list[Any], user_text: str, now: datetime, issued_evidence: set[str],
           db: sqlite3.Connection, turn_id: str) -> Verdict:
    problems: list[str] = []
    allowed = allowed_tokens(tool_outputs, user_text, now)
    text = reply_text(r)
    problems += grounding.violations(text, allowed, now.year, issued_evidence)
    for e in r.evidence_ids:
        if e not in issued_evidence:
            problems.append(f"evidence {e} was not produced in this turn")
    lines = [ln for ln in r.headline.strip().splitlines() if ln.strip()]
    if len(lines) > MAX_HEADLINE_LINES or len(r.headline) > MAX_HEADLINE_CHARS:
        problems.append(f"headline must be at most {MAX_HEADLINE_LINES} short lines")
    if r.kind == "clarify":
        if len(r.options) == 1:
            problems.append("a clarification must offer either no options or at least 2 options")
        if not r.options and not r.clarification_question:
            problems.append("a clarification without candidates must ask for the missing identifier")
    if r.kind == "propose" and not r.proposal_ids:
        problems.append("kind=propose needs the proposal_ids returned by propose_* tools")
    for pid in r.proposal_ids:
        row = db.execute("SELECT status, turn_id FROM pending_actions WHERE action_id = ?", (pid,)).fetchone()
        if row is None or row["turn_id"] != turn_id:
            problems.append(f"proposal {pid} was not created in this turn")
        elif row["status"] != "pending":
            problems.append(f"proposal {pid} is {row['status']}")
    if (r.kind == "propose" or r.proposal_ids) and claims_execution(text):
        problems.append("the reply claims the action was carried out; it only awaits the manager's confirmation")
    tokens = grounding.extract(text, now.year)
    return Verdict(ok=not problems, violations=problems,
                   checked_tokens=len(tokens.numbers) + len(tokens.dates) + len(tokens.ids))
