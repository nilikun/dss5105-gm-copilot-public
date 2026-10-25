"""describe_data_coverage — what the data holds and what it does not (Retrieval; tool 8).

Backs honest refusals with a checkable statement. The catalogue is a reviewed static list."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from app.tools.base import ToolContext, ToolResult
from app.tools.registry import tool

CATALOGUE = [
    {"topic": "order prices, revenue, margin, profit", "covered": False,
     "keywords": ["price", "revenue", "margin", "profit", "sales", "income", "earn", "invoice", "pay", "money"],
     "closest": "Workshop cost_per_piece exists, so the cost of subcontracting can be computed; what customers pay "
                "for orders is not in the data."},
    {"topic": "workers, staff, shifts, people", "covered": False,
     "keywords": ["worker", "staff", "employee", "operator", "shift", "people", "person", "who made", "team",
                  "slowest", "fastest worker", "overtime", "headcount"],
     "closest": "Only factory-wide output per stage per day."},
    {"topic": "machines, breakdowns, maintenance", "covered": False,
     "keywords": ["machine", "breakdown", "maintenance", "downtime", "equipment", "repair"],
     "closest": "Only factory-wide output per stage per day; no cause is recorded for a drop."},
    {"topic": "causes and reasons for delays or drops", "covered": False,
     "keywords": ["why did", "cause", "reason", "because"],
     "closest": "The data records what happened (output, stages, dates), not why."},
    {"topic": "materials, yarn, inventory, suppliers", "covered": False,
     "keywords": ["yarn", "material", "inventory", "stock", "supplier", "fabric"],
     "closest": "None."},
    {"topic": "which workshop made a past order / outsourcing history", "covered": False,
     "keywords": ["outsourced", "subcontracted", "sent to", "which workshop made"],
     "closest": "Workshop profile cards exist, but no order is linked to a workshop."},
    {"topic": "quality complaints or defects per order", "covered": False,
     "keywords": ["complaint", "defect per order", "returned", "rework on"],
     "closest": "Each workshop has a defect_rate; orders carry no quality record."},
    {"topic": "shipping, delivery tracking, customer contacts", "covered": False,
     "keywords": ["shipping", "tracking", "courier", "contact", "email address", "phone"],
     "closest": "Orders have due and completion dates only."},
    {"topic": "orders (customer, product, pieces, dates, stage, lateness)", "covered": True,
     "keywords": ["order", "customer", "due", "late", "stage", "pieces"], "closest": "orders table, 120+ rows"},
    {"topic": "daily output per stage", "covered": True,
     "keywords": ["output", "production", "knitting", "assembly", "washing", "packing"],
     "closest": "production_log, daily per stage"},
    {"topic": "outside workshops (capacity, queue, defects, cost, status)", "covered": True,
     "keywords": ["workshop", "subcontract", "outsource", "capacity", "queue", "cost per piece"],
     "closest": "workshops table, 8 rows"},
]


class CoverageParams(BaseModel):
    topic: str = Field(description="What the manager asked about, in a few words (e.g. 'revenue of TrendCart orders')")


@tool("describe_data_coverage", "retrieval",
      "Check whether the data can answer a topic at all before answering or refusing. Returns covered "
      "true/false/unknown, the closest available data, and the date ranges of the tables. Use it for questions "
      "about money, people, machines, causes, materials or anything outside orders/output/workshops.",
      CoverageParams)
def describe_data_coverage(ctx: ToolContext, topic: str) -> ToolResult:
    t = topic.lower()
    hits = [c for c in CATALOGUE if any(re.search(rf"\b{re.escape(k)}", t) for k in c["keywords"])]
    not_covered = [c for c in hits if not c["covered"]]
    match = not_covered[0] if not_covered else (hits[0] if hits else None)
    lo, hi = ctx.db.execute("SELECT MIN(date), MAX(date) FROM production_log").fetchone()
    o_lo, o_hi = ctx.db.execute("SELECT MIN(order_date), MAX(order_date) FROM orders").fetchone()
    data = {"topic": topic,
            "covered": (match["covered"] if match else "unknown"),
            "matched_catalogue_entry": match["topic"] if match else None,
            "closest_available": match["closest"] if match else None,
            "tables": {"orders": f"order dates {o_lo} to {o_hi}", "production_log": f"{lo} to {hi}",
                       "workshops": "current profile cards"}}
    warnings = [] if match else ["topic not in the coverage catalogue: say you are not sure rather than guess"]
    return ctx.ok(data, warnings=warnings)
