import numpy as np
import pytest

from app.tools.base import ErrorCode
from app.tools.retrieval.orders import find_orders, get_order, summarize_orders
from tests.conftest import TODAY


# ----------------------------------------------------------------- get_order
@pytest.mark.parametrize("raw", ["ORD-120", "ord 120", "120", "order #120"])
def test_get_order_normalises_ids(ctx, raw):
    r = get_order(ctx, raw)
    assert r.ok and r.data["order_id"] == "ORD-120"


def test_get_order_matches_pandas(ctx, orders_df):
    for row in orders_df.itertuples():
        r = get_order(ctx, row.order_id)
        assert r.ok
        d = r.data
        assert d["current_stage"] == row.current_stage
        assert d["days_to_due"] == (row.due_date - TODAY).days
        assert d["is_overdue"] == (row.status == "IN_PROGRESS" and row.due_date < TODAY)
        if row.status == "IN_PROGRESS":
            expected_idle = int(np.busday_count(row.last_activity_date.date(), TODAY.date(), weekmask="1111110"))
            assert d["idle_working_days"] == expected_idle
        assert r.evidence and r.evidence[0].keys == [row.order_id]
        assert ctx.evidence.get(r.evidence[0].id)["rows"][0]["order_id"] == row.order_id


def test_completed_order_is_flagged(ctx):
    r = get_order(ctx, "ORD-058")
    assert r.data["status"] == "COMPLETE" and r.data["completed_date"] == "2026-03-12"
    assert any("COMPLETE" in w for w in r.warnings)
    assert r.data["stages_remaining"] == []


def test_unknown_order(ctx):
    r = get_order(ctx, "ORD-999")
    assert not r.ok and r.error.code == ErrorCode.NOT_FOUND and r.error.candidates


# ----------------------------------------------------------------- find_orders
def test_counts_match_pandas_for_every_customer(ctx, orders_df):
    for customer, n in orders_df.customer.value_counts().items():
        r = find_orders(ctx, customer=customer, limit=50)
        assert r.data["total_matches"] == n


@pytest.mark.parametrize("name, canonical", [("trend cart", "TrendCart"), ("northwind", "Northwind Apparel"),
                                             ("loom and leaf", "Loom & Leaf"), ("maple", "Maple & Co")])
def test_customer_aliases(ctx, name, canonical):
    r = find_orders(ctx, customer=name)
    assert r.ok and r.data["matched_as"]["customer"] == canonical


def test_ambiguous_single_reference(ctx, orders_df):
    r = find_orders(ctx, customer="TrendCart", status="open", expect_single=True)
    assert not r.ok and r.error.code == ErrorCode.AMBIGUOUS
    expected = set(orders_df[(orders_df.customer == "TrendCart") & (orders_df.status == "IN_PROGRESS")].order_id)
    assert {c["order_id"] for c in r.error.candidates} == expected
    assert r.error.candidates[0]["is_overdue"]  # most urgent first


def test_unique_indirect_reference(ctx):
    r = find_orders(ctx, customer="northwind", product="cardigans", status="open", expect_single=True)
    assert r.ok and [o["order_id"] for o in r.data["orders"]] == ["ORD-107"]


def test_overdue_matches_pandas(ctx, orders_df):
    r = find_orders(ctx, overdue=True, limit=50)
    expected = set(orders_df[(orders_df.status == "IN_PROGRESS") & (orders_df.due_date < TODAY)].order_id)
    assert {o["order_id"] for o in r.data["orders"]} == expected and r.data["total_matches"] == 8


def test_quiet_orders(ctx):
    r = find_orders(ctx, min_idle_working_days=3, status="open", sort_by="idle")
    assert [o["order_id"] for o in r.data["orders"]] == ["ORD-002", "ORD-005"]


def test_truncation_is_flagged(ctx):
    r = find_orders(ctx, status="open", limit=5)
    assert r.data["total_matches"] == 34 and len(r.data["orders"]) == 5 and r.data["truncated"]


def test_unknown_customer_lists_known_ones(ctx):
    r = find_orders(ctx, customer="Zara")
    assert not r.ok and r.error.code == ErrorCode.NOT_FOUND and len(r.error.candidates) == 8


def test_bad_date_bound_asks_for_resolution(ctx):
    r = find_orders(ctx, due_to="the 25th")
    assert not r.ok and r.error.code == ErrorCode.INVALID_ARGUMENT and "resolve_time" in r.error.message


# ----------------------------------------------------------------- summarize_orders
def test_open_totals(ctx, orders_df):
    r = summarize_orders(ctx, metrics=["count", "pieces_sum"], status="open")
    open_ = orders_df[orders_df.status == "IN_PROGRESS"]
    assert r.data["totals"] == {"count": len(open_), "pieces_sum": int(open_.pieces.sum())}


def test_lateness_by_customer_matches_pandas(ctx, orders_df):
    r = summarize_orders(ctx, group_by="customer", metrics=["late_rate", "avg_days_late"])
    done = orders_df[orders_df.status == "COMPLETE"]
    for g in r.data["groups"]:
        sub = done[done.customer == g["group"]]
        assert g["late_rate"]["late"] == int((sub.days_late > 0).sum())
        assert g["late_rate"]["completed"] == len(sub)
        assert g["avg_days_late"] == round(sub.days_late.mean(), 1)
    assert any("completed orders only" in w for w in r.warnings)
    worst = max(r.data["groups"], key=lambda g: g["late_rate"]["pct"])
    assert worst["group"] == "TrendCart" and worst["late_rate"]["pct"] == 73


def test_group_evidence_lists_members(ctx):
    r = summarize_orders(ctx, group_by="stage", metrics=["count"], status="open")
    for g in r.data["groups"]:
        assert len(ctx.evidence.get(g["evidence_id"])["keys"]) == g["count"]


def test_invalid_metric(ctx):
    r = summarize_orders(ctx, metrics=["revenue"])
    assert not r.ok and r.error.code == ErrorCode.INVALID_ARGUMENT
