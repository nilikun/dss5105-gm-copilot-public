"""Fig. 1 — system architecture, drawn as a method figure in the style of agent-system papers.

Four layers separated by hairlines (interface, orchestration, tools, data); modules are thin-ruled frames;
components carry their role in colour (vermillion = LLM step, blue = deterministic code, green = human
checkpoint, grey = data). Numbered markers trace one question end to end.

Run from the repo root:
    uv run --no-project --with playwright --with pillow python docs/figures/fig1_architecture.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from style import BLUE, FAINT, GREEN, GREY, GRID, INK, MUTED, RULE, TINT, VERMILLION  # noqa: E402
from svgkit import Canvas  # noqa: E402

OUT = Path(__file__).resolve().parent / "fig1_architecture"
c = Canvas(1500, 610)
TITLE, SUB = 17, 14


def layer(y, name, sep=True):
    if sep:
        c.line(20, y, 1480, y, color=GRID, sw=1.2, dash="5 4")
    c.text(24, y + 26, name, size=13.5, color=MUTED, bold=True, room=110, where=name)


def module(x, y, w, h, title, title_x=None):
    c.rect(x, y, w, h, fill="#FFFFFF", stroke=RULE, sw=1.1, rx=4)
    c.text(title_x or x + 14, y + 23, title, size=15, color=INK, bold=True, room=w - 28, where=title)


def comp(x, y, w, h, title, sub=None, color=BLUE, dash=None):
    c.rect(x, y, w, h, fill=TINT[color], stroke=color, sw=1.3, rx=3, dash=dash)
    cx = x + w / 2
    if sub:
        c.text(cx, y + h / 2 - 3, title, size=TITLE, color=INK, bold=True, anchor="middle", room=w - 16, where=title)
        c.text(cx, y + h / 2 + 16, sub, size=SUB, color=MUTED, anchor="middle", room=w - 16, where=title)
    else:
        c.text(cx, y + h / 2 + 6, title, size=TITLE, color=INK, bold=True, anchor="middle", room=w - 16, where=title)


def ui(x, y, w, label):
    c.rect(x, y, w, 34, fill="#FFFFFF", stroke=GREEN, sw=1.3, rx=17)
    c.text(x + w / 2, y + 22, label, size=15, color=INK, anchor="middle", room=w - 20, where=label)


def pill(x, y, label):
    w = c.width(label, 13.5, mono=True) + 20
    c.rect(x, y, w, 26, fill="#FFFFFF", stroke=GREY, sw=1.0, rx=13)
    c.text(x + 10, y + 17.5, label, size=13.5, color=INK, mono=True)
    return w


# ----------------------------------------------------------------- layers
layer(12, "Interface", sep=False)
layer(96, "Orchestration")
layer(346, "Tools")
layer(458, "Data")

# interface: the manager's surfaces
c.circle(172, 45, 15, fill="#FFFFFF", stroke=GREEN, sw=1.3)
c.circle(172, 40.5, 4.5, fill=GREEN)
c.raw(f'<path d="M 164 54 Q 172 42 180 54 Z" fill="{GREEN}"/>')
ui(198, 28, 180, "Ask (chat · voice)")
ui(570, 28, 210, "Answer + evidence rows")
ui(890, 28, 200, "Briefing · alerts")
ui(1250, 28, 210, "Confirm · cancel · undo")

# orchestration
module(150, 110, 640, 222, "Interactive agent (one turn)", title_x=244)
comp(168, 182, 150, 68, "Context", "history · focus · now")
comp(358, 182, 222, 68, "ReAct LLM", "reason → act → observe", color=VERMILLION)
comp(616, 182, 160, 68, "Verifier", "numbers ⊂ tool output")
c.arrow([(318, 216), (356, 216)])
c.arrow([(580, 216), (614, 216)])
c.arrow([(660, 180), (660, 162), (520, 162), (520, 180)], color=VERMILLION, dash="5 3")
c.rect(552, 150, 76, 16, fill="#FFFFFF")
c.text(590, 162, "repair ×1", size=13, color=VERMILLION, anchor="middle")
c.text(696, 278, "fails twice →", size=13, color=FAINT, anchor="middle")
c.text(696, 294, "show tool output", size=13, color=FAINT, anchor="middle")

module(812, 110, 300, 222, "Scheduled workflows")
comp(830, 146, 264, 68, "Morning briefing", "07:00 · detect → rank → narrate")
comp(830, 230, 264, 68, "Watch engine", "each tick · P1 / P2 / P3 policy")

module(1134, 110, 346, 222, "Action gateway")
comp(1150, 146, 150, 68, "Proposal", "draft · note · watch", dash="5 3")
comp(1316, 146, 150, 68, "Confirm", "manager only", color=GREEN)
comp(1150, 230, 150, 68, "Audit log", "append-only, undo")
comp(1316, 230, 150, 68, "Executor", "deterministic")
c.arrow([(1300, 180), (1314, 180)])
c.arrow([(1391, 214), (1391, 228)])
c.arrow([(1316, 264), (1302, 264)])

# tools
c.rect(150, 360, 962, 82, fill="#FFFFFF", stroke=RULE, sw=1.1, rx=4)
chips = [("Retrieval", "8 tools"), ("Judgement", "2 tools"), ("Tracing", "1 tool"), ("Discovery", "1 tool"),
         ("Feasibility", "1 tool"), ("Action", "4 · propose only")]
for i, (name, sub) in enumerate(chips):
    comp(166 + i * 156, 372, 146, 58, name, sub, dash="5 3" if name == "Action" else None)

# data
c.rect(150, 472, 450, 76, fill="#FFFFFF", stroke=RULE, sw=1.1, rx=4)
c.text(164, 494, "Base data (read-only)", size=15, color=INK, bold=True)
x = 164
for lab in ["orders 120", "production_log 360", "workshops 8"]:
    x += pill(x, 509, lab) + 8
if x > 598:
    c.overflows.append("base pills")
c.rect(616, 472, 864, 76, fill="#FFFFFF", stroke=RULE, sw=1.1, rx=4)
c.text(630, 494, "System state (append-only)", size=15, color=INK, bold=True)
x = 630
for lab in ["notes", "watches", "pending_actions", "audit_log", "outbox", "evidence", "traces", "briefings"]:
    x += pill(x, 509, lab) + 8
if x > 1478:
    c.overflows.append(f"state pills to {x:.0f}")

# cross-layer flow with numbered steps
c.arrow([(222, 62), (222, 180)])
c.step(222, 80, 1)
c.arrow([(469, 252), (469, 358)], both=True)
c.step(469, 305, 2)
c.step(776, 182, 3)
c.arrow([(740, 180), (740, 64)])
c.step(740, 80, 4)
c.arrow([(1062, 144), (1062, 64)])
c.arrow([(1391, 64), (1391, 144)], color=GREEN, both=True)
c.arrow([(962, 300), (962, 358)], both=True)
c.arrow([(1112, 430), (1124, 430), (1124, 180), (1148, 180)], dash="5 3")
c.arrow([(1225, 300), (1225, 470)])
c.rect(1232, 396, 104, 16, fill="#FFFFFF")
c.text(1236, 408, "audited writes", size=13, color=MUTED)
c.arrow([(380, 444), (380, 470)], both=True)
c.arrow([(860, 444), (860, 470)], both=True)

# key
y = 588
x = 150
for n, lab in [(1, "question"), (2, "tool calls (≤ 6)"), (3, "grounding check"), (4, "reply + evidence")]:
    c.step(x + 10, y - 5, n)
    c.text(x + 26, y, lab, size=14, color=INK)
    x += 42 + c.width(lab, 14)
x += 20
for col, lab in [(VERMILLION, "LLM step"), (BLUE, "deterministic code"), (GREEN, "human checkpoint")]:
    c.rect(x, y - 13, 20, 14, fill=TINT[col], stroke=col, sw=1.3, rx=2)
    c.text(x + 27, y, lab, size=14, color=INK)
    x += 52 + c.width(lab, 14)
c.line(x, y - 6, x + 28, y - 6, color=INK, sw=1.3, dash="5 3")
c.text(x + 35, y, "proposal / fallback path", size=14, color=INK)

c.save(OUT)
