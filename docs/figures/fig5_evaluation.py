"""Fig. 5 — evaluation on the dev set (36 items) and the critic ablation.
a, decision accuracy per run (dots) and mean (bar): base system and + LLM critic on the same code, and the final
   system (prompt v9, three runs); b, latency p50 and p90; c, model cost per question.

Numbers are read from eval/results/*/summary.json at build time, so the figure and the results cannot disagree.

Run from the repo root:
    uv run --no-project --with matplotlib python docs/figures/fig5_evaluation.py
"""

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from style import BLUE, GREY, INK, MUTED, TEXT, VERMILLION, apply_matplotlib_style, panel_label  # noqa: E402

apply_matplotlib_style()
RESULTS = ROOT / "eval" / "results"

# ----------------------------------------------------------------- data
GROUPS = [  # label, run-directory suffixes, colour
    ("Base\n(prompt v4)", ["dev-gpt-5.6-luna-base-r1", "dev-gpt-5.6-luna-base-r2"], GREY),
    ("+ LLM critic\n(prompt v4)", ["dev-gpt-5.6-luna-critic-r1", "dev-gpt-5.6-luna-critic-r2"], VERMILLION),
    ("Final\n(prompt v9)", ["dev-gpt-5.6-luna-base-v9a", "dev-gpt-5.6-luna-base-v9b", "dev-gpt-5.6-luna-base-v9c"],
     BLUE),
]


def runs(suffix: str) -> dict:
    [d] = [p for p in RESULTS.iterdir() if p.name.endswith(suffix)]
    return json.loads((d / "summary.json").read_text(encoding="utf-8"))


data = [(lab, [runs(s) for s in sufs], col) for lab, sufs, col in GROUPS]
mean = lambda xs: sum(xs) / len(xs)  # noqa: E731

# ----------------------------------------------------------------- figure
fig, (a, b, c) = plt.subplots(1, 3, figsize=(11.6, 3.3), gridspec_kw={"width_ratios": [1.25, 1, 0.8],
                                                                       "wspace": 0.45})
x = range(len(data))

for i, (_lab, rs, col) in enumerate(data):
    acc = [100 * r["decision_accuracy"] for r in rs]
    a.bar(i, mean(acc), width=0.56, color=col, alpha=0.25, edgecolor="none")
    xs = [i + 0.16 * (k - (len(acc) - 1) / 2) for k in range(len(acc))]
    a.scatter(xs, acc, s=34, color=col, zorder=3, edgecolor="white", linewidth=0.8)
    a.text(i, max(acc) + 1.8, f"{mean(acc):.1f}%", ha="center", va="bottom", fontsize=9.5, color=INK,
           fontweight="bold")
a.axhline(80, color=MUTED, lw=0.8, ls=(0, (3, 3)))
a.text(len(data) - 0.5, 80.8, "target ≥ 80%", ha="right", va="bottom", fontsize=8.5, color=MUTED)
a.set_xticks(list(x), [d[0] for d in data])
a.set_ylim(60, 105)
a.set_ylabel("Decision accuracy, dev set (%)")
a.set_title("Decision accuracy (● run, bar = mean)", loc="left", color=INK)
panel_label(a, "a")

for i, (_lab, rs, col) in enumerate(data):
    p50, p90 = mean([r["latency_p50_s"] for r in rs]), mean([r["latency_p90_s"] for r in rs])
    b.plot([i, i], [p50, p90], color=col, lw=2, solid_capstyle="round")
    b.scatter([i], [p50], s=44, color=col, zorder=3, edgecolor="white", linewidth=0.8)
    b.scatter([i], [p90], s=44, facecolor="white", edgecolor=col, linewidth=1.6, zorder=3)
    b.text(i + 0.12, p50, f"{p50:.1f}", va="center", fontsize=8.5, color=TEXT)
    b.text(i + 0.12, p90, f"{p90:.1f}", va="center", fontsize=8.5, color=TEXT)
b.axhline(10, color=MUTED, lw=0.8, ls=(0, (3, 3)))
b.set_xticks(list(x), [d[0].split("\n")[0] for d in data])
b.set_xlim(-0.5, len(data) - 0.3)
b.set_ylim(0, 22)
b.set_yticks(range(0, 21, 5))
b.set_ylabel("Seconds per question")
b.set_title("Latency: p50 (●) and p90 (○)", loc="left", color=INK)
panel_label(b, "b")

for i, (_lab, rs, col) in enumerate(data):
    cost = 1000 * mean([r["cost_per_item_usd"] for r in rs])
    c.bar(i, cost, width=0.56, color=col, edgecolor="none")
    c.text(i, cost + 0.03, f"{cost:.2f}", ha="center", va="bottom", fontsize=8.5, color=TEXT)
c.set_xticks(list(x), [d[0].split("\n")[0] for d in data])
c.set_ylim(0, 1.6)
c.set_yticks([0, 0.5, 1.0, 1.5])
c.set_ylabel("US$ per 1,000 questions")
c.set_title("Model cost", loc="left", color=INK)
panel_label(c, "c")

for ax in (a, b, c):
    ax.tick_params(axis="x", length=0)
for ext in ("png", "svg"):
    fig.savefig(HERE / f"fig5_evaluation.{ext}")
print("wrote", HERE / "fig5_evaluation.png")
