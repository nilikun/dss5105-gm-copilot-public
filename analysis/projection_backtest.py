"""Walk-forward backtest of order-completion projection models (TOOL_SPEC §7.2, PLAN D11).

For every completed order, predict its cycle time (order_date -> completed_date) using only orders that
had *completed before that order was placed* (no look-ahead). Compare candidate models on accuracy,
interval calibration and stability.

Models
  A  plan:        cycle = promised lead time (due_date - order_date)
  B  global:      median / P80 cycle of all prior completed orders
  C  size band:   median / P80 cycle of prior completed orders in the same size band
  D  size + load: C scaled by the load index at order date (open pieces / trailing typical open pieces)
  E  log-linear:  log(cycle) ~ log(pieces) fitted on prior orders; P80 from residual quantile

Run from the repo root:
    uv run --no-project --with pandas --with scipy --with tabulate python analysis/projection_backtest.py
Writes analysis/results/projection_backtest.md.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ORDERS = ROOT / "data" / "orders.csv"
OUT = ROOT / "analysis" / "results" / "projection_backtest.md"

MIN_HISTORY = 15  # need this many prior completions before predicting
SIZE_BANDS = [0, 300, 800, 1200, 10_000]  # (0,300], (300,800], (800,1200], (1200, …)
MIN_BAND = 5  # fall back to global if a band has fewer prior orders
LOAD_WINDOW_DAYS = 28
N_BOOT = 1000
SEED = 0


def load() -> pd.DataFrame:
    o = pd.read_csv(ORDERS, parse_dates=["order_date", "due_date", "completed_date"])
    o["cycle"] = (o.completed_date - o.order_date).dt.days
    o["lead"] = (o.due_date - o.order_date).dt.days
    o["band"] = pd.cut(o.pieces, SIZE_BANDS)
    return o


def open_pieces(o: pd.DataFrame, t: pd.Timestamp) -> int:
    is_open = (o.order_date <= t) & (o.completed_date.isna() | (o.completed_date > t))
    return int(o.loc[is_open, "pieces"].sum())


def predict(o: pd.DataFrame, row: pd.Series) -> dict | None:
    t = row.order_date
    hist = o[o.completed_date < t]
    if len(hist) < MIN_HISTORY:
        return None
    band_hist = hist[hist.band == row.band]
    band = band_hist if len(band_hist) >= MIN_BAND else hist

    # load index: open pieces now vs the median of open pieces over the trailing window
    window = pd.date_range(t - pd.Timedelta(days=LOAD_WINDOW_DAYS), t - pd.Timedelta(days=1))
    typical = np.median([open_pieces(o, d) for d in window])
    load = open_pieces(o, t) / typical if typical else 1.0

    x, y = np.log(hist.pieces), np.log(hist.cycle)
    slope, intercept = np.polyfit(x, y, 1)
    resid = y - (intercept + slope * x)
    log_fit = intercept + slope * np.log(row.pieces)

    return {
        "A_p50": row.lead, "A_p80": row.lead,
        "B_p50": hist.cycle.median(), "B_p80": hist.cycle.quantile(0.8),
        "C_p50": band.cycle.median(), "C_p80": band.cycle.quantile(0.8),
        "D_p50": band.cycle.median() * load, "D_p80": band.cycle.quantile(0.8) * load,
        "E_p50": np.exp(log_fit + np.median(resid)), "E_p80": np.exp(log_fit + np.quantile(resid, 0.8)),
        "load": load,
    }


def evaluate(o: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    done = o[o.status == "COMPLETE"].sort_values("order_date")
    rows = []
    for _, r in done.iterrows():
        p = predict(o, r)
        if p is not None:
            rows.append({"order_id": r.order_id, "pieces": r.pieces, "actual": r.cycle,
                         "late": r.cycle > r.lead, "lead": r.lead, **p})
    preds = pd.DataFrame(rows)

    rng = np.random.default_rng(SEED)
    names = {"A": "A plan (due date)", "B": "B global median", "C": "C size band",
             "D": "C + load scaling", "E": "E log-linear size"}
    summary = []
    for k, name in names.items():
        err = preds[f"{k}_p50"] - preds.actual
        covered = preds.actual <= preds[f"{k}_p80"]
        flagged = preds[f"{k}_p80"] > preds.lead  # would mark as at risk at order time
        boot = [np.abs(err.sample(frac=1, replace=True, random_state=int(s))).mean()
                for s in rng.integers(0, 1_000_000, N_BOOT)]
        halves = np.array_split(np.abs(err).to_numpy(), 2)
        summary.append({
            "model": name,
            "MAE (days)": round(np.abs(err).mean(), 2),
            "MAE 95% CI": f"{np.percentile(boot, 2.5):.1f}–{np.percentile(boot, 97.5):.1f}",
            "bias (days)": round(err.mean(), 2),
            "P80 coverage": f"{covered.mean():.0%}",
            "MAE 1st half / 2nd half": f"{halves[0].mean():.1f} / {halves[1].mean():.1f}",
            "late-order recall": f"{(flagged & preds.late).sum() / max(preds.late.sum(), 1):.0%}",
            "late-order precision": f"{(flagged & preds.late).sum() / max(flagged.sum(), 1):.0%}",
        })
    return preds, pd.DataFrame(summary)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to a legacy code page
    o = load()
    preds, summary = evaluate(o)
    corr = o[o.status == "COMPLETE"][["cycle", "pieces"]].corr().iloc[0, 1]
    text = "\n".join([
        "# Completion projection backtest\n",
        f"Walk-forward over {len(preds)} completed orders (each predicted from orders completed before it was "
        f"placed; first {MIN_HISTORY} skipped for history). Late orders in sample: {int(preds.late.sum())}. "
        f"Cycle–pieces correlation (all completed): {corr:.2f}. Bootstrap n={N_BOOT}, seed {SEED}.\n",
        summary.to_markdown(index=False),
        "\nMAE = mean |P50 − actual cycle|. P80 coverage should be ≈ 80%. "
        "Late-order recall/precision: P80 projection exceeds the promised lead time, vs actually late.\n",
    ])
    OUT.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
