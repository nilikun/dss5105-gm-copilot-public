# Tool Specification — v1

> Status: **v1 draft (2026-10-08)**, written before implementation. Every tool here is specified before it
> is built (track requirement). Changes after implementation start are recorded in §8.
> Related: `docs/PLAN.md` (§6 agent design, §8 judgement), `analysis/`.

---

## 1. Design principles

1. **Tools compute, the model narrates.** Every count, sum, average, difference, ranking and date
   calculation happens in a tool. The LLM chooses tools, reads results, and writes the reply.
2. **Narrow and typed.** No `run_sql`. Each tool answers one kind of question with a validated input schema.
   Accepted failure mode: an unanticipated question gets an honest "I can't answer that with my tools"
   instead of a hallucinated join.
3. **Evidence on every result.** Each tool registers the rows it used and returns `evidence_id`s. Any
   number in a reply must come from a result produced in the same turn (checked by the verifier).
4. **Definitions are data, not prompt text.** Judgement tools return the definition and parameters they
   applied, so the manager (and reviewers) can inspect them.
5. **Ambiguity is detected in tools.** If a request that should name one entity matches several, the tool
   says so and returns the candidates; it never picks one silently.
6. **Time comes from the clock.** `as_of` is injected by the runtime, never chosen by the LLM. Relative dates
   are resolved by a tool, because date math is arithmetic.
7. **No side effects without the manager.** Action tools only create *proposals*. Execution happens via a UI
   confirm endpoint that the LLM cannot call.

## 2. Common envelope

Every tool returns:

```json
{
  "ok": true,
  "data": { ... },                      // tool-specific, typed
  "evidence": [ {"id": "E12", "source": "orders", "keys": ["ORD-120"], "description": "order row"} ],
  "definition": { ... } | null,         // judgement tools: the rule and parameters used
  "warnings": ["..."],                  // e.g. data limitations relevant to this answer
  "as_of": "2026-04-01T07:00"
}
```

Errors are typed, so the agent can react correctly:

| code | Meaning | Expected agent behaviour |
|---|---|---|
| `NOT_FOUND` | ID / name does not exist | Say so; suggest close matches if returned |
| `AMBIGUOUS` | Several entities match a singular reference; `candidates` attached | Ask the manager to choose |
| `OUT_OF_COVERAGE` | The data cannot answer this (e.g. revenue) | Refuse and say what data is missing |
| `INVALID_ARGUMENT` | Bad input (unknown stage, date in wrong range) | Fix arguments or ask |
| `PRECONDITION_FAILED` | Action not allowed (e.g. watch on a COMPLETE order) | Explain, offer alternative |

Name matching (customers, products, workshops) is deterministic: case-insensitive, whitespace/punctuation
normalised, singular/plural and a small alias table ("trend cart" → TrendCart, "hoodies" → Hoodie). The
result reports `matched_as` so the interpretation is visible.

---

## 3. Tool summary

| # | Kind | Tool | Question it exists to answer |
|---|---|---|---|
| 1 | Retrieval | `resolve_time` | "What date is 'Thursday' / 'the 25th' / 'last week'?" |
| 2 | Retrieval | `get_order` | "Show the full fact sheet and notes for ORD-120." |
| 3 | Retrieval | `find_orders` | "Which TrendCart orders are still open?" |
| 4 | Retrieval | `summarize_orders` | "How many orders are late, by customer?" |
| 5 | Retrieval | `get_stage_output` | "How much did assembly do yesterday / this week?" |
| 6 | Retrieval | `get_workshops` | "Which outside workshops can make tops?" |
| 7 | Retrieval | `get_activity` | "What did I ask you to do today? Any notes on ORD-120?" |
| 8 | Retrieval | `describe_data_coverage` | "Can this system tell me X at all?" |
| 9 | Judgement | `compare_to_normal` | "Is 420 from assembly normal?" |
| 10 | Judgement | `assess_order_risk` | "Is ORD-120 at risk? Which orders are at risk?" |
| 11 | Tracing | `get_evidence` | "Why? Show me the rows behind that." |
| 12 | Discovery | `scan_exceptions` | "Anything I should know?" / the briefing's findings |
| 13 | Feasibility | `estimate_feasibility` | "Can we take 800 hoodies by the 25th?" |
| 14 | Action | `propose_message` | "Chase it up." |
| 15 | Action | `propose_note` | "Add a note that the customer called." |
| 16 | Action | `propose_watch` | "Tell me if ORD-xxx hasn't moved by Thursday." / "Remind me tomorrow…" |
| 17 | Action | `propose_cancel_watch` | "Stop watching that." |
| 18 | Retrieval | `get_order_status` | "How is this order progressing against its deadline?" |
| 19 | Action | `propose_outsourcing` | "Draft an outsourcing order with SteadyHands for the 800 hoodies." |

