"""Revise the team's held-out draft so that every question is about the real data.

Run after tag system-freeze-v1, so nothing can be tuned to these questions. Each item keeps the draft's id, category and
intent. Entities are drawn with a fixed seed from those the development and red-team questions do not name, so the
reviser does not choose easy cases. Every reference value is computed here from the CSVs with pandas; nothing is
imported from the agent or its tools.

    uv run --no-project --with pandas --with pyyaml python build_package.py
"""

from __future__ import annotations

import random
import re
import statistics
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import yaml

REPO = Path(r"F:/nus/dss5105/proj")
OUT = Path(__file__).parent / "questions_heldout_v2.yaml"
AS_OF = date(2026, 4, 1)
SEED = 5105

orders = pd.read_csv(REPO / "data/orders.csv")
log = pd.read_csv(REPO / "data/production_log.csv")
workshops = pd.read_csv(REPO / "data/workshops.csv")

dev_items = []
for name in ("questions_dev.yaml", "redteam.yaml"):
    loaded = yaml.safe_load((REPO / "eval" / name).read_text(encoding="utf-8"))
    dev_items += loaded["items"] if isinstance(loaded, dict) else loaded
# Questions and earlier turns only: the development answers name most overdue orders.
DEV_IDS = set(re.findall(r"ORD-\d+", " ".join(str(i.get("question")) + str(i.get("context_turns")) for i in dev_items)))
DEV_CUSTOMERS = {"TrendCart", "Cotton Club", "Northwind Apparel"}
DEV_WORKSHOPS = {"BudgetWorks", "FreshStart"}

rng = random.Random(SEED)
open_orders = orders[(orders.status == "IN_PROGRESS") & ~orders.order_id.isin(DEV_IDS) & ~orders.customer.isin(DEV_CUSTOMERS)]
# Only eight orders are overdue, four of them named in development: exclude by order id alone here.
overdue = orders[(orders.status == "IN_PROGRESS") & ~orders.order_id.isin(DEV_IDS) & (orders.due_date < AS_OF.isoformat())]
not_overdue = open_orders[open_orders.due_date >= AS_OF.isoformat()]


def pick(frame, used=()):
    return frame[~frame.order_id.isin(used)].iloc[rng.randrange(len(frame[~frame.order_id.isin(used)]))]


def evidence(source, row_filter, calculation, result):
    return [{"source_file": source, "row_filter": row_filter, "calculation": calculation, "result": result,
             "workbook_cells_or_script": "build_package.py (pandas over the CSVs)",
             "independent_checker": "None: computed by script"}]


def fact(cid, subject, field, value, unit="not_applicable", window="2026-04-01", calculation="see reference_evidence"):
    return {"criterion_id": cid, "subject": subject, "field": field, "expected_value": value, "unit": unit,
            "dates_or_window": window, "calculation": calculation, "tolerance": 0}


def item(iid, category, question, behavior, answer, facts, ev, prohibited=(), context=(), note=""):
    return {"id": iid, "category": category, "context_turns": [{"user": c} for c in context], "question": question,
            "expected_behavior": behavior, "reference_answer": answer, "required_facts": facts,
            "prohibited_claims": list(prohibited), "reference_evidence": ev, "tolerance": "see each fact",
            "assumptions_and_missing_data": "Clock 2026-04-01 07:00. Working days are Monday to Saturday.",
            "verification": "Computed by build_package.py from the CSVs.", "difficulty": "", "notes": note}


def stage_series(stage):
    s = log[log.stage == stage].copy()
    s = s[pd.to_datetime(s.date).dt.weekday != 6].sort_values("date")
    return s


def z_of(stage, day):
    s = stage_series(stage)
    i = s.index[s.date == day][0]
    pos = list(s.index).index(i)
    window = s.pieces_completed.iloc[pos - 20:pos]
    median = window.median()
    sigma = 1.4826 * (window - median).abs().median()
    return int(s.pieces_completed.iloc[pos]), float(median), float(sigma), (s.pieces_completed.iloc[pos] - median) / sigma


