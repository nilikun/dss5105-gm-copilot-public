"""Grounding: extract the factual tokens of a text (numbers, dates, IDs) and check each one is supported.

This is the mechanical core of Definition 1 (a reply r_t is grounded iff N(r_t) ⊆ N(O_t)). Supported means the
token appears in the tool outputs of the turn — allowing presentation changes that do not change the fact:
rounding to 0 or 1 decimals, a dropped minus sign ("40.2% below"), a fraction shown as a percentage
(0.12 → 12%), and dates written as "31 Mar" / "March 31" / "2026-03-31". Numbers the manager said themselves
(e.g. "800 hoodies by the 25th") may be echoed.
Known limitation (reported in the evaluation): spelled-out numbers ("six") are not extracted.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
MONTHS |= {m[:3].lower(): i for m, i in list(MONTHS.items())}
MONTHS["sept"] = 9
_MON = "|".join(sorted(MONTHS, key=len, reverse=True))

ISO_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
DAY_MON = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({_MON})\.?(?:,?\s+(\d{{4}}))?\b", re.I)
MON_DAY = re.compile(rf"\b({_MON})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s+(\d{{4}}))?\b", re.I)
IDS = re.compile(r"\b(ORD-\d{1,3}|WT-\d+|A-\d+|L-\d+|E\d+|W[1-9]\d?)\b")
TIME = re.compile(r"\b\d{1,2}:\d{2}\b")
LIST_MARKER = re.compile(r"(?m)^\s*\d+[.)]\s+")
NUMBER = re.compile(r"(?<![A-Za-z0-9_.])[-−–]?\d{1,3}(?:,\d{3})+(?:\.\d+)?|(?<![A-Za-z0-9_.])[-−–]?\d+(?:\.\d+)?")


def _dec(s: str) -> Decimal | None:
    try:
        return Decimal(s.replace(",", "").replace("−", "-").replace("–", "-")).copy_abs().normalize()
    except InvalidOperation:
        return None


@dataclass
class Facts:
    numbers: list[tuple[str, Decimal]] = field(default_factory=list)
    dates: set[str] = field(default_factory=set)
    ids: set[str] = field(default_factory=set)


def _mk_date(y: int, m: int, d: int) -> str | None:
    try:
        return date(y, m, d).isoformat()
    except ValueError:
        return None


def extract(text: str, year: int) -> Facts:
    """Factual tokens in a text. Dates, IDs, times and list markers are removed before numbers are read."""
    f = Facts()
    s = text or ""

    def take_iso(m):
        d = _mk_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if d:
            f.dates.add(d)
        return " "

    def take_day_mon(m):
        d = _mk_date(int(m.group(3) or year), MONTHS[m.group(2).lower()], int(m.group(1)))
        if d:
            f.dates.add(d)
        return " "

    def take_mon_day(m):
        d = _mk_date(int(m.group(3) or year), MONTHS[m.group(1).lower()], int(m.group(2)))
        if d:
            f.dates.add(d)
        return " "

    s = ISO_DATE.sub(take_iso, s)
    s = DAY_MON.sub(take_day_mon, s)
    s = MON_DAY.sub(take_mon_day, s)

    def take_id(m):
        f.ids.add(m.group(1))
        return " "

    s = IDS.sub(take_id, s)
    s = TIME.sub(" ", s)
    s = LIST_MARKER.sub(" ", s)
    for m in NUMBER.finditer(s):
        v = _dec(m.group(0))
        if v is not None:
            f.numbers.append((m.group(0), v))
    return f


@dataclass
class Allowed:
    numbers: set[Decimal] = field(default_factory=set)
    dates: set[str] = field(default_factory=set)
    ids: set[str] = field(default_factory=set)

    def add_number(self, x: float | int | Decimal) -> None:
        try:
            v = Decimal(str(x)).copy_abs()
        except InvalidOperation:
            return
        self.numbers.add(v.normalize())
        for places in ("1", "0.1"):
            self.numbers.add(v.quantize(Decimal(places), rounding=ROUND_HALF_UP).normalize())
        if Decimal(0) < v <= Decimal(1) and v != v.to_integral_value():
            pct = v * 100
            self.numbers.add(pct.normalize())
            for places in ("1", "0.1"):
                self.numbers.add(pct.quantize(Decimal(places), rounding=ROUND_HALF_UP).normalize())

    def absorb(self, obj: Any, year: int) -> None:
        """Add every number, date and ID found anywhere in a (JSON-like) object."""
        if isinstance(obj, bool) or obj is None:
            return
        if isinstance(obj, (int, float)):
            self.add_number(obj)
        elif isinstance(obj, str):
            facts = extract(obj, year)
            self.dates |= facts.dates
            self.ids |= facts.ids
            for _, v in facts.numbers:
                self.add_number(v)
        elif isinstance(obj, dict):
            for k, v in obj.items():
                self.absorb(k, year)
                self.absorb(v, year)
        elif isinstance(obj, (list, tuple, set)):
            for v in obj:
                self.absorb(v, year)


def violations(text: str, allowed: Allowed, year: int, evidence_ids: set[str] | None = None) -> list[str]:
    """Factual tokens in `text` that are not supported by `allowed`. Evidence IDs must be ones issued this turn."""
    facts = extract(text, year)
    out = []
    for raw, v in facts.numbers:
        if v not in allowed.numbers:
            out.append(f"number {raw.strip()} is not in any tool output of this turn")
    for d in sorted(facts.dates - allowed.dates):
        out.append(f"date {d} is not in any tool output of this turn")
    for i in sorted(facts.ids):
        if i.startswith("E") and i[1:].isdigit():
            if evidence_ids is not None and i not in evidence_ids:
                out.append(f"evidence {i} was not produced in this turn")
        elif i not in allowed.ids:
            out.append(f"id {i} is not in any tool output of this turn")
    return out
