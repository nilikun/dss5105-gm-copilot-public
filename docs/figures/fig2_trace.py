"""Fig. 2 — one turn of the agent, step by step (in the style of the ReAct trajectory figures).

The tool calls and observations are produced by running the implemented tools at build time, so the figure
cannot drift from the code. The thought, the rejected draft and the final reply are illustrative until the
agent loop exists; the figure says so.

Run from the repo root:
    uv run --project backend --with playwright --with pillow python docs/figures/fig2_trace.py
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "backend"))

from app.clock import SimClock  # noqa: E402
from app.config import DATASET_TODAY  # noqa: E402
from app.db.database import connect  # noqa: E402
from app.tools import TOOLS  # noqa: E402
from app.tools.base import ToolContext  # noqa: E402
from style import BLUE, FAINT, GREEN, GREY, GRID, INK, MUTED, TEXT, TINT, VERMILLION  # noqa: E402
from svgkit import Canvas  # noqa: E402

OUT = HERE / "fig2_trace"

# ----------------------------------------------------------------- real tool calls
ctx = ToolContext(db=connect(), clock=SimClock.at(DATASET_TODAY))
r1 = TOOLS["resolve_time"](ctx, "yesterday")
day = r1.data["start"]
r2 = TOOLS["compare_to_normal"](ctx, stage="ASSEMBLY", on_date=day)
o = r2.data["results"][0]


def js(d: dict) -> str:
    return json.dumps(d, ensure_ascii=False).replace('", "', '", "')


obs1 = [js({"start": r1.data["start"], "working_days": r1.data["working_days"]})]
obs2 = [
    '{"actual": %s, "baseline_median": %s,' % (o["actual"], o["baseline_median"]),
    ' "z": %s, "pct_vs_baseline": %s,' % (o["z"], o["pct_vs_baseline"]),
    ' "tier": "%s", "consecutive_low_days": %s,' % (o["tier"], o["consecutive_low_days"]),
    ' "window": ["%s", "%s"], "evidence_id": "%s"}' % (o["window"][0], o["window"][1], o["evidence_id"]),
]
reply = (f"Not normal: {o['actual']} pieces on 31 Mar, {abs(o['pct_vs_baseline'])}% below the usual "
         f"{o['baseline_median']} — the {o['consecutive_low_days']}th low day in a row (interrupt tier). "
         f"[{o['evidence_id']}]")
reply_tokens = [str(o["actual"]), day, str(abs(o["pct_vs_baseline"])), str(o["baseline_median"]),
                str(o["consecutive_low_days"])]
observed = json.dumps([r1.data, o])
assert all(tok in observed for tok in reply_tokens), "illustrative reply must only use observed values"

# ----------------------------------------------------------------- figure
W = 780
c = Canvas(W, 720)
TAG_X, TAG_W, BODY_X = 12, 84, 110
ROOM = W - BODY_X - 12
SANS, MONO = 15, 14
rows = [
    ("Question", GREEN, [("sans", "Was assembly's output yesterday normal?", {"bold": True})]),
    ("Thought", VERMILLION, [("sans", "“Yesterday” is relative: resolve it before querying.", {"italic": True})]),
    ("Act 1", BLUE, [("mono", 'resolve_time(expression="yesterday")', {})]),
    ("Obs 1", GREY, [("mono", s, {}) for s in obs1]),
    ("Act 2", BLUE, [("mono", 'compare_to_normal(stage="ASSEMBLY",', {}),
                     ("mono", f'                  on_date="{day}")', {})]),
    ("Obs 2", GREY, [("mono", s, {}) for s in obs2]),
    ("Draft", VERMILLION, [("sans", "“Assembly made about 300 fewer pieces than normal.”", {"italic": True})]),
    ("Verifier", INK, [("rich", [("✗  ", {"color": VERMILLION, "bold": True}),
                                 ("“300” appears in no tool output → rejected, repair", {})], {})]),
    ("Reply", VERMILLION, [("sans", line, {}) for line in (
        reply[:reply.index(" — ") + 2], reply[reply.index(" — ") + 3:])]),
    ("Verifier", INK, [("rich", [("✓  ", {"color": GREEN, "bold": True}),
                                 (" · ".join(reply_tokens[:3]) + " · " + " · ".join(reply_tokens[3:]), {"mono": True}),
                                 ("  all in tool outputs → send", {})], {})]),
]

y = 14
for i, (tag, color, lines) in enumerate(rows):
    lh = 21 if lines[0][0] == "mono" else 22
    h = 14 + lh * len(lines)
    c.rect(TAG_X, y + 4, TAG_W, 26, fill=TINT.get(color, "#F0F0F0"), stroke=color, sw=1.2, rx=3)
    c.text(TAG_X + TAG_W / 2, y + 22, tag, size=13.5, color=INK, bold=True, anchor="middle")
    for j, (kind, s, opts) in enumerate(lines):
        ty = y + 22 + j * lh
        if kind == "rich":
            c.rich(BODY_X, ty, s, size=SANS)
            if c.rich_width(s, SANS) > ROOM:
                c.overflows.append(f"rich line in {tag}")
        else:
            c.text(BODY_X, ty, s, size=MONO if kind == "mono" else SANS, mono=kind == "mono",
                   color=TEXT, bold=opts.get("bold", False), italic=opts.get("italic", False),
                   room=ROOM, where=tag)
    y += h + 8
    if i in (0, 5, 7):
        c.line(TAG_X, y - 4, W - 12, y - 4, color=GRID, sw=1.2)
        y += 4

# provenance (real tool calls vs illustrative text) is stated in the figure caption
c.h = int(y + 4)
c.save(OUT)
print("reply tokens all observed:", reply_tokens, "| faint", FAINT)
