"""One visual style for every figure (SVG diagrams and matplotlib charts) and the slides.

Conventions follow journal figure practice (Nature figure guide): sans-serif Arial, bold lowercase panel
labels, thin strokes, white background, a colour-blind-safe palette (Okabe–Ito / Wong, Nature Methods 2011),
colour used for meaning rather than decoration. The categorical slots were checked with the dataviz
validator (vermillion, blue, bluish green pass CVD and normal-vision separation on white).
"""

INK = "#1A1A1A"
TEXT = "#333333"
MUTED = "#6B6B6B"
FAINT = "#9A9A9A"
RULE = "#C8C8C8"
GRID = "#E6E6E6"

VERMILLION = "#D55E00"  # LLM steps; the highlighted result
BLUE = "#0072B2"        # deterministic code; baselines
GREEN = "#009E73"       # human checkpoint
GREY = "#8C8C8C"        # data, comparison series

TINT = {VERMILLION: "#FBEAE0", BLUE: "#E3EEF7", GREEN: "#E0F2EC", GREY: "#F2F2F2"}

SANS = "Arial"
MONO = "Consolas"
FONT_FILES = {
    ("sans", False): "C:/Windows/Fonts/arial.ttf",
    ("sans", True): "C:/Windows/Fonts/arialbd.ttf",
    ("mono", False): "C:/Windows/Fonts/consola.ttf",
    ("mono", True): "C:/Windows/Fonts/consolab.ttf",
}


def apply_matplotlib_style():
    import matplotlib as mpl

    mpl.rcParams.update({
        "font.family": SANS, "font.size": 10, "axes.titlesize": 10.5, "axes.labelsize": 10,
        "xtick.labelsize": 9, "ytick.labelsize": 9, "legend.fontsize": 9,
        "axes.edgecolor": TEXT, "axes.labelcolor": TEXT, "xtick.color": TEXT, "ytick.color": TEXT,
        "axes.linewidth": 0.8, "xtick.major.width": 0.8, "ytick.major.width": 0.8,
        "xtick.major.size": 3, "ytick.major.size": 3,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": False, "legend.frameon": False,
        "savefig.dpi": 300, "savefig.bbox": "tight", "savefig.pad_inches": 0.04,
        "svg.fonttype": "none",
    })


def panel_label(ax, letter, x=-0.12, y=1.04):
    ax.text(x, y, letter, transform=ax.transAxes, fontsize=12, fontweight="bold", va="bottom", ha="left",
            color=INK)