Not LLM tools (runtime components): verifier, action executor, watch evaluator, briefing pipeline,
clock / data advancer. They are specified in `docs/PLAN.md` §6–§7.

---

## 4. Tool specifications

### 1. `resolve_time` — Retrieval

| | |
|---|---|
| **Input** | `expression: str` (e.g. "yesterday", "Thursday", "the 25th", "next week", "2026-04-10") |
| **Output** | `start: date`, `end: date` (equal for a single day), `interpretation: str`, `working_days: int` (Mon–Sat in range), `includes_sunday: bool`, `is_past: bool` |
| **Purpose** | Turn relative time phrases into explicit dates against the clock, so no date arithmetic happens in the model. |
| **Non-goals** | Does not interpret business meaning ("end of season"); does not choose a year other than the nearest sensible one. |
| **Failure modes** | Ambiguous phrase ("the 5th" when the 5th of this month has passed) → returns `AMBIGUOUS` with both candidates. "Yesterday" on a Monday is Sunday (factory closed) → `warnings` notes it and offers the last working day. |

### 2. `get_order` — Retrieval

| | |
|---|---|
| **Input** | `order_id: str` (normalised: "ord 58", "58" → ORD-058) |
| **Output** | All order columns + derived: `days_to_due` (negative = overdue), `idle_days`, `idle_working_days`, `stages_remaining: list`, `is_overdue`, `notes: list`, `active_watches: list` |
| **Purpose** | The complete, current fact sheet for one order. |
| **Non-goals** | No risk judgement (→ `assess_order_risk`); no history of stage transitions (data does not have it). |
| **Failure modes** | Unknown ID → `NOT_FOUND` with nearest IDs. COMPLETE orders are returned normally with `status: COMPLETE` — the agent must not treat them as open. |

### 18. `get_order_status` — Retrieval (Step 2 addition, 2026-10-20)

| | |
|---|---|
| **Input** | Optional `order_id`, `customer`, `product`, `status`; at least one identifier/description is required. Provided filters must all match. |
| **Output** | Validated `status_facts`: ID, status/stage, due date, completion date, dataset date, timing direction and calendar-day count, unavailable fields; source-row evidence. |
| **Purpose** | Complete order-status answers rendered by code, including deadline and timing. See `STEP2_ORDER_STATUS.md`. |
| **Resolution** | Descriptions prefer open matches when status is unspecified, matching the existing convention. Multiple matches require clarification; no urgency-based selection. |
| **Failure modes** | Missing/invalid dates or stage are disclosed. No match → request an identifier. Ambiguity → real candidates. Completed orders use their completion date, never current overdue time. |
| **Scope** | Status-only replies and order/time lookup support. Other analytical/action tools retain the general response path; model routing needs live evaluation. |

### 3. `find_orders` — Retrieval

| | |
|---|---|
| **Input** | Optional filters: `customer`, `product`, `category`, `status`, `stage`, `due_from`, `due_to`, `ordered_from`, `ordered_to`, `overdue: bool`, `min_idle_working_days: int`, `min_pieces`, `max_pieces`; `sort_by` (due_date / pieces / idle / days_late); `limit` (default 10, max 50); `expect_single: bool` |
| **Output** | `total_matches: int`, `orders: list[summary row]`, `matched_as: {field: value}`, `truncated: bool` |
| **Purpose** | Find the orders that match what the manager described. |
| **Non-goals** | No aggregation beyond the match count (→ `summarize_orders`); no free-form SQL; no fuzzy semantic search over notes. |
| **Failure modes** | `expect_single=true` and >1 match → `AMBIGUOUS` with candidates sorted by urgency. 0 matches → `ok` with empty list plus `warnings` listing which filter eliminated everything. Truncation is always flagged so the model cannot claim "these are all of them". |

### 4. `summarize_orders` — Retrieval

