# Design notes — why GM Co-Pilot is built the way it is

Each decision below records **what we chose, the alternatives, and the evidence** — from the literature, from a
backtest on the factory's own data, or from an evaluation run. The engineering journal
([JOURNAL.md](JOURNAL.md)) tells the same story in the order it happened.

## 1. The problem

The general manager of a quick-response knitwear factory runs 120 orders through four stages
(KNITTING → ASSEMBLY → WASHING → PACKING), with eight outside workshops for overflow. Through the day the
manager asks questions that today cost a call to a planner and a wait:

| When | Question | What a good answer needs |
|---|---|---|
| 07:00 | "Did anything go wrong yesterday?" | A judgement of *normal*, not just a number |
| all day | "How is the TrendCart order doing?" | Noticing that TrendCart has six open orders — and asking which |
| on request | "A customer wants 800 hoodies by the 25th. Can we take it?" | An estimate with its assumptions, never a bare yes |
| standing | "Tell me if ORD-120 hasn't moved by Friday." | Something that fires on its own, later |
| on confirm | "Chase it up." | An action the manager approves before it happens |

The data is three small CSVs (orders, a 90-day production log, workshop cards). It has **no prices, revenue,
worker names or causes of delays** — so some questions must be refused honestly — but it does have workshop
costs, so others that sound similar can be answered.

**The worst failure is a confident wrong number.** The most common source of wrong numbers in LLM systems is the
model doing arithmetic or "remembering" a figure. Everything below follows from taking that seriously.

## 2. Principles

1. **Tools compute, the model narrates.** Every count, sum, date difference and percentage comes from a typed
   tool. The model chooses tools and words, nothing else.
2. **Every number is traceable.** A reply is *grounded* iff every number, date and ID in it appears in this
   turn's tool outputs (Definition 1). A deterministic verifier enforces it before anything is shown, and each
   figure links to the rows behind it.
3. **Ask, don't guess; refuse honestly.** Ambiguous references become a clarifying question with options; a
   question the data cannot answer gets a plain "the data doesn't contain that" plus what it does contain.
4. **The model can only propose.** Chase-ups, notes, watches and outsourcing requests are proposals. Only the
   manager's click executes them — deterministically, audited, undoable, into an outbox rather than a real
   channel.
5. **Deterministic work is code.** The morning briefing, watch evaluation and action execution are code on a
   clock, not prompts.

## 3. Architecture

![Architecture](figures/fig1_architecture.png)

One **ReAct** agent (Yao et al., 2023) runs a tool loop of at most six steps and ends every turn with a
structured `respond` call (answer · estimate · clarify · refuse · propose · reject). A **verifier** in plain code
checks the reply; one repair attempt is allowed, after which the user sees the raw tool output instead of an
unverified sentence. For two question types the reply body is rendered from validated tool fields rather than
model prose (order status and feasibility estimates), so a fact the tools returned cannot be dropped.

## 4. Key decisions and their evidence

| Decision | Alternatives considered | Evidence |
|---|---|---|
| **Narrow typed tools (19), no free SQL** | Text-to-SQL over the CSVs | An honest "I can't answer that" beats a hallucinated join; every tool result carries evidence IDs. Each tool is unit-tested against an independent pandas computation |
| **Code verifier, not LLM self-review**, in the answer path | LLM critic reviewing every draft | Self-correction without external feedback is unreliable (Huang et al., ICLR 2024). Our ablation: a critic added **+1.4 points** on dev for **63% more cost and doubled p90 latency** — below the +5 we required in advance, so it is an off-by-default switch |
| **"Normal" = robust z vs the trailing 20 working days** (median, 1.4826·MAD), two tiers: briefing `z < −1.75`, interrupt `z < −3` or 2-of-3 days `z < −2` | Fixed % drops; same-weekday medians; Shewhart 3σ; modified z < −3.5 | Threshold backtest with 400 injected drops per cell: the briefing tier keeps **88% recall of a 20% drop at 0.37 false alerts/week**; a −15% rule fires 0.86–1.59/week; 3σ rules catch 9–29%. The interrupt tier raised **no false alert in 80 clean days**. No weekday effect (Kruskal–Wallis p ≥ 0.53) ([analysis](../analysis/results/threshold_backtest.md)) |
| **Completion forecast = log-linear size model** (P50/P80 from residual quantiles) | Promised due date; global median; size bands; scaling by current load | Walk-forward over 34 orders: **MAE 4.6 days vs 6.9 for promised dates**, bias +0.1, P80 coverage 76%; load scaling made it worse ([analysis](../analysis/results/projection_backtest.md)) |
| Risk levels: AT_RISK when P50 > due; WATCH when only P80 > due | Flag on P80 | Flagging on P80 alone marks 16 of 26 non-overdue orders, 48% precision |
| Production log used only for **relative** signals | Use it for capacity | The log and the order book differ ≈ 2× in scale |
| Relative dates resolved by code (`resolve_time`, a computed calendar) | Let the model work out "Friday" | Date arithmetic is arithmetic |
| **Proposals + confirm gateway** for every side effect | Let the agent call actions | Bounded blast radius; red team: **0 of 12 attack prompts** executed anything (advance consent, typing "CONFIRM", injected instructions) |
| Simulated clock + seeded data advancer + scenarios; jump to any time, rewind by deterministic replay | Static data | Alerts and watches need days to pass. Each day is seeded by (scenario, date), so a rewind replays identically (tested row for row) |
| Daily LLM budget, access code, per-visitor rate limit; resets never touch the spend record | Open demo | A public link costs money per question; a reset that wiped spend would lift the cap |
| Every AI step traced (plan, tool, arguments, draft, verifier verdict, cost, latency) | Logs only on error | The manager and the team can see exactly why an answer is what it is |

## 5. Evaluation design

Two scores per item: **decision** (right behaviour and every required fact, no forbidden claim) and
**faithfulness** (every figure passed the verifier). Three sets: 36 dev questions whose answers are computed by
pandas from the CSVs, 12 red-team attacks on actions, and a held-out set written separately by the team and run
once. Scoring rules are code with unit tests; any correction is re-applied to every run and disclosed in
[eval/results](../eval/results/README.md). Method: [EVAL_PLAN.md](EVAL_PLAN.md).

## 6. Known limitations

- Dev scores are tuning scores: prompts were adjusted after reading dev failures. The held-out set is the test.
- A reply can still leave out a fact the tools returned (e.g. the size of a drop); the verifier checks that what
  is said is supported, not that everything relevant is said. Two question types are protected by rendering.
- Spelled-out numbers ("six") are not extracted by the verifier.
- The data has no causes, prices or people, so "why did assembly drop?" can only be answered with what happened.
- One model provider has been measured so far.
