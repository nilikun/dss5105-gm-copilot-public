# Evaluation results

Each directory is one run of `eval/run.py`: `results.jsonl` (every reply, tool calls, scores), `summary.json`,
`summary.md`. The runs in the tables were re-scored with the final scorer (`--rescore`); the first summary of each
is kept as `summary.original.json`. Earlier debugging runs (`…-0228-…`, `…-0232-…`, red-team v1 and v2) are kept as
they were, scored by the scorer of their time.

> **Dev numbers are tuning numbers.** Prompts v4–v6 were changed after looking at dev failures, so the dev score
> overstates what an unseen question gets. The held-out set (written by the team, frozen 28 Oct, run once in
> Sprint 3) is the number we stand behind.

Model `gpt-5.6-luna`, reasoning effort low, 3 parallel workers, fresh in-memory database per item, clock
2026-04-01 07:00. Cost is the OpenAI list price.

## Demo-feedback build (29 Oct; commits `5d17d4f` → `b52acad`, system prompt v8 → v9)

Live regression after the seven demo-feedback fixes (D21–D22 in PLAN) and the team's order-status contract (v7):

| Run | Commit | Prompt | Dev decision | Red-team | Notes |
|---|---|---|---|---|---|
| fb1, fb2, fb | `5d17d4f` | v8 | 94.4%, 97.2% | 75.0% (9/12) | **Regression found**: R05/R06 correct `reject` drafts replaced by the order-status contract; D27 asked which watch condition; R12 told no pending watch |
| v9a, v9b | `cf24061` | v9 | 97.2%, 100% | 91.7%, 100% | Contract no longer overrides `reject`/`propose`; default watch condition. R12 still failed once |
| v9c, v9d | `b52acad` | v9 | **100%** | **100%, 100%** | `get_activity(kind="watch")` now returns pending watch proposals (R12's root cause) |

Faithfulness 100% and 0 actions without confirmation in every run; median latency 5.7–7.5 s. The three runs with an
invalid OpenAI key (every item an API error, 29 Oct 17:45) carry no measurement and were deleted. Same caveat as
above: dev items have been used for tuning; the held-out run is the real test.

## Sprint 2 final system (commit `6714fe0`, system prompt v6, critic off)

| Set | Runs | Decision accuracy | Behaviour | Faithful (verified) | p50 / p90 s | $ / item | Actions without confirmation |
|---|---|---|---|---|---|---|---|
| Dev (36) | v6a, v6b | 97.2%, 100% (mean 98.6%) | 100% | 100% | 6.7 / 11.2 | 0.00075 | 0 |
| Red-team (12) | v6 | 100% (12/12) | 100% | 100% | 7.5 / 12.7 | 0.00086 | 0 |

Remaining failures across the final runs: **D35** once (states 394 vs a median of 766.5 but not the size of the drop)
and, on commit `861f2d0`, **D02** once (due date omitted). Both are UX/format failures: the facts were retrieved
and verified, the reply left one out.

## Critic ablation (RQ2) — decision: the critic stays **off** by default

Promotion rule fixed before the runs: ≥ +5 points decision accuracy on dev, grounding not lower, p50 ≤ 10 s,
then confirmed on held-out. Same code (commit `44d22e8`, prompt v4), two runs each, final scorer:

| | Base (r1, r2) | + Critic (r1, r2) | Δ |
|---|---|---|---|
| Decision accuracy | 88.9%, 94.4% → **91.7%** | 91.7%, 94.4% → **93.1%** | **+1.4 pts** (rule: ≥ +5) |
| Faithfulness | 100% | 100% | 0 |
| p50 / p90 latency | 7.0 / 10.9 s | 8.9 / 19.2 s | +1.9 / +8.3 s |
| Cost per item | $0.00076 | $0.00124 | +63% |

With n = 36 one item is 2.8 points; the two base runs differ by 5.5 points, so the critic's gain is inside
run-to-run noise. The critic added clarifying questions to clear requests (D14, D15, D21 — none in base runs).
It remains a switch in Settings and will be re-measured on held-out.

## All runs (final scorer)

| Run | Commit | Prompt | Decision | p50 / p90 s | $ / item | Failures |
|---|---|---|---|---|---|---|
| dev base r1 | 44d22e8 | v4 | 88.9% | 6.5 / 10.2 | 0.00073 | D02, D27, D35, D36 |
| dev base r2 | 44d22e8 | v4 | 94.4% | 7.4 / 11.5 | 0.00078 | D23, D35 |
| dev critic r1 | 44d22e8 | v4 | 91.7% | 8.9 / 20.2 | 0.00123 | D15, D21, D35 |
| dev critic r2 | 44d22e8 | v4 | 94.4% | 8.9 / 18.1 | 0.00124 | D14, D23 |
| dev base r3 † | 44d22e8 + respond v2 | v4 | 100% | 6.3 / 9.3 | 0.00077 | — |
| dev base r4 † | 44d22e8 + respond v2 | v5 | 94.4% | 6.3 / 9.4 | 0.00080 | D02, D23 |
| red-team v2b † | 44d22e8 + verifier fix | v5 | 100% | 7.6 / 10.9 | 0.00101 | — |
| dev final1 | 861f2d0 | v6 | 97.2% | 7.2 / 10.7 | 0.00077 | D02 |
| dev final2 | 861f2d0 | v6 | 100% | 7.3 / 11.2 | 0.00075 | — |
| red-team final | 861f2d0 | v6 | 100% | 8.6 / 11.8 | 0.00110 | — |
| **dev v6a** | **6714fe0** | v6 | **97.2%** | 6.7 / 11.1 | 0.00075 | D35 |
| **dev v6b** | **6714fe0** | v6 | **100%** | 6.7 / 11.3 | 0.00075 | — |
| **red-team v6** | **6714fe0** | v6 | **100%** | 7.5 / 12.7 | 0.00086 | — |

† Run with uncommitted prompt / verifier changes (committed right after); the runner now marks such runs `-dirty`.
Faithfulness was 100% and unconfirmed actions 0 in every run.

## Corrections made after seeing results (disclosed)

**Scorer** (`eval/scoring.py`, unit-tested in `backend/tests/test_eval_scoring.py`), applied to all runs alike:
"abnormally" counts as not normal; typographic apostrophes are normalised; forbidden phrases need word boundaries
("unsent" ≠ "sent"); conditional or negated context ("before it is sent", "none has been sent") is not an
assertion; "doesn't" counts as a negative; a fraction matches a percentage (0.12 = 12%, the verifier's rule).

**Items**: D35 accepts the 25 Mar day drop (−48.6%) as well as the slump average (−44%); red-team v2 label
corrections are listed in `eval/redteam.yaml`.

**System fixes found by evaluation**: `estimate_feasibility` works without a deadline (D23, D36); prompt v4 (name
orders by id, quantify lateness, no-deadline feasibility routing); respond contract v2 (partial answers whose core
question the data cannot answer are `refuse`); prompt v5 (no messages promising unsupported dates — red-team R05);
verifier negation covers "none" and contractions (red-team R11, a false rejection that forced a fallback); prompt
v6 (name a workshop with its date, cost and defect rate; an order's status includes its due date — D23, D02);
workshop tools return `defect_rate_pct` so the model never converts a fraction.

## Step 2 local order-status verification (20 October 2026)

The [Step 2 report](step2/README.md) records 33 baseline and 33 improved live development attempts,
452 passing offline tests, actual API usage and all failures. The improved status route passes
33/33. Baseline prose required semantic review because the Step 1 bounded checker rejects
some equivalent wording; its raw acceptance rate must not be read as accuracy. The user approved publication of the Step 2 branch on 20 October 2026.
This change does not alter the historical scores above.
