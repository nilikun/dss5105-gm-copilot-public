"""Product → category, from the products the factory has actually made (orders table)."""

from __future__ import annotations

import sqlite3

from app.domain.names import match


def product_categories(db: sqlite3.Connection) -> dict[str, str]:
    return {r[0]: r[1] for r in db.execute("SELECT DISTINCT product, category FROM orders")}


def resolve_product(db: sqlite3.Connection, product: str) -> tuple[str | None, str | None, list[str]]:
    """(canonical product, category, candidates). Unknown → (None, None, known products)."""
    cats = product_categories(db)
    hits = match(product, list(cats))
    if len(hits) == 1:
        return hits[0], cats[hits[0]], hits
    return None, None, hits or sorted(cats)
