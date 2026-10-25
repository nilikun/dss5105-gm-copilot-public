"""Fig. 3 — what the data already shows. a, ASSEMBLY output against its rolling normal band. b, late delivery
rate by customer (completed orders).

Run from the repo root:
    uv run --no-project --with matplotlib --with pandas python docs/figures/fig3_signals.py
"""

import sys
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from style import BLUE, GREY, INK, MUTED, TEXT, TINT, VERMILLION, apply_matplotlib_style, panel_label  # noqa: E402

ROOT = HERE.parents[1]
apply_matplotlib_style()

log = pd.read_csv(ROOT / "data" / "production_log.csv", parse_dates=["date"])
s = log[(log.stage == "ASSEMBLY") & (log.date.dt.dayofweek != 6)].set_index("date").pieces_completed.astype(float)
hist = s.shift(1).rolling(20)
med = hist.median()
sigma = 1.4826 * s.shift(1).rolling(20).apply(lambda v: np.median(np.abs(v - np.median(v))), raw=True)
win = s.index >= "2026-02-16"
before = s[s.index < "2026-03-25"].tail(20).median()
after = s[s.index >= "2026-03-25"].mean()
drop_pct = round(100 * (after / before - 1))

orders = pd.read_csv(ROOT / "data" / "orders.csv")
done = orders[orders.status == "COMPLETE"]
g = done.groupby("customer").days_late.agg(n="count", late=lambda x: int((x > 0).sum()))
g["rate"] = 100 * g.late / g.n
g = g.sort_values("rate")
overall = 100 * (done.days_late > 0).mean()

fig, (a, b) = plt.subplots(1, 2, figsize=(7.4, 3.5), gridspec_kw={"width_ratios": [1.55, 1], "wspace": 0.55})

# a — time series with the briefing-tier band
x = s.index[win]
a.fill_between(x, (med - 1.75 * sigma)[win], (med + 1.75 * sigma)[win], color=TINT[BLUE], lw=0,
               label="normal band (|z| ≤ 1.75)")
a.plot(x, med[win], color=BLUE, lw=1.2, ls=(0, (4, 2)), label="median, prior 20 working days")
a.plot(x, s[win], color=VERMILLION, lw=1.4, marker="o", ms=2.6, label="ASSEMBLY output")
a.annotate(f"−{abs(drop_pct)}% from 25 Mar\nflagged on day 1", xy=(pd.Timestamp("2026-03-25"), s["2026-03-25"]),
           xytext=(pd.Timestamp("2026-03-04"), 520), fontsize=9, color=INK,
           arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.8, shrinkB=3))
a.set_ylim(300, 1000)
a.set_ylabel("Pieces per working day")
a.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO, interval=2))
a.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
a.legend(loc="lower left", ncol=1, handlelength=1.8, borderaxespad=0.2, fontsize=8.5)
panel_label(a, "a", x=-0.2)

# b — late rate by customer
colors = [VERMILLION if c == "TrendCart" else GREY for c in g.index]
b.barh(g.index, g.rate, color=colors, height=0.62)
for i, (c, r) in enumerate(g.iterrows()):
    b.text(r.rate + 2, i, f"{int(r.late)}/{int(r.n)}", va="center", fontsize=8.5, color=TEXT)
b.axvline(overall, color=MUTED, lw=0.8, ls=(0, (3, 2)))
b.text(overall + 1.5, len(g) - 0.45, f"all {overall:.0f}%", fontsize=8.5, color=MUTED, va="bottom")
b.set_xlim(0, 100)
b.set_xlabel("Completed orders delivered late (%)")
b.tick_params(axis="y", length=0)
b.spines["left"].set_visible(False)
panel_label(b, "b", x=-0.62)

for ext in ("png", "svg"):
    fig.savefig(HERE / f"fig3_signals.{ext}")
print("wrote fig3_signals; drop", drop_pct, "% | overall late", round(overall))