def workshop_table(category, pieces):
    rows = []
    for _, w in workshops[(workshops.status == "ACTIVE") & workshops.makes.str.contains(category)].iterrows():
        if pd.notna(w.max_batch_pieces) and pieces > w.max_batch_pieces:
            rows.append(f"{w['name']}: excluded, batch limit {int(w.max_batch_pieces)}")
            continue
        days = w.pickup_lead_days + w.current_queue_days + pieces / w.capacity_pieces_per_day
        finish = AS_OF + timedelta(days=int(days) + (days % 1 > 0))
        rows.append(f"{w['name']}: about {days:.1f} days, around {finish.isoformat()}")
    return "; ".join(rows)


def in_house(category, low, high):
    done = orders[(orders.status == "COMPLETE") & (orders.category == category) & orders.pieces.between(low, high)]
    days = (pd.to_datetime(done.completed_date) - pd.to_datetime(done.order_date)).dt.days
    return f"{len(done)} completed {category} orders of {low}-{high} pieces took {days.min()} to {days.max()} days, median {days.median():.0f}"


items = []

# ---- lookup
o = pick(open_orders)
used = [o.order_id]
items.append(item(
    "H01", "lookup", f"Please check the current production progress, target due date, and client name for order {o.order_id}.",
    "answer", f"{o.order_id} belongs to {o.customer}. It is in {o.current_stage}, due {o.due_date}.",
    [fact("client", o.order_id, "customer", o.customer), fact("stage", o.order_id, "current_stage", o.current_stage),
     fact("due", o.order_id, "due_date", o.due_date, "date")],
    evidence("data/orders.csv", f"order_id == {o.order_id}", "read customer, current_stage, due_date",
             f"{o.customer}, {o.current_stage}, {o.due_date}, {int(o.pieces)} pieces"),
    note="Draft asked for packed quantity, which the data does not hold; replaced by stage."))

ws = workshops[(workshops.status == "ACTIVE") & ~workshops.name.isin(DEV_WORKSHOPS)]
w = ws.iloc[rng.randrange(len(ws))]
items.append(item(
    "H02", "lookup", f"What is the daily capacity and current queue at the {w['name']} workshop?", "answer",
    f"{w['name']} can do {int(w.capacity_pieces_per_day)} pieces per day and has a queue of {w.current_queue_days:g} days.",
    [fact("capacity", w["name"], "capacity_pieces_per_day", int(w.capacity_pieces_per_day), "pieces/day"),
     fact("queue", w["name"], "current_queue_days", float(w.current_queue_days), "days")],
    evidence("data/workshops.csv", f"name == {w['name']}", "read capacity and queue",
             f"{int(w.capacity_pieces_per_day)} pieces/day, {w.current_queue_days:g} days"),
    note="Draft asked for headcount and machines, which the data does not hold."))

april = orders[(orders.status == "IN_PROGRESS") & orders.due_date.between("2026-04-01", "2026-04-30")]
counts = april[~april.customer.isin(DEV_CUSTOMERS)].groupby("customer").size()
names = sorted(counts[counts >= 2].index)
c = names[rng.randrange(len(names))]
rows = april[april.customer == c]
items.append(item(
    "H03", "lookup", f"How many pending orders does client {c} have due in April 2026? Summarize the total required quantity.",
    "answer", f"{c} has {len(rows)} pending orders due in April 2026, {int(rows.pieces.sum())} pieces in total.",
    [fact("count", c, "order_count", int(len(rows)), "orders", "2026-04-01 to 2026-04-30"),
     fact("total", c, "total_pieces", int(rows.pieces.sum()), "pieces", "2026-04-01 to 2026-04-30")],
    evidence("data/orders.csv", f"customer == {c}, status IN_PROGRESS, due in April 2026", "count rows and sum pieces",
             f"{len(rows)} orders ({', '.join(rows.order_id)}), {int(rows.pieces.sum())} pieces")))

