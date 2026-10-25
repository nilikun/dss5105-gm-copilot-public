"""resolve_time — turn relative time phrases into explicit dates (Retrieval; TOOL_SPEC tool 1).

Date arithmetic is arithmetic, so the model never does it. Conventions (stated in `interpretation`):
- a bare weekday ("Friday", "by Friday") is the next such day on or after today;
- "last <weekday>" is the most recent one before today; "next <weekday>" is the one in next week (Mon–Sun);
- "the 25th" is this month if the 25th has not passed, otherwise AMBIGUOUS (last month's vs next month's);
- weeks run Monday–Sunday.
"""

from __future__ import annotations

import calendar
import re
from datetime import date, timedelta

from pydantic import BaseModel, Field

from app.domain.calendar import working_days_between
from app.tools.base import ErrorCode, ToolContext, ToolResult
from app.tools.registry import tool

WEEKDAYS = {name: i for i, name in enumerate(
    ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"])}
WEEKDAYS |= {name[:3]: i for name, i in list(WEEKDAYS.items())}
MONTHS = {name.lower(): i for i, name in enumerate(calendar.month_name) if name}
MONTHS |= {name[:3]: i for name, i in list(MONTHS.items())}
FILLER = re.compile(r"^(by|on|until|before|for|since|from)\s+")


class _Ambiguous(Exception):
    def __init__(self, options: list[tuple[date, str]]):
        self.options = options


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _day_of_month(today: date, day: int) -> date:
    if day >= today.day:
        return today.replace(day=day)
    prev = (today.replace(day=1) - timedelta(days=1))
    nxt_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
    options = []
    for base in (prev, nxt_month):
        try:
            options.append((base.replace(day=day), f"the {day}th of {calendar.month_name[base.month]}"))
        except ValueError:
            pass
    raise _Ambiguous(options)


def _parse(expr: str, today: date) -> tuple[date, date, str]:
    e = FILLER.sub("", expr.strip().lower()).strip(" ?.!")
    if e in ("today", "now", "this morning"):
        return today, today, "today"
    if e == "yesterday":
        return today - timedelta(days=1), today - timedelta(days=1), "yesterday"
    if e == "tomorrow":
        return today + timedelta(days=1), today + timedelta(days=1), "tomorrow"
    if e in ("this week", "the week"):
        s = _week_start(today)
        return s, s + timedelta(days=6), "this week (Mon–Sun)"
    if e == "last week":
        s = _week_start(today) - timedelta(days=7)
        return s, s + timedelta(days=6), "last week (Mon–Sun)"
    if e == "next week":
        s = _week_start(today) + timedelta(days=7)
        return s, s + timedelta(days=6), "next week (Mon–Sun)"
    if e in ("end of the month", "end of month", "month end"):
        last = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        return last, last, "last day of this month"
    if m := re.fullmatch(r"(?:the )?(?:last|past) (\d+) days", e):
        n = int(m.group(1))
        return today - timedelta(days=n), today - timedelta(days=1), f"the {n} days before today"
    if m := re.fullmatch(r"in (\d+) days", e):
        d = today + timedelta(days=int(m.group(1)))
        return d, d, f"{m.group(1)} days from today"
    if m := re.fullmatch(r"(last|next|this)?\s*([a-z]+)", e):
        mod, word = m.group(1), m.group(2)
        if word in WEEKDAYS:
            wd = WEEKDAYS[word]
            if mod == "last":
                d = today - timedelta(days=((today.weekday() - wd) % 7) or 7)
                how = "the most recent one before today"
            elif mod == "next":
                d = _week_start(today) + timedelta(days=7 + wd)
                how = "the one in next week"
            else:
                d = today + timedelta(days=(wd - today.weekday()) % 7)
                how = "the next one on or after today"
            return d, d, f"{calendar.day_name[wd]}, {how}"
    if m := re.fullmatch(r"(?:the )?(\d{1,2})(?:st|nd|rd|th)?", e):
        d = _day_of_month(today, int(m.group(1)))
        return d, d, f"the {m.group(1)} of this month"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", e):
        d = date.fromisoformat(e)
        return d, d, "explicit date"
    if m := re.fullmatch(r"(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?([a-z]+)\.?(?:,?\s*(\d{4}))?", e) or \
            re.fullmatch(r"([a-z]+)\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s*(\d{4}))?", e):
        a, b, y = m.groups()
        day, month = (int(a), b) if a.isdigit() else (int(b), a)
        if month in MONTHS:
            d = date(int(y) if y else today.year, MONTHS[month], day)
            return d, d, "explicit date"
    raise ValueError(expr)


class ResolveTimeParams(BaseModel):
    expression: str = Field(description="Time phrase as the manager said it: 'yesterday', 'Friday', 'the 25th', "
                                        "'last week', 'April 10', '2026-04-10'")


@tool("resolve_time", "retrieval",
      "Turn a relative time phrase into explicit ISO dates against the system clock. ALWAYS use this instead of "
      "computing dates yourself. Returns start/end, working days in range and whether it includes a Sunday.",
      ResolveTimeParams)
def resolve_time(ctx: ToolContext, expression: str) -> ToolResult:
    """Resolve a time phrase against the clock. Returns start/end dates, working days and flags."""
    today = ctx.clock.today()
    try:
        start, end, how = _parse(expression, today)
    except _Ambiguous as a:
        return ctx.fail(ErrorCode.AMBIGUOUS, f"'{expression}' could mean more than one date",
                        candidates=[{"date": d.isoformat(), "meaning": why} for d, why in a.options])
    except ValueError:
        return ctx.fail(ErrorCode.INVALID_ARGUMENT,
                        f"cannot interpret '{expression}' as a date; give a weekday, a date, or a phrase like "
                        "'last week'")
    warnings = []
    if start == end and start.weekday() == 6:
        warnings.append(f"{start.isoformat()} is a Sunday: the factory is closed")
    return ctx.ok({
        "expression": expression,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "interpretation": how,
        "working_days": working_days_between(start, end + timedelta(days=1)),
        "includes_sunday": any((start + timedelta(days=i)).weekday() == 6 for i in range((end - start).days + 1)),
        "is_past": end < today,
        "today": today.isoformat(),
    }, warnings=warnings)
