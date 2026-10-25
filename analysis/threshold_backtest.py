"""Backtest of candidate "is this stage output normal?" rules (PLAN.md decision D6).

Answers three questions on data/production_log.csv:
  1. Is there a weekday effect between working days? (decides same-weekday vs trailing-window baseline)
  2. On the clean period (before the real ASSEMBLY drop on 2026-03-25), how often does each rule
     raise a false alert, and when does it catch the real drop?
  3. With synthetic 3-day drops injected into the clean period, what is each rule's recall?

Run from the repo root:
    uv run --with pandas --with scipy python analysis/threshold_backtest.py
Writes analysis/results/threshold_backtest.md.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "data" / "production_log.csv"
OUT = ROOT / "analysis" / "results" / "threshold_backtest.md"

DROP_START = pd.Timestamp("2026-03-25")  # first day of the real ASSEMBLY drop
WINDOW = 20  # trailing working days in the baseline
N_INJECT = 400  # synthetic trials per (rule, magnitude)
SEED = 0
ALERTS_PER_WEEK_FACTOR = 4 * 6  # 4 stages x 6 working days


def load() -> pd.DataFrame:
    log = pd.read_csv(LOG, parse_dates=["date"])
    log = log[log.date.dt.dayofweek != 6]  # factory closed on Sundays
    return log.pivot(index="date", columns="stage", values="pieces_completed").astype(float)


def robust_z(s: pd.Series, i: int) -> float:
    hist = s.iloc[i - WINDOW : i].to_numpy()
    med = np.median(hist)
    sigma = 1.4826 * np.median(np.abs(hist - med))
    return (s.iloc[i] - med) / sigma


def same_weekday_median(s: pd.Series, i: int) -> float:
    day = s.index[i]
    prior = s.iloc[:i]
    prior = prior[prior.index.dayofweek == day.dayofweek].tail(4)
    return prior.median() if len(prior) == 4 else np.nan


# Each rule: (series, index) -> bool "alert on this day" (drops only, one-sided).
RULES = {
    "same-weekday median, -15%": lambda s, i: s.iloc[i] < 0.85 * same_weekday_median(s, i),
    "same-weekday median, -20%": lambda s, i: s.iloc[i] < 0.80 * same_weekday_median(s, i),
    "trailing median, -15%": lambda s, i: s.iloc[i] < 0.85 * s.iloc[i - WINDOW : i].median(),
    "modified z < -3.5 (Iglewicz-Hoaglin)": lambda s, i: robust_z(s, i) < -3.5,
    "Shewhart mean/sd 3 sigma": lambda s, i: (s.iloc[i] - s.iloc[i - WINDOW : i].mean())
    / s.iloc[i - WINDOW : i].std()
    < -3,
    "robust z < -1.5": lambda s, i: robust_z(s, i) < -1.5,
    "robust z < -1.75 (briefing tier)": lambda s, i: robust_z(s, i) < -1.75,
    "robust z < -2": lambda s, i: robust_z(s, i) < -2,
    "robust z < -3": lambda s, i: robust_z(s, i) < -3,
    "2 of 3 days robust z < -2 (Western Electric)": lambda s, i: sum(
        robust_z(s, j) < -2 for j in (i - 2, i - 1, i)
    )
    >= 2,
    "interrupt tier: z < -3 OR 2-of-3 z < -2": lambda s, i: robust_z(s, i) < -3
    or sum(robust_z(s, j) < -2 for j in (i - 2, i - 1, i)) >= 2,
}


def weekday_effect(pv: pd.DataFrame) -> pd.DataFrame:
    clean = pv[pv.index < DROP_START]
    rows = []
    for stage in clean.columns:
        s = clean[stage]
        groups = [g.to_numpy() for _, g in s.groupby(s.index.dayofweek)]
        rows.append(
            {
                "stage": stage,
                "Kruskal-Wallis p": round(stats.kruskal(*groups).pvalue, 3),
                "mean": round(s.mean()),
                "sd": round(s.std()),
                "CV": round(s.std() / s.mean(), 3),
            }
        )
    return pd.DataFrame(rows)


def false_alerts_and_real_drop(pv: pd.DataFrame) -> pd.DataFrame:
    clean = pv[pv.index < DROP_START]
    start = WINDOW + 2  # room for the trailing window and the 2-of-3 look-back
    rows = []
    for name, rule in RULES.items():
        flags = [rule(clean[st], i) for st in clean.columns for i in range(start, len(clean))]
        fa_rate = float(np.nanmean(flags))
        assembly = pv["ASSEMBLY"]
        first = next(
            (
                assembly.index[i].date().isoformat()
                for i in range(assembly.index.get_loc(DROP_START), len(assembly))
                if rule(assembly, i)
            ),
            "missed",
        )
        rows.append(
            {
                "rule": name,
                "false alerts / week": round(fa_rate * ALERTS_PER_WEEK_FACTOR, 2),
                "real drop first flagged": first,
            }
        )
    return pd.DataFrame(rows)


def injection_recall(pv: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    clean = pv[pv.index < DROP_START]
    rows = []
    for name, rule in RULES.items():
        row = {"rule": name}
        for mag in (0.10, 0.15, 0.20, 0.30):
            hits = []
            for _ in range(N_INJECT):
                s = clean[rng.choice(clean.columns)].copy()
                i = int(rng.integers(WINDOW + 2, len(s) - 3))
                s.iloc[i : i + 3] *= 1 - mag
                hits.append(any(rule(s, i + k) for k in range(3)))
            row[f"recall -{int(mag * 100)}% (within 3 days)"] = f"{np.mean(hits):.0%}"
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to a legacy code page
    pv = load()
    sections = [
        "# Threshold backtest\n",
        f"Baseline window: {WINDOW} trailing working days; robust sigma = 1.4826 x MAD; "
        f"clean period = before {DROP_START.date()}; {N_INJECT} injections per cell, seed {SEED}.\n",
        "## 1. Weekday effect (clean period)\n",
        weekday_effect(pv).to_markdown(index=False),
        "\n## 2. False alerts on clean data, and the real ASSEMBLY drop\n",
        false_alerts_and_real_drop(pv).to_markdown(index=False),
        "\n## 3. Recall on injected 3-day drops\n",
        injection_recall(pv).to_markdown(index=False),
        "",
    ]
    OUT.write_text("\n".join(sections), encoding="utf-8")
    print("\n".join(sections))


if __name__ == "__main__":
    main()