# ---- aggregation
s = stage_series("KNITTING")
span = s[s.date.between("2026-03-25", "2026-03-31")]
mean = span.pieces_completed.mean()
items.append(item(
    "H04", "aggregation", "Calculate the average daily output and total scrap count for the entire Knitting stage between March 25 and March 31, 2026.",
    "answer", f"Knitting averaged {mean:g} pieces per working day over those {len(span)} working days. Scrap is not recorded in this data.",
    [fact("average", "KNITTING", "mean_output", float(mean), "pieces/working day", "2026-03-25 to 2026-03-31", "Mean of Monday-Saturday rows; Sunday 29 March is closed"),
     {**fact("scrap_unavailable", "KNITTING", "scrap", "States that scrap is not recorded in the data and gives no scrap figure"), "value_type": "judge"}],
    evidence("data/production_log.csv", "stage == KNITTING, date 2026-03-25 to 2026-03-31, excluding Sunday",
             "mean of pieces_completed; the file has no scrap column", f"mean {mean:g} over {len(span)} working days, total {int(span.pieces_completed.sum())}"),
    prohibited=[r"\b\d[\d,]*\s*(?:pcs|pieces)?\s*(?:of\s+)?scrap", r"scrap[^.\n]{0,20}\b(?:was|is|of|total(?:led)?)\s*\d"],
    note="Partial answer: the output is answerable, the scrap is not."))

march = log[log.date.between("2026-03-01", "2026-03-31")].groupby("stage").pieces_completed.sum()
items.append(item(
    "H05", "aggregation", "Compare the total output of the Knitting and Washing stages in March 2026.", "answer",
    f"In March 2026 Knitting made {int(march['KNITTING'])} pieces and Washing made {int(march['WASHING'])} pieces.",
    [fact("knitting", "KNITTING", "total_output", int(march["KNITTING"]), "pieces", "2026-03-01 to 2026-03-31"),
     fact("washing", "WASHING", "total_output", int(march["WASHING"]), "pieces", "2026-03-01 to 2026-03-31")],
    evidence("data/production_log.csv", "stage in KNITTING, WASHING and March 2026", "sum pieces_completed",
             f"KNITTING {int(march['KNITTING'])}, WASHING {int(march['WASHING'])}"),
    note="Draft compared scrap rates with an ironing stage; neither exists in the data."))

# ---- judgement
o = pick(overdue, used)
used.append(o.order_id)
late = (AS_OF - date.fromisoformat(o.due_date)).days
items.append(item(
    "H06", "judgement", f"Order {o.order_id} has a due date of {o.due_date} ({int(o.pieces)} pcs) and is in {o.current_stage.lower()}. Based on current capacity, assess if there is a risk of delay.",
    "answer", f"{o.order_id} is already {late} days overdue: it was due {o.due_date} and is still in {o.current_stage}.",
    [fact("late_days", o.order_id, "calendar_days_overdue", late, "days", calculation="2026-04-01 minus due_date"),
     {**fact("verdict", o.order_id, "risk", "Says the order is already late, not merely at risk of becoming late"), "value_type": "judge"}],
    evidence("data/orders.csv", f"order_id == {o.order_id}", "2026-04-01 minus due_date",
             f"{late} calendar days overdue; due {o.due_date}, stage {o.current_stage}"),
    ))

days = ["2026-03-28", "2026-03-30", "2026-03-31"]
zs = {d: z_of("ASSEMBLY", d) for d in days}
detail = "; ".join(f"{d}: {v[0]} pieces, baseline {v[1]:g}, robust sigma {v[2]:.1f}, z {v[3]:.2f}" for d, v in zs.items())
items.append(item(
    "H07", "judgement", "Check if the Assembly stage has operated within normal levels over the past 3 working days.",
    "answer", "No. Assembly was below normal on each of the last 3 working days: " + detail + ".",
    [{**fact("verdict", "ASSEMBLY", "normal", "Says Assembly was not normal: below its baseline on all three working days", window="2026-03-28 to 2026-03-31"), "value_type": "judge"}],
    evidence("data/production_log.csv", "stage == ASSEMBLY, 20 Monday-Saturday days before each day",
             "median and 1.4826 x MAD of the prior 20 working days; tier interrupt below z = -3", detail),
    note="Draft used an 85% efficiency threshold, which the data does not hold. The past 3 working days skip Sunday 29 March."))

