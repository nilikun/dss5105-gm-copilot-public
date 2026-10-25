import pytest

from app.clock import SimClock
from app.tools.base import ErrorCode, ToolContext
from app.tools.retrieval.time import resolve_time


@pytest.mark.parametrize("expr, start, end", [
    ("today", "2026-04-01", "2026-04-01"),
    ("yesterday", "2026-03-31", "2026-03-31"),
    ("tomorrow", "2026-04-02", "2026-04-02"),
    ("Thursday", "2026-04-02", "2026-04-02"),
    ("by Friday", "2026-04-03", "2026-04-03"),
    ("Wednesday", "2026-04-01", "2026-04-01"),
    ("Monday", "2026-04-06", "2026-04-06"),
    ("last Monday", "2026-03-30", "2026-03-30"),
    ("next Monday", "2026-04-06", "2026-04-06"),
    ("last week", "2026-03-23", "2026-03-29"),
    ("this week", "2026-03-30", "2026-04-05"),
    ("the 25th", "2026-04-25", "2026-04-25"),
    ("25th", "2026-04-25", "2026-04-25"),
    ("April 10", "2026-04-10", "2026-04-10"),
    ("10 April", "2026-04-10", "2026-04-10"),
    ("Apr 10, 2026", "2026-04-10", "2026-04-10"),
    ("2026-05-01", "2026-05-01", "2026-05-01"),
    ("end of the month", "2026-04-30", "2026-04-30"),
    ("last 7 days", "2026-03-25", "2026-03-31"),
    ("in 3 days", "2026-04-04", "2026-04-04"),
])
def test_resolves(ctx, expr, start, end):
    r = resolve_time(ctx, expr)
    assert r.ok, r.error
    assert (r.data["start"], r.data["end"]) == (start, end)


def test_last_week_counts_working_days(ctx):
    r = resolve_time(ctx, "last week")
    assert r.data["working_days"] == 6
    assert r.data["includes_sunday"] is True
    assert r.data["is_past"] is True


def test_sunday_warning(ctx):
    r = resolve_time(ctx, "2026-03-29")
    assert any("Sunday" in w for w in r.warnings)


def test_passed_day_of_month_is_ambiguous(db):
    ctx = ToolContext(db=db, clock=SimClock.at("2026-04-10"))
    r = resolve_time(ctx, "the 5th")
    assert not r.ok and r.error.code == ErrorCode.AMBIGUOUS
    assert {c["date"] for c in r.error.candidates} == {"2026-03-05", "2026-05-05"}


def test_unparseable(ctx):
    r = resolve_time(ctx, "when the cows come home")
    assert not r.ok and r.error.code == ErrorCode.INVALID_ARGUMENT
