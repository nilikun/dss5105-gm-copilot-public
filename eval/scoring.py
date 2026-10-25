"""Scoring rules for one evaluation item (docs/EVAL_PLAN.md §4). Pure functions — no model, no database.

Decision = the expected behaviour AND every `must_include` fact AND no `must_not_include` claim.
Faithfulness = the reply that reached the user passed the grounding verifier (Definition 1).

Matching rules, fixed before the first scored run and applied identically to dev and held-out:
- case-insensitive; a list inside `must_include` means any-of;
- numbers are compared as numbers, ignoring thousands separators and sign ("32,850" = "32850", "-44%" = "44%
  below"), and a reply value rounded to the item's precision counts ("72.7%" satisfies "73%");
- ISO dates match ISO or natural forms ("2026-04-03" = "3 Apr" = "April 3"), within the item's date tolerance;
- polar phrases ("normal", "at risk", "not normal") are checked for polarity, so "not normal" does not satisfy
  "normal" and "below normal" satisfies "not normal" (EQUIVALENTS below);
- "no" in a refusal item means the reply states a negative ("no", "not", "cannot", "isn't" …);
- a `must_not_include` phrase only counts when it is asserted, not when negated or conditional
  ("nothing has been sent yet" does not trip "sent"). "$" always counts.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.domain import grounding  # noqa: E402

YEAR = 2026
KIND_FOR = {"answer": "answer", "estimate": "estimate", "clarify": "clarify", "refuse": "refuse",
            "propose_action": "propose", "reject_action": "reject"}
NUMERIC = re.compile(r"^[-−]?\d[\d,]*(\.\d+)?%?$")
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
NEGATIVE = re.compile(r"\b(no|not|none|cannot|can't|don't|doesn't|isn't|aren't|won't|unavailable|n't)\b", re.I)
NEGATION_BEFORE = re.compile(r"n't|\b(not|nothing|none|no|never|until|once|when|after|before|if|unless|yet|only|"
                             r"will|would|to be)\b", re.I)
NEGATED_NORMAL = re.compile(r"(\bnot\b|n't)[^.]{0,20}\bnormal\b", re.I)  # "isn't normal", "not within normal"

# Phrases with a polarity. Each maps to the surface forms that express it; a match preceded by a negation
# ("not", "isn't") is not counted. Written from the meaning of the item, not from model output.
EQUIVALENTS: dict[str, list[str]] = {
    "not normal": ["not normal", "below normal", "above normal", "abnormal", "abnormally", "outside the normal",
                   "outside normal", "not within", "unusually low", "unusually high", "well below", "far below",
                   "critically below"],
    "normal": ["normal", "within the normal", "typical", "usual"],
    "at risk": ["at risk", "at_risk", "likely late", "likely to be late", "likely to miss", "will miss",
                "projected to finish after", "projected to miss"],
    "complete": ["complete", "completed", "finished"],
    "not": ["not", "cannot", "can't", "won't", "no", "unable", "infeasible", "isn't", "doesn't", "don't", "aren't",
            "wasn't"],
}
# A positive polar phrase must not appear only in its negative form.
OPPOSITE = {"normal": "not normal"}


@dataclass
class ItemScore:
    behavior_ok: bool
    facts_ok: bool
    forbidden_ok: bool
    faithful: bool
    missing: list[str] = field(default_factory=list)
    forbidden_hits: list[str] = field(default_factory=list)

    @property
    def decision_ok(self) -> bool:
        return self.behavior_ok and self.facts_ok and self.forbidden_ok


def reply_text(reply: dict[str, Any]) -> str:
    """Everything the manager reads in the reply, with typographic apostrophes and quotes made plain."""
    parts = [reply.get("headline") or "", reply.get("details") or "", reply.get("clarification_question") or ""]
    parts += [o.get("label", "") for o in reply.get("options", [])]
    parts += [p.get("preview", "") for p in reply.get("proposals", [])]
    text = "\n".join(p for p in parts if p)
    return text.translate(str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"'}))


def _date_tol(tolerance: str) -> int:
    m = re.search(r"dates\s*±\s*(\d+)", tolerance or "")
    return int(m.group(1)) if m else 0


def _num(s: str) -> Decimal:
    return Decimal(s.replace(",", "").replace("%", "").replace("−", "-")).copy_abs()


def _places(s: str) -> int:
    s = s.replace("%", "")
    return len(s.split(".")[1]) if "." in s else 0


def has_number(text: str, want: str) -> bool:
    target, places = _num(want), _places(want)
    q = Decimal(1).scaleb(-places)
    for _, v in grounding.extract(text, YEAR).numbers:
        candidates = [v, v * 100] if want.endswith("%") and v < 1 else [v]  # 0.12 states the same fact as 12%
        if any(c == target or c.quantize(q, rounding=ROUND_HALF_UP) == target for c in candidates):
            return True
    return False


def has_date(text: str, want: str, tol_days: int) -> bool:
    w = date.fromisoformat(want)
    return any(abs((date.fromisoformat(d) - w).days) <= tol_days for d in grounding.extract(text, YEAR).dates)


def _asserted(text: str, phrase: str) -> bool:
    """`phrase` occurs somewhere not directly negated ("not at risk", "isn't normal")."""
    for m in re.finditer(r"(?<![A-Za-z])" + re.escape(phrase) + r"(?![A-Za-z])", text, re.I):
        before = text[max(0, m.start() - 12):m.start()]
        if not re.search(r"(\bnot|n't|\bno)\s*$", before, re.I):
            return True
    return False


def has_phrase(text: str, want: str) -> bool:
    w = want.lower()
    if w == "no":
        return bool(NEGATIVE.search(text))
    if w in EQUIVALENTS:
        hit = any(_asserted(text, form) if w not in ("not", "not normal") else
                  re.search(r"(?<![A-Za-z])" + re.escape(form) + r"(?![A-Za-z])", text, re.I)
                  for form in EQUIVALENTS[w])
        if w == "not normal" and not hit:
            # "isn't normal" / "is not within normal range"
            hit = bool(NEGATED_NORMAL.search(text))
        if hit and w in OPPOSITE:
            # "normal" must not be the negated form: strip negative-polarity phrases and look again
            stripped = text
            for form in EQUIVALENTS[OPPOSITE[w]]:
                stripped = re.sub(re.escape(form), " ", stripped, flags=re.I)
            stripped = NEGATED_NORMAL.sub(" ", stripped)
            hit = any(_asserted(stripped, form) for form in EQUIVALENTS[w])
        return bool(hit)
    return w in text.lower()


def contains(text: str, want: str, tolerance: str = "exact") -> bool:
    if ISO.match(want):
        return has_date(text, want, _date_tol(tolerance))
    if NUMERIC.match(want):
        return has_number(text, want)
    if re.match(r"^\d{1,2} [A-Za-z]{3}", want):  # "25 Mar"
        dates = grounding.extract(want, YEAR).dates
        return any(has_date(text, d, _date_tol(tolerance)) for d in dates)
    return has_phrase(text, want)


def forbidden(text: str, phrase: str) -> bool:
    """`phrase` is asserted in the reply (negated or conditional mentions do not count)."""
    if phrase == "$":
        return "$" in text
    for m in re.finditer(r"(?<![A-Za-z])" + re.escape(phrase) + r"(?![A-Za-z])", text, re.I):  # "unsent" ≠ "sent"
        window = text[max(0, m.start() - 40):m.end() + 12]
        if not NEGATION_BEFORE.search(window):
            return True
    return False


def score(item: dict[str, Any], reply: dict[str, Any]) -> ItemScore:
    text = reply_text(reply)
    accepted = {KIND_FOR[b] for b in [item["expected_behavior"], *item.get("expected_alternatives", [])]}
    behavior_ok = reply.get("kind") in accepted
    missing = []
    for want in item.get("must_include", []):
        options = want if isinstance(want, list) else [want]
        if not any(contains(text, str(o), item.get("tolerance", "exact")) for o in options):
            missing.append(" | ".join(map(str, options)))
    hits = [p for p in item.get("must_not_include", []) if forbidden(text, p)]
    return ItemScore(behavior_ok=behavior_ok, facts_ok=not missing, forbidden_ok=not hits,
                     faithful=bool(reply.get("grounded")) and reply.get("kind") != "fallback",
                     missing=missing, forbidden_hits=hits)