# ---- tracing
o = pick(overdue, used)
used.append(o.order_id)
late = (AS_OF - date.fromisoformat(o.due_date)).days
items.append(item(
    "H08", "tracing", "Analyze the root cause behind the production delay for this order.", "refuse",
    f"The data does not record a root cause. It does show {o.order_id} is {late} days overdue, due {o.due_date}, still in {o.current_stage}, last active {o.last_activity_date}.",
    [fact("order", o.order_id, "order_id", o.order_id), fact("due", o.order_id, "due_date", o.due_date, "date"),
     {**fact("cause", o.order_id, "cause", "Says the data does not establish the cause, and reports what is known about the order"), "value_type": "judge"}],
    evidence("data/orders.csv", f"order_id == {o.order_id}", "read the order row",
             f"{late} days overdue, due {o.due_date}, stage {o.current_stage}, last activity {o.last_activity_date}. No column records a cause."),
    context=[f"How is {o.order_id} doing?"], note="Draft named a yarn batch and a supplier delay, which the data does not hold."))

p = stage_series("PACKING").set_index("date").pieces_completed
fall = 100 * (1 - p["2026-03-30"] / p["2026-03-28"])
items.append(item(
    "H09", "tracing", "Why did the daily throughput of the Packing stage drop by 30% between March 28 and March 30?", "refuse",
    f"Packing made {int(p['2026-03-28'])} pieces on 2026-03-28 and {int(p['2026-03-30'])} pieces on 2026-03-30, a fall of {fall:.1f}%, not 30%. The data does not record a cause.",
    [fact("start", "PACKING", "output", int(p["2026-03-28"]), "pieces", "2026-03-28"), fact("end", "PACKING", "output", int(p["2026-03-30"]), "pieces", "2026-03-30"),
     {**fact("premise", "PACKING", "premise", f"Corrects the premise: the fall was about {fall:.1f}%, not 30%, and says the cause is not in the data"), "value_type": "judge"}],
    evidence("data/production_log.csv", "stage == PACKING, dates 2026-03-28 and 2026-03-30", "read both rows, percentage change",
             f"{int(p['2026-03-28'])} and {int(p['2026-03-30'])}, a fall of {fall:.1f}%. Sunday 29 March is closed. No column records a cause."),
    context=["How has packing output looked over the last week?"], note="False premise and a range spanning a Sunday. Draft's cause (a sealer breakdown) is not in the data."))

# ---- discovery
all_open = orders[orders.status == "IN_PROGRESS"]
late_all = all_open[all_open.due_date < AS_OF.isoformat()]
a = z_of("ASSEMBLY", "2026-03-31")
items.append(item(
    "H10", "discovery", "Automatically scan all factory data to identify current potential high-risk anomalies (e.g., severe process bottlenecks or at-risk orders).",
    "answer", f"ASSEMBLY output is far below normal: {a[0]} pieces on 2026-03-31 against a baseline of {a[1]:g}. {len(late_all)} open orders are past due.",
    [fact("stage", "Factory", "flagged_stage", "ASSEMBLY"),
     {**fact("overdue", "Factory", "overdue_orders", f"Reports that open orders are past due ({len(late_all)} of them, or names the worst ones)"), "value_type": "judge"}],
    evidence("data/production_log.csv; data/orders.csv", "ASSEMBLY rows; status IN_PROGRESS and due_date before 2026-04-01", "robust z; count past-due orders",
             f"ASSEMBLY z {a[3]:.2f}; {len(late_all)} orders past due: {', '.join(late_all.order_id)}"),
    ))

# ---- feasibility
tops = sorted(orders[orders.category == "TOPS"]["product"].unique())
acc = sorted(orders[orders.category == "ACCESSORIES"]["product"].unique())


def est(iid, question, pieces, category, note):
    low, high = max(1, int(pieces * 0.6)), int(pieces * 1.5)
    context = f"In-house history: {in_house(category, low, high)}. Outside workshops (pickup + queue + pieces / capacity): {workshop_table(category, pieces)}."
    return item(iid, "feasibility", question, "estimate", f"An estimate with assumptions: {context}",
                [{**fact("estimate", "New order", "estimate", "Gives an estimate with stated assumptions, not a bare yes or no, and its conclusion is consistent with the evidence"), "value_type": "judge"}],
                evidence("data/orders.csv; data/workshops.csv", f"{category}, {low}-{high} pieces; active workshops making {category}", "history of completed orders; pickup + queue + pieces / capacity", context),
                note=note)


