# Step 3: comparison replies

Step 3 of the [evaluation plan](EVAL_PLAN.md), on system prompt v10. Development cases only; no held-out question was
opened. Two implementations of this step were built: the one described here, and one by Zihao Zeng
(`get_production_change`). We kept this one because it needs no second tool for the same question, and used his cases,
independent references and scorer to cross-check it, which found a real defect (below). His results are in
[`eval/results/step3-production-change/`](../eval/results/step3-production-change/README.md).

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

> Assembly output was 394 pieces on 2026-03-25, 48.6% below baseline.
> The baseline was the median of 20 working days from 2026-03-02 to 2026-03-24: 766.5 pieces/day. The cause is
> unknown from these data.

A cause question has kind `refuse`, because the cause is what the data cannot give, and the observation is still
stated in full. Any other comparison has kind `answer`. A question about normality also gets the verdict:

> Assembly output was 455 pieces on 2026-03-31, 40.2% below baseline. Judged not normal: z = -6.26 against the usual
> spread (interrupt tier), 6 low working days in a row.

`compare_to_normal` changes:

- `through_date` compares the mean per working day of a period with the 20 working days before it. Sundays inside
  the period are not counted. A period with a missing working day gets a warning and no mean, because a missing day
  is not a zero.
- A working day missing from the baseline window gives no baseline, no percentage and no verdict. The window does not
  move further back. A log that simply starts later keeps the disclosed shorter window. The alert and briefing paths
  still use the existing window rule; the seeded data has no such gaps.
- Results carry `statistic` (daily, mean or quoted), `start`, `end` and `observed_days`.
- `actual`, `baseline_median`, `pct_vs_baseline` and `tier` can be null. A zero or absent baseline gives "Percentage
  change cannot be computed", never a division by zero. A missing day says the output is unavailable.
- Evidence rows carry `role: baseline | observed`, so every figure expands to the rows behind it.

## Which questions the renderer owns

The renderer takes the turn only if all of these hold:

- the draft is an `answer`, or a `refuse` of a cause question or of a comparison with data missing from it;
- there is one successful `compare_to_normal` call with one result, and it is not a quoted hypothetical value;
- every other tool in the turn is a support tool (`resolve_time`, `describe_data_coverage`, `get_stage_output`).

`reject` and `propose` are never overridden; step 14 of the [journal](JOURNAL.md) shows why. Comparisons across all
stages, compound questions and "is 800 normal?" keep the general path. The rendered reply still passes the verifier.

## Results

The current build is commit `3600933`. Every attempt, reply and failure code is kept in `eval/results/step3/`.

| Check | Build | Result |
|---|---|---|
| Our cases: D35 and twelve variations, three runs each (`live-*`) | `8a662e9`, `123fe55`, `3600933` | 39/39 each |
| Independent cases and references, three runs each (`independent-*`) | `f678d70`, before the fixes | **29/33; hard checks 27/33** |
| The same | `123fe55`, hole fixed | 33/33; hard checks 33/33 |
| The same | `3600933`, current | **33/33; hard checks 33/33** |
| Independent judge on one real reply per case (`../step4/real-replies-*`) | `123fe55` | **7/13** |
| The same | `3600933`, current | **13/13** |
| Full regression, two runs per set | `3600933` | dev 36/36 twice, red team 12/12 twice, faithfulness 100%, 0 unconfirmed |

No action was executed in any gate. A gate costs about $0.02 and runs at about 5.5 s p50.

What the independent checks found, none of which our own 39/39 had shown:

- **A hole in the baseline window (P08), a defect in the tool.** With one day missing, the window silently moved a
  day back and still produced a percentage and a verdict. Fixed in the tool, and the scorer passes it now.
- **A refusal could bypass the renderer (P09).** Once in three, the model refused a period with a missing day, so the
  reply left out the baseline. A refusal caused by missing data now gets the known facts.
- **The verdict sentence (6 of 13).** The judge failed correct z-scores that its reference package did not contain
  and called the wording unclear. It was right on the second point: a factory manager had not asked for a z-score.
  The verdict now appears only for a question about normality, in plainer words.
- **One scorer false rejection (P09).** The scorer asked for a mean's statistic and unit when no mean exists. We
  changed the rule, not the reply.

To repeat from the repository root:

```sh
uv run --project backend python eval/run_step3.py --output-dir eval/results/step3/<new-dir>
uv run --project backend python eval/run_step3.py --suite production --output-dir eval/results/step3/<new-dir>
uv run --project backend python eval/judge_real_replies.py --replies <run>/results.jsonl --output <new-file>.jsonl
```

## Limits

- **These are development numbers.** The renderer and prompt v10 were written with these cases in view, and the
  fixes above were made after seeing the independent results, so those cases are now development material too. None of
  this predicts unseen questions.
- **The judge is not calibrated.** No person has labelled its decisions yet, so 13/13 means only that it finds nothing
  to object to in these replies.
- **The judge can only check its package.** It failed true statements the package omitted, and removing the sentence
  from comparisons does not solve this for other answers. See the rubric's review rule.
- **Our checks favour our wording.** The hard patterns came from the same contract as the renderer. In a smoke test
  the Step 1 build's "Assembly output on 2026-03-25 was 394 pieces" is correct and still unrecognised. So a baseline
  comparison needs its hard failures reviewed by a person, as the rubric requires.
- **Synthetic cases in our own gate use a changed question**, because those fixtures name no stage or date. The
  independent suite asks its questions as written.
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
