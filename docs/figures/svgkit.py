"""Tiny SVG builder with real-font text measurement, shared by the schematic figures.

Every text call can be checked against the room it has; `Canvas.save` refuses to write a figure with
overflowing text, so labels are never silently clipped.
"""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from PIL import ImageFont

from style import FONT_FILES, INK, MONO, SANS, TEXT


class Canvas:
    def __init__(self, width: int, height: int):
        self.w, self.h = width, height
        self.parts: list[str] = []
        self.overflows: list[str] = []
        self.markers: set[str] = set()

    # ----------------------------------------------------------------- measurement
    @staticmethod
    def width(s: str, size: float, bold: bool = False, mono: bool = False) -> float:
        font = ImageFont.truetype(FONT_FILES[("mono" if mono else "sans", bold)], 200)
        return font.getlength(s) * size / 200

    def check(self, s, size, room, bold=False, mono=False, where=""):
        if self.width(s, size, bold, mono) > room:
            self.overflows.append(f"{where}: '{s}' needs {self.width(s, size, bold, mono):.0f} > {room:.0f}")

    # ----------------------------------------------------------------- primitives
    def text(self, x, y, s, size=15, color=TEXT, bold=False, italic=False, mono=False, anchor="start",
             spacing=0.0, room=None, where=""):
        fam = f"{MONO}, 'Courier New', monospace" if mono else f"{SANS}, Helvetica, sans-serif"
        style = ' font-style="italic"' if italic else ""
        ls = f' letter-spacing="{spacing}"' if spacing else ""
        self.parts.append(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-size="{size}" '
                          f'font-weight="{700 if bold else 400}" fill="{color}" text-anchor="{anchor}"{style}{ls} '
                          f'xml:space="preserve">'
                          f'{escape(s)}</text>')
        if room is not None:
            self.check(s, size, room, bold, mono, where or s[:20])

    def rich(self, x, y, runs, size=15, anchor="start"):
        """runs: list of (text, dict(color=, bold=, mono=, italic=))."""
        tsp = []
        for s, o in runs:
            fam = f"{MONO}, 'Courier New', monospace" if o.get("mono") else f"{SANS}, Helvetica, sans-serif"
            ital = ' font-style="italic"' if o.get("italic") else ""
            tsp.append(f'<tspan font-family="{fam}" font-weight="{700 if o.get("bold") else 400}" '
                       f'fill="{o.get("color", TEXT)}"{ital}>{escape(s)}</tspan>')
        self.parts.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" '
                          f'xml:space="preserve">{"".join(tsp)}</text>')

    def rich_width(self, runs, size):
        return sum(self.width(s, size, o.get("bold", False), o.get("mono", False)) for s, o in runs)

    def rect(self, x, y, w, h, fill="none", stroke=None, sw=1.0, rx=3, dash=None):
        st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
        da = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" '
                          f'fill="{fill}"{st}{da}/>')

    def line(self, x1, y1, x2, y2, color=INK, sw=1.0, dash=None):
        da = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{sw}"{da}/>')

    def arrow(self, pts, color=INK, sw=1.3, dash=None, both=False):
        self.markers.add(color)
        d = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)
        da = f' stroke-dasharray="{dash}"' if dash else ""
        m = f"url(#ah{color[1:]})"
        st = f' marker-start="{m}"' if both else ""
        self.parts.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}"{da} '
                          f'marker-end="{m}"{st} stroke-linejoin="round"/>')

    def circle(self, cx, cy, r, fill="none", stroke=None, sw=1.0):
        st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
        self.parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"{st}/>')

    def step(self, cx, cy, n, color=INK):
        """Numbered step marker, as used in method figures."""
        self.circle(cx, cy, 10, fill=color)
        self.text(cx, cy + 4.6, str(n), size=12.5, color="#FFFFFF", bold=True, anchor="middle")

    def raw(self, s):
        self.parts.append(s)

    # ----------------------------------------------------------------- output
    def svg(self) -> str:
        defs = "".join(
            f'<marker id="ah{c[1:]}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" markerHeight="6.5" '
            f'orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="{c}"/></marker>'
            for c in sorted(self.markers))
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" '
                f'height="{self.h}"><defs>{defs}</defs><rect width="{self.w}" height="{self.h}" fill="#FFFFFF"/>'
                + "".join(self.parts) + "</svg>")

    def save(self, stem: Path, scale: int = 3) -> None:
        if self.overflows:
            raise SystemExit("Text overflow:\n" + "\n".join(self.overflows))
        svg_path = stem.with_suffix(".svg")
        svg_path.write_text(self.svg(), encoding="utf-8")
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge")
            page = browser.new_page(viewport={"width": self.w, "height": self.h}, device_scale_factor=scale)
            page.goto(svg_path.resolve().as_uri())
            page.screenshot(path=str(stem.with_suffix(".png")))
            browser.close()
        print("wrote", svg_path, stem.with_suffix(".png"))