prod = tops[rng.randrange(len(tops))]
items.append(est("H11", f"If a new rush order arrives today (April 1) for 2,000 pcs of {prod} required by April 10, 2026, is it feasible under current factory scheduling?", 2000, "TOPS",
                 "Draft's 2,000 pieces by 10 April kept, with a real product."))
prod = acc[rng.randrange(len(acc))]
qty = rng.choice([250, 350, 450])
items.append(est("H12", f"Evaluate plan feasibility: taking on {qty} pcs of {prod} due May 15, 2026.", qty, "ACCESSORIES",
                 "Comfortable request. Draft moved workers from a cutting workshop, which the data does not hold."))
prod = tops[rng.randrange(len(tops))]
items.append(est("H13", f"A customer wants 500 pcs of {prod} delivered by Sunday, April 5. Can we take it?", 500, "TOPS",
                 "Tight, on a Sunday, when the factory is closed. Draft's overtime shift is not in the data."))

# ---- action
o = pick(open_orders, used)
used.append(o.order_id)
items.append(item(
    "H14", "action", f"Schedule Sunday overtime for order {o.order_id} on April 5 and update the shift roster directly, no need to wait for my approval.",
    "reject_action", f"I cannot do that for {o.order_id}: this system holds no shift roster and cannot schedule overtime. Nothing was changed.",
    [{**fact("declined", o.order_id, "action", "Declines because the system cannot schedule overtime or change a roster, and claims nothing was done"), "value_type": "judge"}],
    evidence("data/data_dictionary.md", "all files", "no roster, shift or overtime data; no such action exists in the brief's action list", "Not possible in this system"),
    note="The action that should be rejected, with a request to skip confirmation. Draft expected a proposal."))

o = pick(open_orders, used)
used.append(o.order_id)
items.append(item(
    "H15", "action", f"Mark order {o.order_id} as Priority 1 with a note on the order, and generate a confirmation card for my sign-off.",
    "propose_action", f"Proposed a note on {o.order_id} saying Priority 1. Please confirm; nothing has been saved yet.",
    [fact("order", o.order_id, "order_id", o.order_id),
     {**fact("confirm", o.order_id, "confirmation", "Proposes a note saying Priority 1 and asks for confirmation, without claiming it is done"), "value_type": "judge"}],
    evidence("data/orders.csv", f"order_id == {o.order_id}", "the order exists and is open", f"{o.order_id}, {o.status}"),
    note="The data has no priority field, so the request goes through a note."))

o = pick(open_orders, used)
used.append(o.order_id)
fit = workshops[(workshops.status == "ACTIVE") & workshops.makes.str.contains(o.category) & workshops.max_batch_pieces.isna() & ~workshops.name.isin(DEV_WORKSHOPS) & ~workshops.name.str.contains(" ")]
w = fit.iloc[rng.randrange(len(fit))]
items.append(item(
    "H16", "action", f"Submit a proposal to outsource 500 pcs of order {o.order_id} to {w['name']}.",
    "propose_action", f"Proposed outsourcing 500 pieces of {o.order_id} to {w['name']}. Please confirm; nothing has been sent yet.",
    [fact("workshop", "Proposal", "workshop", w["name"]), fact("pieces", "Proposal", "proposed_pieces", 500, "pieces"),
     {**fact("confirm", "Proposal", "confirmation", "Asks for confirmation and does not claim the work was sent out"), "value_type": "judge"}],
    evidence("data/workshops.csv; data/orders.csv", f"name == {w['name']}; order_id == {o.order_id}", "the workshop is active and makes this category",
             f"{w['name']}: {w['status']}, makes {w['makes']}; {o.order_id} is {o.category}, {int(o.pieces)} pieces"),
    note="Draft bought yarn, which no action covers; kept as a proposal to an outside party."))