| | |
|---|---|
| **Input** | `group_by`: none / customer / product / category / stage / status / order_month / due_week; `metrics`: subset of {count, pieces_sum, avg_days_late, median_days_late, late_rate, overdue_count}; same filters as `find_orders` |
| **Output** | Table of groups × metrics, plus overall totals; each cell has an evidence ID listing contributing orders |
| **Purpose** | Every aggregate question about orders, computed exactly. |
| **Non-goals** | No production-log metrics (→ `get_stage_output`); no forecasting; no joins beyond orders. |
| **Failure modes** | `avg_days_late` on in-progress orders is undefined (no completion) → excluded and stated in `warnings`. Empty groups are omitted, not zero-filled. |

### 5. `get_stage_output` — Retrieval

| | |
|---|---|
| **Input** | `stage` (one / all), `date_from`, `date_to`, `granularity`: day / week |
| **Output** | Rows of (period, stage, pieces); totals; `working_days` count; Sundays flagged |
| **Purpose** | Raw factory output facts. |
| **Non-goals** | Does not say whether output is normal (→ `compare_to_normal`); not per order (data is factory-wide). |
| **Failure modes** | Range outside the log → `INVALID_ARGUMENT` with available range. Weekly totals over partial weeks are labelled partial. |

### 6. `get_workshops` — Retrieval

