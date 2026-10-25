"""Deterministic name matching for customers, products and workshops (TOOL_SPEC §2).

"trend cart" → TrendCart, "hoodies" → Hoodie, "northwind" → Northwind Apparel, "loom and leaf" → Loom & Leaf.
The caller always reports what a name was matched as, so the interpretation is visible.
"""

from __future__ import annotations

import re


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower().replace("&", "and"))


def singulars(key: str) -> set[str]:
    """English plural → candidate singulars: scarves → scarf, polos → polo, hoodies → hoodie."""
    out = {key}
    if len(key) > 3 and key.endswith("s"):
        out.add(key[:-1])
        if key.endswith("ves"):
            out |= {key[:-3] + "f", key[:-3] + "fe"}
        if key.endswith("ies"):
            out.add(key[:-3] + "y")
        if key.endswith("es"):
            out.add(key[:-2])
    return out


def match(value: str, canonical: list[str]) -> list[str]:
    """Canonical values that `value` refers to: exact (incl. plurals) first, else unique-prefix/substring."""
    key = norm(value)
    if not key:
        return []
    keys = singulars(key)
    exact = [c for c in canonical if norm(c) in keys]
    if exact:
        return exact
    if len(key) < 4:
        return []
    return [c for c in canonical if any(k in norm(c) for k in keys)]
