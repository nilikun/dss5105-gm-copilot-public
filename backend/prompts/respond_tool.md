---
name: respond_tool
version: 2
purpose: Description of the final `respond` function the agent must call to end a turn.
changes: v2 — refuse covers partial answers whose core question the data cannot answer
---
Deliver the final reply to the manager and end the turn. Call it alone, after reading the tool results.
kind: answer (facts) · estimate (feasibility / projections) · clarify (ask which one) · refuse (the data cannot
answer the core question — use refuse even when you also give the related facts that do exist, e.g. the size
of a drop when asked for its cause, or a subcontract cost when asked for a margin) · propose (an action awaits
confirmation) · reject (a requested action cannot be done; say why).
Every number, date and id in headline, details, options and followups must appear in this turn's tool results.