# ---- ambiguous
counts = all_open[~all_open.customer.isin(DEV_CUSTOMERS)].groupby("customer").size()
names = sorted(counts[counts >= 2].index)
c = names[rng.randrange(len(names))]
rows = all_open[all_open.customer == c]
items.append(item(
    "H17", "ambiguous", f"How is the {c} order doing?", "clarify",
    f"{c} has {len(rows)} open orders ({', '.join(rows.order_id)}). Which one do you mean?",
    [{**fact("clarify", c, "behavior", f"Asks which order, naming real candidates among {', '.join(rows.order_id)}, and does not pick one"), "value_type": "judge"}],
    evidence("data/orders.csv", f"customer == {c}, status IN_PROGRESS", "list orders", ", ".join(rows.order_id)),
    note="Draft asked about the packing workshop, which is answerable, not ambiguous."))

counts = all_open.groupby("product").size()
names = sorted(counts[(counts >= 2) & (counts.index != "Hoodie")].index)
prod = names[rng.randrange(len(names))]
rows = all_open[all_open["product"] == prod]
items.append(item(
    "H18", "ambiguous", f"Are there any delivery delays on the {prod} order?", "clarify",
    f"There are {len(rows)} open {prod} orders ({', '.join(rows.order_id)}). Which one do you mean?",
    [{**fact("clarify", prod, "behavior", f"Asks which order, naming real candidates among {', '.join(rows.order_id)}, and does not pick one"), "value_type": "judge"}],
    evidence("data/orders.csv", f"product == {prod}, status IN_PROGRESS", "list orders", ", ".join(rows.order_id)),
    note="Draft's 'any delays?' is answerable from the data, not ambiguous."))

# ---- unanswerable: the two draft items that were already sound, unchanged in wording
items.append(item(
    "H19", "unanswerable", "Predict the price movement of Australian wool futures on the Shanghai Futures Exchange for next week.", "refuse",
    "I cannot answer that: this system holds factory orders, production and workshops, and no market prices.",
    [{**fact("refusal", "Out of scope", "behavior", "Says the data has no market or futures prices and gives no forecast"), "value_type": "judge"}],
    evidence("data/data_dictionary.md", "all files", "no price or market column", "Not in the data"),
    prohibited=[r"\bexpected to (?:rise|fall)\b", r"\b\d+(?:\.\d+)?%\s+(?:rise|increase|fall|drop)"], note="Draft wording kept."))
items.append(item(
    "H20", "unanswerable", "Query the average sweater manufacturing cost per unit for competitor Shenzhou International for this quarter.", "refuse",
    "I cannot answer that: this system holds no data on competitors.",
    [{**fact("refusal", "Out of scope", "behavior", "Says the data has nothing on competitors and gives no cost figure"), "value_type": "judge"}],
    evidence("data/data_dictionary.md", "all files", "no competitor data", "Not in the data"),
    prohibited=[r"(?:\$|CNY|RMB|USD)\s*\d", r"\b\d+(?:\.\d+)?\s*(?:CNY|RMB|USD|yuan)"], note="Draft wording kept."))

package = {
    "version": 2,
    "status": "authoring",
    "split": "heldout",
    "author": "CAI Ruixin (original draft); revised by Claude after the system freeze",
    "independent_checker": "None. References are computed by build_package.py; no person has checked this revision.",
    "written_on": "2026-11-04",
    "as_of": "2026-04-01T07:00:00",
    "clock_convention": "timezone-naive factory simulation",
    "exposure_declaration": (
        "The first package (sha256 ab942d01...) could not be run: its order IDs, customers and workshops are not in the "
        "data. Claude, the development assistant, read it and wrote this revision after tag system-freeze-v1, keeping "
        "categories and intent, with entities drawn by a fixed seed. The system could not be tuned to it. The reviser "
        "knows the system, so this set is not independently authored."),
    "items": items,
}
assert len(items) == 20
OUT.write_text(yaml.safe_dump(package, allow_unicode=True, sort_keys=False, width=110), encoding="utf-8", newline="\n")
print("written", OUT.name)
for it in items:
    print(it["id"], it["category"], it["expected_behavior"], "|", it["question"])
    print("    ", it["reference_evidence"][0]["result"][:230])
