"""Recompute a held-out package's stated facts from the CSVs, independently of the agent and its tools.

    uv run --no-project --with pandas --with pyyaml python eval/verify_references.py --package <private>/heldout.yaml \
        --output <private>/reference-verification.json

For each fact it selects rows using the entities and dates named in the fact and its evidence (order, workshop,
customer, product, stage, status, date window), computes the usual statistics on them, and looks for the stated value.
A value it reproduces is `recomputed`; one that contradicts a direct lookup of the same column is `contradicted`;
anything else (reasons, yes/no judgements, values needing logic this script lacks) is `not_recomputed`, which says
nothing either way. It proves a value can be reached from the stated rows, not that the fact is the right one to ask.

Prints and saves ids, methods and counts only, never question, answer or value text, so a developer can run it on a
package they must not read. Imports nothing from the agent or from the development reference generators.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
AS_OF = date(2026, 4, 1)
STAGES = ("KNITTING", "ASSEMBLY", "WASHING", "PACKING")
ISO = re.compile(r"\d{4}-\d{2}-\d{2}")


def _tolerance(fact: dict) -> float:
    value = fact.get("tolerance")
    if isinstance(value, str):
        found = re.search(r"\d+(?:\.\d+)?", value)
        return float(found[0]) if found else 0.0
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0.0


def _same(value: float, expected: float, tolerance: float) -> bool:
    """Equal within the tolerance, or to the precision the author wrote."""
    if not math.isfinite(value):
        return False
    decimals = len(str(expected).split(".")[1]) if "." in str(expected) else 0
    return abs(value - expected) <= tolerance or round(value, decimals) == expected


def _stats(frame: pd.DataFrame) -> dict[str, float]:
    out: dict[str, float] = {"count": float(len(frame))}
    if frame.empty:
        return out
    for column in frame.select_dtypes("number").columns:
        series = frame[column].dropna()
        if series.empty:
            continue
        for name, value in (("sum", series.sum()), ("mean", series.mean()), ("median", series.median()),
                            ("max", series.max()), ("min", series.min())):
            out[f"{name}:{column}"] = float(value)
        if frame[column].nunique() == 2 and set(frame[column].dropna().unique()) <= {0, 1}:
            out[f"share:{column}"] = float(100 * series.mean())
    return out


def _production_stats(log: pd.DataFrame, stage: str, dates: list[str]) -> dict[str, float]:
    """Daily or period output, with its fixed baseline: the median of the 20 Monday-Saturday days before it."""
    work = log[(log["stage"] == stage) & (pd.to_datetime(log["date"]).dt.weekday != 6)].sort_values("date")
    start, end = min(dates), max(dates)
    window = work[(work["date"] >= start) & (work["date"] <= end)]["pieces_completed"]
    prior = work[work["date"] < start]["pieces_completed"].tail(20)
    out: dict[str, float] = {}
    if len(window):
        out.update(actual=float(window.mean()), total=float(window.sum()), days=float(len(window)))
    if len(prior) == 20:
        median = float(prior.median())
        sigma = 1.4826 * float((prior - median).abs().median())
        out.update(baseline=median, sigma=sigma)
        if len(window):
            mean = float(window.mean())
            if median:
                change = 100 * (mean / median - 1)
                out.update(change=change, change_abs=abs(change))
            out.update(gap=mean - median, gap_abs=abs(mean - median))
            if sigma:
                out.update(z=(mean - median) / sigma, z_abs=abs(mean - median) / sigma)
    return out


def _order_stats(row: pd.Series) -> dict[str, float]:
    out: dict[str, float] = {}
    due = date.fromisoformat(str(row["due_date"]))
    out["days_to_due"] = float(abs((AS_OF - due).days))
    completed = row.get("completed_date")
    if isinstance(completed, str) and ISO.fullmatch(completed):
        out["days_vs_due"] = float(abs((date.fromisoformat(completed) - due).days))
    last = row.get("last_activity_date")
    if isinstance(last, str) and ISO.fullmatch(last):
        idle = (AS_OF - date.fromisoformat(last)).days
        out["idle_days"] = float(idle)
        out["idle_working_days"] = float(sum((AS_OF - timedelta(days=i)).weekday() != 6 for i in range(1, idle + 1)))
    return out


class Tables:
    def __init__(self, data: Path):
        self.orders = pd.read_csv(data / "orders.csv")
        self.log = pd.read_csv(data / "production_log.csv")
        self.workshops = pd.read_csv(data / "workshops.csv")
        self.vocab = {c: [str(v) for v in self.orders[c].dropna().unique()]
                      for c in ("customer", "product", "category", "status", "current_stage")}


def _mentions(text: str, value: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(value)}(?!\w)", text, re.I) is not None


def verify_fact(fact: dict, item: dict, t: Tables) -> tuple[str, str]:
    """(verdict, method). The method is a column or statistic name, never a value."""
    expected = fact.get("expected_value")
    evidence = " ".join(str(e.get(k, "")) for e in item.get("reference_evidence") or []
                        for k in ("row_filter", "calculation"))
    context = " ".join([str(fact.get("subject", "")), str(fact.get("field", "")), str(fact.get("dates_or_window", "")),
                        str(fact.get("calculation", "")), evidence])
    numeric = isinstance(expected, (int, float)) and not isinstance(expected, bool)
    if not numeric and not (isinstance(expected, str) and expected.strip()):
        return "not_recomputed", "no_comparable_value"
    tolerance = _tolerance(fact)

    # A named order or workshop: read the row, and the column the fact names when it names one.
    subject = str(fact.get("subject", ""))
    for table, key, pattern in ((t.orders, "order_id", r"ORD-\d+"), (t.workshops, "workshop_id", r"\bW\d+\b")):
        if key not in table:
            continue
        ids = re.findall(pattern, subject) or re.findall(pattern, str(item.get("reference_evidence")))
        rows = table[table[key].isin(ids)]
        if len(rows) != 1:
            continue
        row = rows.iloc[0]
        field = str(fact.get("field", "")).strip().lower().replace(" ", "_")
        if field in table.columns:
            found = row[field]
            same = (_same(float(found), float(expected), tolerance) if numeric and pd.notna(found)
                    else str(found).strip().lower() == str(expected).strip().lower())
            return ("recomputed", f"lookup:{field}") if same else ("contradicted", f"lookup:{field}")
        for column, value in row.items():
            if numeric and isinstance(value, (int, float)) and _same(float(value), float(expected), tolerance):
                return "recomputed", f"row:{column}"
            if not numeric and str(value).strip().lower() == str(expected).strip().lower():
                return "recomputed", f"row:{column}"
        if numeric and key == "order_id":
            for name, value in _order_stats(row).items():
                if _same(value, float(expected), tolerance):
                    return "recomputed", f"derived:{name}"

    named = t.workshops[t.workshops["name"].str.lower() == subject.strip().lower()]
    field = str(fact.get("field", "")).strip().lower().replace(" ", "_")
    if len(named) == 1 and field in t.workshops.columns:
        found = named.iloc[0][field]
        same = (_same(float(found), float(expected), tolerance) if numeric and pd.notna(found)
                else str(found).strip().lower() == str(expected).strip().lower())
        return ("recomputed", f"lookup:{field}") if same else ("contradicted", f"lookup:{field}")

    if not numeric:
        return "not_recomputed", "text"

    # A stage and a date or window: the production log and the published baseline.
    dates = ISO.findall(context)
    stages = [s for s in STAGES if _mentions(context, s)]
    for stage in stages:
        for span in ([dates[:2], dates[:1]] if dates else []):
            for name, value in _production_stats(t.log, stage, span).items():
                if _same(value, float(expected), tolerance):
                    return "recomputed", f"production:{name}"

    # Rows selected by the entities the evidence names.
    selected = t.orders
    used = []
    for column, values in t.vocab.items():
        named = [v for v in values if _mentions(context, v)]
        if named and len(named) < len(values):
            selected = selected[selected[column].isin(named)]
            used.append(column)
    candidates = {"filter": selected}
    if "status" not in used:
        candidates["filter+open"] = selected[selected["status"] == "IN_PROGRESS"]
        candidates["filter+done"] = selected[selected["status"] == "COMPLETE"]
    for label, frame in candidates.items():
        for name, value in _stats(frame).items():
            if _same(value, float(expected), tolerance):
                return "recomputed", f"{label}:{name}"
    for name, value in _stats(t.workshops).items():
        if _same(value, float(expected), tolerance) and _mentions(context, "workshop"):
            return "recomputed", f"workshops:{name}"
    return "not_recomputed", "no_computation_matched"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--package", type=Path, required=True)
    ap.add_argument("--output", type=Path)
    a = ap.parse_args()
    package = yaml.safe_load(a.package.read_text(encoding="utf-8"))
    tables = Tables(ROOT / "data")
    rows = []
    for item in package["items"]:
        for n, fact in enumerate(item["required_facts"]):
            verdict, method = verify_fact(fact, item, tables)
            rows.append({"item": item["id"], "category": item["category"], "fact": n, "verdict": verdict,
                         "method": method})
    summary = {"facts": len(rows), "verdicts": dict(Counter(r["verdict"] for r in rows)),
               "by_category": {c: dict(Counter(r["verdict"] for r in rows if r["category"] == c))
                               for c in sorted({r["category"] for r in rows})}}
    for r in rows:
        print(r["item"], r["category"], f"fact{r['fact']}", r["verdict"], r["method"])
    print(json.dumps(summary))
    if a.output:
        a.output.write_text(json.dumps({"summary": summary, "facts": rows}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
