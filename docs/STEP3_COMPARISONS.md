# Step 3: comparison replies

Step 3 of the [evaluation plan](EVAL_PLAN.md), implemented on commit `5f5b43e` (system prompt v10), with the live
gate run on `8a662e9` (the same system plus the gate runner). Development cases only; no held-out question was
opened.

## The problem

D35 asks "why did assembly drop on 25 March?". Across earlier runs the reply once stated 394 against a median of
766.5 without saying how large the drop was. The verifier could not catch that: it checks that what is said is
supported, not that everything needed is said. The route also had two gaps of its own:

- The `compare_to_normal` evidence held only the baseline window, so the observed row (for example 455 pieces on
  31 March) could not be traced from the answer's source chip.
- A question about a period ("average assembly output over 25–31 March") had no tool support, so the model was left
  to average daily figures itself, against invariant 1.

## Behavior

When a turn holds exactly one successful comparison of one stage, the runtime builds the reply from the tool fields
(`app/agent/comparison_view.py`). For D35, the answer is:

> Assembly output was 394 pieces on 2026-03-25, 48.6% below baseline. Judged not normal: interrupt tier, z = -9.48.
> The baseline was the median of 20 working days from 2026-03-02 to 2026-03-24: 766.5 pieces/day. The cause is
> unknown from these data.

A cause question has kind `refuse`, because the cause is what the data cannot give, and the observation is still
stated in full. Any other comparison has kind `answer`.

`compare_to_normal` changes:

- `through_date` compares the mean per working day of a period with the 20 working days before it. Sundays inside
  the period are not counted. A period with a missing working day gets a warning and no mean, because a missing day
  is not a zero.
- Results carry `statistic` (daily, mean or quoted), `start`, `end` and `observed_days`.
- `actual`, `baseline_median`, `pct_vs_baseline` and `tier` can be null. A zero or absent baseline gives "Percentage
  change cannot be computed", never a division by zero. A missing day says the output is unavailable.
- Evidence rows carry `role: baseline | observed`, so every figure expands to the rows behind it.

## Which questions the renderer owns

The renderer takes the turn only if all of these hold:

- the draft is an `answer`, or a `refuse` to a cause question;
- there is one successful `compare_to_normal` call with one result, and it is not a quoted hypothetical value;
- every other tool in the turn is a support tool (`resolve_time`, `describe_data_coverage`, `get_stage_output`).

`reject` and `propose` are never overridden; step 14 of the [journal](JOURNAL.md) shows why. Comparisons across all
stages, compound questions and "is 800 normal?" keep the general path. The rendered reply still passes the verifier.

## Results

| Check | Result |
|---|---|
| Offline (scripted model): D35 and P01–P12, three runs each, through the contract checker | all pass (`backend/tests/test_comparison.py`) |
| Live gate: the same 13 cases, three runs each | **39/39**, all routed to `compare_to_normal` |
| Live gate: of those, questions asked as written | 21/21 |
| Live gate: of those, synthetic edge cases | 18/18 |
| Unconfirmed executions in the gate | 0 |
| Gate latency p50 / p90, total cost | 5.3 s / 6.8 s, $0.023 |
| Full live regression on `5f5b43e`, two runs per set | dev 36/36 twice, red team 12/12 twice, faithfulness 100%, 0 unconfirmed |

Every attempt, reply and failure code is in `eval/results/step3/live-v1/`. To repeat the gate from the repository
root (about $0.03):

```sh
uv run --project backend python eval/run_step3.py --output-dir eval/results/step3/<new-dir>
```

The cases are in `eval/fixtures/answer_contracts.json`. They cover daily and period comparisons, all four stages, a
range spanning a Sunday, and P07–P12: zero baseline, missing baseline, an increase, no change, a missing observation
and zero output.

## Limits

- **These are development numbers.** Prompt v10 and the renderer were written with these cases in view, so 39/39
  shows the contract holds on them. It does not predict unseen questions.
- **The checker is bounded.** `eval/answer_contracts.py` checks the required facts and rejects unrecognised claims.
  It does not judge quality; that is Step 4.
- **Synthetic cases use a changed question.** The fixture questions for P07–P12 name no stage or date, so the live
  model is asked "Compare assembly output on 2026-03-25 with its previous 20 working days." on a changed in-memory
  database. They test rendering under real routing, not whether the model understands the original wording.
- **No live baseline comparison.** Unlike Step 2, the previous version was not re-run on these cases. The earlier
  failure is D35's one recorded miss, so an improvement in rate is not claimed from this gate.
- **Routing stays with the model.** The renderer guarantees completeness once the route is chosen and data is
  retrieved. Questions routed elsewhere keep the general path.
- **Period comparisons carry no verdict.** The robust-z rule is defined for one day, so a period gets a percentage
  against the baseline and no tier.
- **The cause sentence is on every comparison.** "The cause is unknown from these data." follows the contract, so it
  also appears on normal days, where it reads oddly. Removing it there means changing the contract and fixtures P03
  and P05; it is left as a team decision.

## Also in this build

The briefing summary is now written on schedule. A background check writes the day's prose after the structured
briefing exists, however the day arrived (start-up, the 07:00 boundary or a clock jump). A rejected or failed summary
is not retried, so it cannot keep spending, and the structured briefing stands.
