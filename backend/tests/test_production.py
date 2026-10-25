import numpy as np
import pytest

from app.tools.base import ErrorCode
from app.tools.judgement.normal import compare_to_normal
from app.tools.retrieval.production import get_stage_output


def pandas_z(log_df, stage, day):
    s = log_df[(log_df.stage == stage) & (log_df.date.dt.dayofweek != 6)].set_index("date").pieces_completed
    hist = s[s.index < day].tail(20)
    med = hist.median()
    return (s[day] - med) / (1.4826 * np.median(np.abs(hist - med))), med


# ----------------------------------------------------------------- get_stage_output
def test_packing_last_week(ctx, log_df):
    r = get_stage_output(ctx, "2026-03-23", "2026-03-29", stage="PACKING")
    expected = log_df[(log_df.stage == "PACKING") & log_df.date.between("2026-03-23", "2026-03-29")]
    assert r.data["totals"]["PACKING"] == int(expected.pieces_completed.sum()) == 3983
    assert r.data["working_days"] == 6
    assert any(row["is_sunday"] for row in r.data["series"])


def test_weekly_granularity(ctx):
    r = get_stage_output(ctx, "2026-03-16", "2026-03-31", stage="ASSEMBLY", granularity="week")
    weeks = {w["week_start"]: w for w in r.data["series"]}
    assert set(weeks) == {"2026-03-16", "2026-03-23", "2026-03-30"}
    assert weeks["2026-03-30"]["partial_week"] and not weeks["2026-03-16"]["partial_week"]


def test_out_of_range(ctx):
    r = get_stage_output(ctx, "2026-05-01", "2026-05-07")
    assert not r.ok and r.error.code == ErrorCode.INVALID_ARGUMENT and "2026-03-31" in r.error.message


def test_clipping_warns(ctx):
    r = get_stage_output(ctx, "2026-03-30", "2026-04-05", stage="KNITTING")
    assert r.ok and r.warnings and r.data["to"] == "2026-03-31"


# ----------------------------------------------------------------- compare_to_normal
def test_assembly_yesterday_is_interrupt_tier(ctx, log_df):
    r = compare_to_normal(ctx, stage="ASSEMBLY", on_date="2026-03-31")
    res = r.data["results"][0]
    z, med = pandas_z(log_df, "ASSEMBLY", np.datetime64("2026-03-31"))
    assert res["actual"] == 455 and res["baseline_median"] == med
    assert res["z"] == pytest.approx(z, abs=0.01)
    assert res["tier"] == "interrupt" and res["direction"] == "below"
    assert res["consecutive_low_days"] == 6  # 25, 26, 27, 28, 30, 31 March
    assert r.definition and "median" in r.definition["baseline"]


def test_z_matches_pandas_everywhere(ctx, log_df):
    days = sorted(d for d in log_df.date.unique() if np.datetime64(d).astype("datetime64[D]").item().weekday() != 6)
    for stage in ("KNITTING", "ASSEMBLY", "WASHING", "PACKING"):
        for d in days[20:]:
            iso = str(np.datetime64(d, "D"))
            res = compare_to_normal(ctx, stage=stage, on_date=iso).data["results"][0]
            z, _ = pandas_z(log_df, stage, np.datetime64(d))
            assert res["z"] == pytest.approx(z, abs=0.01), (stage, iso)


def test_quoted_value_uses_latest_window(ctx):
    res = compare_to_normal(ctx, stage="KNITTING", value=900).data["results"][0]
    assert res["tier"] == "normal" and res["baseline_median"] == 886.5
    assert res["window"][1] == "2026-03-31"


def test_quoted_value_ignores_recent_real_days(ctx):
    # a normal-looking quoted assembly number must not inherit the real slump via the 2-of-3 rule
    res = compare_to_normal(ctx, stage="ASSEMBLY", value=760).data["results"][0]
    assert res["tier"] in ("normal", "briefing")


def test_sunday_is_closed_not_abnormal(ctx):
    r = compare_to_normal(ctx, stage="PACKING", on_date="2026-03-29")
    assert r.ok and r.data["closed"]


def test_clean_period_false_alert_rate_matches_backtest(ctx, log_df):
    """Interrupt tier raised no alert on clean data in the backtest; the tool must agree."""
    days = sorted({str(np.datetime64(d, "D")) for d in log_df.date.unique()})
    clean = [d for d in days if "2026-02-01" <= d < "2026-03-25"]
    flags = [compare_to_normal(ctx, on_date=d).data.get("results", []) for d in clean]
    assert not any(r["tier"] == "interrupt" for day in flags for r in day)


def test_value_and_date_together_is_rejected(ctx):
    """Regression: the model once passed value=0 with on_date and the tool judged 0 instead of the recorded 455."""
    r = compare_to_normal(ctx, stage="ASSEMBLY", on_date="2026-03-31", value=0)
    assert not r.ok and r.error.code == ErrorCode.INVALID_ARGUMENT