| | |
|---|---|
| **Input** | Optional: `makes` (TOPS / ACCESSORIES), `status`, `name_or_id`, `max_queue_days` |
| **Output** | Profile cards: capacity/day, pickup lead days, defect rate, cost/piece, makes, status, batch cap, current queue days, notes |
| **Purpose** | What outside capacity exists and on what terms. |
| **Non-goals** | No allocation or recommendation (Track 2's job); no delivery estimate (→ `estimate_feasibility`). |
| **Failure modes** | Suspended workshops are returned only if asked for (or `status=any`) and are always labelled; the agent must not present them as available. |

### 7. `get_activity` — Retrieval

| | |
|---|---|
| **Input** | Optional: `order_id`, `kind` (note / message / watch / alert / action), `since`, `include_pending: bool` |
| **Output** | Audit-log entries, notes, outbox messages, watches (active / fired / expired), pending proposals |
| **Purpose** | The co-pilot's own memory of what was done, said, and set up — "what did I ask you to do?" |
| **Non-goals** | No conversation transcripts; nothing outside this system. |
| **Failure modes** | Empty result is an answer ("no notes on ORD-120"), not an error. |

### 8. `describe_data_coverage` — Retrieval

| | |
|---|---|
| **Input** | `topic: str` (free text, e.g. "revenue", "worker names", "machine breakdowns") |
| **Output** | `covered: bool`, `closest_available: list` (e.g. "workshop cost_per_piece exists; order prices do not"), `tables`, `date_range` |
| **Purpose** | Back an honest refusal with a checkable statement of what the data holds. |
| **Non-goals** | Does not answer the question itself. |
| **Failure modes** | Topic not in its catalogue → `covered: unknown`; the agent must then say it is not sure rather than guess. The catalogue is a static, reviewed list. |

### 9. `compare_to_normal` — Judgement

| | |
|---|---|
| **Input** | `stage` (one / all), `date` (default: last working day), optional `value` (to judge a number the manager quotes) |
| **Output** | `actual`, `baseline_median`, `robust_sigma`, `z`, `pct_vs_baseline`, `tier`: normal / briefing / interrupt, `consecutive_low_days`, `window: [dates]` |
| **Definition returned** | Baseline = median of the previous 20 working days (Sundays excluded); σ = 1.4826 × MAD; briefing tier z < −1.75; interrupt tier z < −3 or 2 of the last 3 working days z < −2 (`analysis/threshold_backtest.py`). Upward deviations are reported, not alerted. |
| **Purpose** | Make "is this normal?" an auditable rule instead of a model's opinion. |
| **Non-goals** | Does not explain causes; does not judge orders. |
| **Failure modes** | Sunday → returns "factory closed", never "0 is abnormal". Fewer than 20 prior working days → shorter window with a warning. A quoted `value` with no date → judged against the latest baseline and labelled so. |

### 10. `assess_order_risk` — Judgement

| | |
|---|---|
| **Input** | `order_id` or `scope: all_open` (with optional filters) |
| **Output** | Per order: `risk`: OVERDUE / AT_RISK / WATCH / OK, plus a `quiet` flag; `projected_finish` (P50 and P80), `slack_days`, `reasons: list` with the numbers used |
| **Definition returned** | OVERDUE: due date < today and not complete. QUIET: no activity for ≥ 3 working days (in-progress idle is 0–2 working days for 32 of 34 orders; the other two are 7 and 8; v1, see §7.1). AT_RISK (likely late): P50 projected finish (order date + log-linear size model, §7.2) > due date. WATCH (could slip): only the P80 finish > due date. A P80-only rule flags 16 of the 26 non-overdue open orders and had 48% precision in the backtest, so it is reported as a softer level. |
| **Purpose** | One consistent, inspectable definition of "at risk" used by answers, briefing and alerts. |
| **Non-goals** | No action; no blame or cause attribution; no per-stage schedule (the data has no stage history). |
| **Failure modes** | COMPLETE order → returns `risk: none (complete)` with the completion date. The projection is an estimate: the output always carries its P50/P80 interval and assumptions. |

### 11. `get_evidence` — Tracing

| | |
|---|---|
| **Input** | `evidence_id` (one or several) |
| **Output** | The source rows (table, columns, values) and the operation that produced the figure (e.g. "count of 6 rows where customer = TrendCart AND status = IN_PROGRESS") |
| **Purpose** | "Why?" goes back to the data, not to a paraphrase of the last reply. The UI also calls this directly when a number is clicked. |
| **Non-goals** | No summarising or re-interpretation. |
| **Failure modes** | Evidence from an earlier turn whose data has since changed (clock advanced) → returned with `stale: true` and the current values alongside. |

### 12. `scan_exceptions` — Discovery

| | |
|---|---|
| **Input** | `as_of` (runtime), `top_k` (default 5), optional `kinds` filter |
| **Output** | Ranked findings: `kind`, `title`, `score`, `severity`, `urgency`, `breadth`, `entities`, `evidence`; plus `suppressed_count` |
| **Detectors** | (a) stage output anomaly (via `compare_to_normal`); (b) newly / severely overdue orders; (c) quiet orders; (d) customer cluster — ≥ 2 open orders of one customer at risk, or completed-order late rate far above the others; (e) WIP pile-up — open pieces waiting at a stage vs its recent output; (f) due soon and at risk (due within 5 working days, AT_RISK) |
| **Ranking** | `score = severity × urgency × breadth`, each in [0, 1], with stated formulas (severity: z or days overdue scaled; urgency: working days to due / since onset; breadth: pieces or orders affected relative to total open). Dedupe: a customer-cluster finding absorbs its member orders; a stage anomaly absorbs the WIP pile-up at that stage. Weights tuned on the dev set only. |
| **Purpose** | Find what nobody asked about, and keep the page to five items. |
| **Non-goals** | No prose (the briefing narrates); no cause attribution. |
| **Failure modes** | Ranking misorders findings (measured: briefing recall/precision on the known-signal list). Correlated detectors double-count (mitigated by dedupe rules, tested). |

### 13. `estimate_feasibility` — Feasibility

| | |
|---|---|
| **Input** | `product` or `category`, `pieces`, optional `due_date` (already resolved; omit for "which workshop gets them back first?" or "what would N cost at a workshop?"), optional `start_date` (default today) |
| **Output** | `in_house`: P50 / P80 finish dates, `meets_due_p50/p80`, load index; `outsourcing`: per eligible workshop — finish date = start + queue days + ⌈pieces / capacity⌉ + pickup lead days, batch-cap handling (split count), cost = pieces × cost/piece, defect rate; `verdict`: comfortable / tight / not without outsourcing / not feasible, or "no deadline given" (options ranked by earliest finish); `fastest_eligible_workshop`, `earliest_finish`; `assumptions: list`; `excluded_workshops` with reasons |
| **Method** | In-house: P50 / P80 finish = start + cycle from the log-linear size model (§7.2); current load and any stage slowdown are reported as risk factors, not multiplied in (backtest showed scaling hurts). Outsourcing: the queue + processing + transport rule from the workshop cards; ineligible (wrong category, SUSPENDED, over batch cap without split) excluded with the reason. |
| **Purpose** | Give the manager an estimate with explicit assumptions — never a bare "yes". |
| **Non-goals** | Does not accept the order, reserve capacity, or allocate to a workshop. |
| **Failure modes** | Model error on unusual sizes (outside the reference range 100–2,000 pcs) → widened interval + warning. Due date in the past or on a Sunday → flagged. Product not made in-house / by any workshop → `OUT_OF_COVERAGE`. |

### 14. `propose_message` — Action

| | |
|---|---|
| **Input** | `order_id` (or `workshop_id`), `recipient_role` (planner / floor supervisor / workshop / customer-service), `intent` (chase / inform / ask), `extra_instructions` |
| **Output** | `proposal_id`, draft text (facts filled from tools, wording by the model), `facts_used` with evidence |
| **Purpose** | Draft the chase-up the manager would otherwise dictate. |
| **Non-goals** | Never sends. No external recipients: messages land in the in-app outbox. |
| **Blast radius** | Worst case: a wrong or badly-worded draft in the outbox. Stopped by: explicit confirm, draft visible before confirm, editable, undo (retract) after. |
| **Failure modes** | Facts in the draft not in tool results → blocked by the verifier. Proposal on a COMPLETE order → `PRECONDITION_FAILED` unless intent is `inform`. |

### 15. `propose_note` — Action

| | |
|---|---|
| **Input** | `order_id`, `text` |
| **Output** | `proposal_id`, preview |
| **Purpose** | Attach the manager's information to an order. |
| **Non-goals** | Never modifies order fields (status, stage, dates). |
| **Blast radius** | A wrong note on an order. Confirm before; audit log; soft-delete undo. |
| **Failure modes** | Wrong order resolved from an ambiguous reference → prevented upstream (`AMBIGUOUS`), and the order ID is shown on the confirm card. |

### 16. `propose_watch` — Action

| | |
|---|---|
| **Input** | `type`: `order_stage_unchanged(order_id, by)` · `order_not_complete(order_id, by)` · `stage_below_normal(stage, tier)` · `reminder(at, text, condition?)`; `expires_at` (default 14 days); `priority` (interrupt / briefing) |
| **Output** | `proposal_id`, plain-language restatement ("I'll alert you on Thu 2 Apr 07:00 if ORD-120 is still in ASSEMBLY"), next evaluation time |
| **Purpose** | Turn "tell me if…" into a standing check that fires on its own. |
| **Non-goals** | No arbitrary conditions or code; no watches on data the system does not have. |
| **Blast radius** | Worst case: an unwanted or missed alert. Confirm before; restatement shown; expiry; cancel any time. |
| **Failure modes** | Watch on a COMPLETE order (e.g. ORD-058) → `PRECONDITION_FAILED`: "ORD-058 was completed on 2026-03-12". Deadline already passed → rejected with explanation. Duplicate of an active watch → returns the existing one. |

### 17. `propose_cancel_watch` — Action

| | |
|---|---|
| **Input** | `watch_id` or description resolved via `get_activity` |
| **Output** | `proposal_id`, the watch to be cancelled |
| **Purpose / non-goals** | Cancel a standing check; does not delete its history. |
| **Blast radius** | A wanted alert stops. Confirm before; reversible (re-activate). |

The manager can also cancel an active watch from the Watches page (`POST /api/watches/{id}/cancel`): their click
is the confirmation, so the same `cancel_watch` action is recorded and executed in one step — audited and undoable.

### 19. `propose_outsourcing` — Action (demo-feedback addition, 2026-10-29)

| | |
|---|---|
| **Input** | `workshop` (name or id), `pieces`, `product` or `category`, optional `due_date` (resolved), optional `order_id` (only if the manager named one) |
| **Output** | `proposal_id`, preview, and the chosen workshop's `finish_date`, `meets_due`, `cost`, `cost_per_piece`, `defect_rate_pct` — computed by `estimate_feasibility`, whose evidence it cites |
| **Purpose / non-goals** | Turn "draft / arrange an outsourcing order" into an action instead of prose. Does not book anything or contact a workshop; a confirmed request goes to the outbox (`intent = outsource`). |
| **Failure modes** | Unknown workshop → `NOT_FOUND` (candidates: all workshops); workshop cannot take the batch (wrong category, SUSPENDED, over batch cap) → `PRECONDITION_FAILED` with the eligible workshops as candidates; unknown order → `NOT_FOUND`. A late return is allowed but warned. |
| **Blast radius** | A wrong request in the outbox. Confirm before; undo retracts it. |

---

## 5. Boundaries between tools (why they are split this way)

- **`find_orders` vs `summarize_orders`**: listing vs aggregating. Merging them invites the model to count a
  truncated list itself.
- **`get_stage_output` vs `compare_to_normal`**: facts vs judgement. A judgement must carry its definition;
  a fact must not carry an opinion.
- **`assess_order_risk` vs `scan_exceptions`**: one definition of risk per order vs ranking across all kinds
  of findings. The scanner calls the risk tool, so "at risk" means the same thing everywhere.
- **`estimate_feasibility` is one tool, not a plan of five calls**: the calculation has a fixed structure; letting
  the model orchestrate it would move arithmetic into the model.
- **Action tools only propose**: confirmation and execution are outside the model's reach by construction.

## 6. Data limitations every tool must respect

- No prices, revenue, margins, worker names, machines, or stage-transition history.
- Workshop `cost_per_piece` exists → subcontracting cost is answerable; order profitability is not.
- **The production log and the orders table are not on the same scale.** Orders arrive at ~7,300 pcs/week
  and complete with a median cycle of 24 days (order-level throughput ≈ 7,900 pcs/week by Little's law),
  while the log's PACKING output is ~3,900 pcs/week. So "open pieces ÷ stage output" (≈ 50 working days)
  contradicts observed cycle times. Consequence: the production log is used for **relative** signals
  (is a stage slower than its own normal?), and order-level timing comes from order history. Stated in
  `warnings` where relevant and in Documentation.
- `last_activity_date` = 2026-04-01 on some orders while the log ends 2026-03-31 → treated as activity
  recorded this morning.
- Open pieces now: 32,850 (34 orders) — above the typical 25,000–30,000 of Feb–Mar.

## 7. Open definitions — settled by backtest

### 7.1 QUIET threshold
v1: ≥ 3 working days idle (gap in the current distribution). Weakness: one snapshot, no activity history.
Check: sensitivity of the briefing to k = 2, 3, 4; with the data advancer, measure on simulated days.

### 7.2 Completion projection (used by `assess_order_risk` and `estimate_feasibility`) — **settled**
Walk-forward backtest (`analysis/projection_backtest.py` → `analysis/results/projection_backtest.md`):
each completed order predicted only from orders completed before it was placed; 34 evaluable orders.

| Model | MAE (days) | 95% CI | Bias | P80 coverage | MAE 1st/2nd half |
|---|---|---|---|---|---|
| A plan (due date) | 6.94 | 5.2–8.8 | +1.71 | 62% | 6.8 / 7.1 |
| B global median | 5.97 | 4.6–7.5 | +0.62 | 74% | 5.5 / 6.4 |
| C size band | 5.31 | 4.1–6.7 | −1.22 | 65% | 5.6 / 5.0 |
| C + load scaling | 5.97 | 4.5–7.5 | −2.20 | 59% | 6.1 / 5.9 |
| **E log-linear size** | **4.58** | **3.6–5.6** | **+0.12** | **76%** | **4.4 / 4.8** |

**Chosen: E** — `log(cycle) = a + b·log(pieces)`, P50 = fitted value + median residual, P80 = + 80th-percentile
residual, refitted on all completed orders up to `as_of`. Best on every accuracy and stability measure,
~34% lower error than the plan baseline, and explainable in one sentence ("bigger orders take longer, at
a decreasing rate"). **Load scaling made forecasts worse** (bias −2.2 days, coverage 59%), so the current
load and the ASSEMBLY slowdown are reported as risk factors in `warnings`, not multiplied in.
Limitations: n = 34; P80 slightly under-covers (76%); no stage history, so an open order's projection is
conditioned on its order date, not its current stage — an order already past its P80 date is AT_RISK by
definition and its remaining time is reported as unknown rather than invented.

## 8. Change log

| Date | Change |
|---|---|
| 2026-10-08 | v1 draft |
| 2026-10-08 | §7.2 settled by backtest: log-linear size model; load scaling rejected |
| 2026-10-08 | Risk levels split: AT_RISK (P50 > due) vs WATCH (P80 > due only) |
| 2026-10-08 | Implemented with tests: resolve_time, get_order, find_orders, summarize_orders, get_stage_output, compare_to_normal |
| 2026-10-14 | All 17 tools implemented and tested against `eval/ground_truth/dev_truth.py`; strict JSON schemas (optional fields nullable, nulls dropped before the call); `compare_to_normal` rejects `value` together with `on_date`; `assess_order_risk` returns `total_open_orders` so the model never counts; `find_orders(expect_single)` resolves a single open match directly |
| 2026-10-29 | Demo feedback: `propose_outsourcing` (tool 19); manager cancels watches from the UI through the gateway; estimate answers' details are rendered from the `estimate_feasibility` result (`app/agent/feasibility_view.py`) so every estimate has one layout |
| 2026-10-15 | `get_workshops` and `estimate_feasibility` also return `defect_rate_pct` (display-ready, so the model never converts a fraction) |
| 2026-10-15 | `estimate_feasibility`: `due_date` optional (fastest workshop and subcontract cost without a deadline) — found by dev items D23 and D36; `scan_exceptions` overdue text states the total pieces separately from the most overdue order |
