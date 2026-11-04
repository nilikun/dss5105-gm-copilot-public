"""Fig. 6: the frozen held-out run, Step 1 baseline against the frozen system.
a, passes out of 60 attempts under the strict score and after the judge saw source rows (post hoc);
b, the second score by category. Numbers are read from eval/results/heldout-v1 at build time.

Run from the repo root:
    uv run --no-project --with matplotlib --with pyyaml python docs/figures/fig6_heldout.py
"""

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from style import BLUE, GRID, INK, MUTED, TEXT, VERMILLION, apply_matplotlib_style, panel_label  # noqa: E402

apply_matplotlib_style()
RUN = ROOT / "eval/results/heldout-v1"
rows = [json.loads(x) for x in (RUN / "rescored.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
items = yaml.safe_load((RUN / "heldout.yaml").read_text(encoding="utf-8"))["items"]
category = {i["id"]: i["category"] for i in items}
ORDER = ["lookup", "aggregation", "judgement", "tracing", "discovery", "feasibility", "action", "ambiguous",
         "unanswerable"]
VERSIONS = [("baseline", "Step 1 baseline", BLUE), ("improved", "Frozen system", VERMILLION)]


def passes(version, key, cat=None):
    return sum(r[key] for r in rows if r["version"] == version and (cat is None or category[r["id"]] == cat))


fig, (a, b) = plt.subplots(1, 2, figsize=(11.6, 3.7), gridspec_kw={"width_ratios": [0.8, 1.5], "wspace": 0.3})

width = 0.34
for k, (version, label, color) in enumerate(VERSIONS):
    xs = [i + (k - 0.5) * (width + 0.03) for i in range(2)]
    values = [passes(version, "strict_pass"), passes(version, "reviewed_pass")]
    a.bar(xs, values, width=width, color=color, label=label)
    for x, v in zip(xs, values, strict=True):
        a.text(x, v + 1, str(v), ha="center", va="bottom", fontsize=9.5, color=INK, fontweight="bold")
a.set_xticks([0, 1], ["Strict score\n(fixed before the run)", "Judge given source rows\n(post hoc)"])
a.set_ylim(0, 60)
a.set_ylabel("Passes out of 60 attempts")
a.set_title("Overall", loc="left", color=INK)
a.yaxis.grid(True, color=GRID, lw=0.6)
a.set_axisbelow(True)
a.legend(frameon=False, loc="upper left", fontsize=9)
panel_label(a, "a")

height = 0.36
ys = list(range(len(ORDER)))[::-1]
for k, (version, _label, color) in enumerate(VERSIONS):
    for y, cat in zip(ys, ORDER, strict=True):
        n = sum(1 for r in rows if r["version"] == version and category[r["id"]] == cat)
        v = passes(version, "reviewed_pass", cat)
        pos = y + (0.5 - k) * (height + 0.02)
        b.barh(pos, 100 * v / n, height=height, color=color)
        b.text(100 * v / n + 1.2, pos, f"{v}/{n}", va="center", fontsize=8.2, color=TEXT)
b.set_yticks(ys, ORDER)
b.set_xlim(0, 112)
b.set_xticks([0, 25, 50, 75, 100], ["0", "25", "50", "75", "100%"])
b.set_xlabel("Attempts passing, judge given source rows", color=MUTED)
b.set_title("By category", loc="left", color=INK)
b.xaxis.grid(True, color=GRID, lw=0.6)
b.set_axisbelow(True)
panel_label(b, "b")

for ext in ("png", "svg"):
    fig.savefig(HERE / f"fig6_heldout.{ext}", dpi=220, bbox_inches="tight", facecolor="white")
print("wrote fig6_heldout")
