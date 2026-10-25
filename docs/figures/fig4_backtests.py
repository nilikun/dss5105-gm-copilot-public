"""Fig. 4 — design choices settled by backtests.
a, false alerts versus recall for candidate "abnormal output" rules (threshold backtest).
b, completion-forecast error with 95% bootstrap CIs (walk-forward backtest).

Numbers are recomputed from analysis/*.py at build time, so the figure and the tables cannot disagree.

Run from the repo root:
    uv run --no-project --with matplotlib --with pandas --with scipy --with tabulate python docs/figures/fig4_backtests.py
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis"))
import projection_backtest as pb  # noqa: E402
import threshold_backtest as tb  # noqa: E402
from style import BLUE, GREY, INK, MUTED, TEXT, TINT, VERMILLION, apply_matplotlib_style, panel_label  # noqa: E402

apply_matplotlib_style()

# ----------------------------------------------------------------- data
pv = tb.load()
fa = tb.false_alerts_and_real_drop(pv).set_index("rule")["false alerts / week"]
rec = tb.injection_recall(pv).set_index("rule")["recall -20% (within 3 days)"].str.rstrip("%").astype(float)
rules = fa.to_frame("fa").join(rec.rename("recall"))

_, summary = pb.evaluate(pb.load())
summary = summary.set_index("model")
lo_hi = summary["MAE 95% CI"].str.split("–", expand=True).astype(float)

# ----------------------------------------------------------------- figure
fig, (a, b) = plt.subplots(1, 2, figsize=(11.6, 3.4), gridspec_kw={"width_ratios": [1.1, 1], "wspace": 0.42})

# a — trade-off
a.axvspan(-0.05, 0.5, color=TINT[BLUE], lw=0)
a.text(0.03, 103, "alert budget\n≤ 0.5 / week", fontsize=8.5, color=BLUE, va="top")
labels = {
    "robust z < -1.75 (briefing tier)": ("briefing tier  z < −1.75", VERMILLION, (8, -12)),
    "interrupt tier: z < -3 OR 2-of-3 z < -2": ("interrupt tier", BLUE, (8, -4)),
    "modified z < -3.5 (Iglewicz-Hoaglin)": ("textbook modified z < −3.5", GREY, (8, -3)),
    "same-weekday median, -15%": ("fixed −15% vs same weekday", GREY, (-8, 4)),
    "robust z < -2": ("z < −2", GREY, (8, -10)),
}
for rule, r in rules.iterrows():
    name, color, off = labels.get(rule, (None, GREY, (0, 0)))
    size = 46 if color != GREY else 22
    a.scatter(r.fa, r.recall, s=size, color=color if name else "#BDBDBD", zorder=3, lw=0)
    if name:
        a.annotate(name, (r.fa, r.recall), xytext=off, textcoords="offset points", fontsize=8.5,
                   color=INK if color == GREY else color, ha="right" if off[0] < 0 else "left",
                   fontweight="bold" if color != GREY else "normal")
a.set_xlim(-0.05, 1.75)
a.set_ylim(0, 105)
a.set_xlabel("False alerts per week on clean data (4 stages)")
a.set_ylabel("Recall of a 20% drop within 3 days (%)")
panel_label(a, "a", x=-0.13)

# b — forest plot of forecast error
order = ["A plan (due date)", "B global median", "C size band", "C + load scaling", "E log-linear size"]
names = ["Promised due date", "Global median", "Size band", "Size band + load", "Log-linear size (chosen)"]
for i, (m, n) in enumerate(zip(order, names)):
    y = len(order) - 1 - i
    chosen = m.startswith("E")
    color = VERMILLION if chosen else GREY
    mae = summary.loc[m, "MAE (days)"]
    a_lo, a_hi = lo_hi.loc[m, 0], lo_hi.loc[m, 1]
    b.plot([a_lo, a_hi], [y, y], color=color, lw=1.6, solid_capstyle="butt")
    b.scatter(mae, y, s=40 if chosen else 28, color=color, zorder=3, lw=0)
    plan_mae = summary.loc["A plan (due date)", "MAE (days)"]
    label_x = a_hi + 0.15 if a_hi + 0.15 > plan_mae + 0.1 or a_hi < plan_mae - 1.5 else plan_mae + 0.2
    b.text(label_x, y, f"{mae:.1f}  [{a_lo:.1f}, {a_hi:.1f}]", va="center", fontsize=8.5,
           color=INK if chosen else TEXT, fontweight="bold" if chosen else "normal")
b.axvline(summary.loc["A plan (due date)", "MAE (days)"], color=MUTED, lw=0.8, ls=(0, (3, 2)))
b.set_yticks(range(len(order)), names[::-1])
b.tick_params(axis="y", length=0)
b.spines["left"].set_visible(False)
b.set_xlim(2, 11.5)
b.set_xlabel(f"Mean absolute error, days (95% bootstrap CI; n = {pb.evaluate(pb.load())[0].shape[0]} orders)")
panel_label(b, "b", x=-0.36)

for ext in ("png", "svg"):
    fig.savefig(HERE / f"fig4_backtests.{ext}")
print("wrote fig4_backtests")
print(rules.round(2).to_string())
