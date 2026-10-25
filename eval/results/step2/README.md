# Step 2: local verification results

The improved status route passes **33/33 live development cases** (D02 plus ten variations, three runs each).
**452 offline tests pass**, including 59 new checks. The user approved branch publication after reviewing these results on 20 October 2026.

The live model was `gpt-5.6-luna`, reasoning effort `low`, critic off, with a fresh in-memory database per case
and dataset clock `2026-04-01T07:00:00`. All 33 improved replies selected `get_order_status`.
The two suites ran concurrently, one sequential worker per version. Latencies include context turns.

## What changed

- A typed status tool resolves an order and computes timing from validated source dates.
- A deterministic response contains the same order’s ID, stage, deadline and calendar-day timing.
- Ambiguity requests a real candidate selection; missing/invalid dates retain known facts without guessed timing.
- Model prose and critic revisions cannot remove the facts on this route. The normal verifier still runs.
- Other analytical/action routes retain their behavior. D35 and independent held-out evaluation remain later steps.

## Results and interpretation

| Measure | Baseline | Step 2 |
|---|---:|---:|
| Core contract, assistant semantic review | 26/33 | 33/33 |
| D02 required facts in fresh live runs | 3/3 | 3/3 |
| Missing/invalid deadline cases: known stage retained, date unavailability disclosed | 0/6 | 6/6 |
| p50 / p90 elapsed seconds | 6.82 / 11.60 | 4.78 / 7.43 |
| Actual API calls, including context | 89 | 72 |
| Unconfirmed actions | 0 | 0 |

The intermittent D02 deadline omission did **not** recur in the three fresh baseline answers. It is not
valid to infer a measured D02 accuracy improvement from this sample. A regression test instead replays the
actual failed D02 prose from `20261015-2219-dev-gpt-5.6-luna-base-final1`; that prose omits the deadline,
and the new status route replaces it with the complete, correct response. Deliberately wrong dates,
stages and incomplete drafts are also replaced in controlled tests.

The baseline’s seven core-contract failures are S07 and S08 in all three runs (lost known stage after
a missing/invalid date caused retrieval failure), plus S06 run 2 (`reject` instead of clarification).
All raw replies, errors and traces remain in the run folders.

**Scoring limitation disclosed:** the frozen Step 1 checker accepted only 3/33 baseline answers.
That is **not baseline accuracy**. Its short-example grammar rejects valid free prose such as “overdue by
16 days”, “Due date: …”, extra last-activity dates, and lists of remaining stages. The source checker and
raw results were not changed after the run. `core-contract-review.json` records the coding assistant’s
semantic review for every reply, with excerpts and reasons. This is not independent human calibration
or a calibrated judge, and it evaluates the core status contract, not every supplementary claim.
The improved canonical replies pass both the frozen checker and this review.

| Case | Scenario | Baseline reviewed pass | Step 2 pass |
|---|---|---:|---:|
| D02 | Original indirect Northwind query | 3/3 | 3/3 |
| S01 | Explicit ID | 3/3 | 3/3 |
| S02 | Future deadline | 3/3 | 3/3 |
| S03 | Due today | 3/3 | 3/3 |
| S04 | Completed late | 3/3 | 3/3 |
| S05 | Ambiguous customer | 3/3 | 3/3 |
| S06 | Unknown order | 2/3 | 3/3 |
| S07 | Missing deadline (synthetic) | 0/3 | 3/3 |
| S08 | Invalid deadline (synthetic) | 0/3 | 3/3 |
| S09 | Missing stage (synthetic) | 3/3 | 3/3 |
| S10 | Switch order in a conversation | 3/3 | 3/3 |

## D02 answer example

> ORD-107 is in packing. Due date 2026-03-16. 16 calendar days overdue.
>
> As of 2026-04-01 (dataset clock).

## Actual API usage

| Usage | Baseline | Step 2 | Total |
|---|---:|---:|---:|
| Input tokens | 419,457 | 339,246 | 758,703 |
| Cached input (subset of input) | 382,813 | 317,897 | 700,710 |
| Output tokens | 8,519 | 5,140 | 13,659 |
| Reasoning (subset of output) | 1,455 | 391 | 1,846 |

Total calls: **161**. No judge calls. Tokens are provider-reported usage.
The repository-configured rates produce estimates of $0.025208 baseline and
$0.016796 improved ($0.042004 total).
Those rates are not verified current pricing or a provider bill. Reasoning tokens are already included
in output tokens; cached tokens are already included in input tokens. Engineering/chat usage is not
measured by this runner.

## Reproducibility and boundaries

- Baseline: clean code `44af3eed66d6a5f2aa8247c1f73c5df7218ec922` (Step 1 changed no runtime code).
- Improved at evaluation time: that commit plus the then-uncommitted Step 2 patch. The manifest records exact runtime/prompt hashes.
- Both manifests match on source data, questions, reference helper, checker, runner, model and reasoning effort.
- Public fixture SHA-256: `b64dfd10ad05ebc1910fcf69897422a870a58412ba5991c5d43d21b7caf12986`.
- Source CSVs are unchanged; synthetic overrides and independent reference facts are stored per attempt.
- Completed 33/33 attempts per version. No API execution errors. No failed cases were discarded.
- API data-transfer approval was given explicitly before the live runs. GitHub branch publication was separately approved after review on 20 October 2026.
- The offline suite passed `452 passed in 2.25s`; changed Python files pass Ruff, and `git diff --check` passes.
- This is development evidence. It does not establish unseen performance or replace Steps 4–5.
- Routing remains model-dependent outside these tested cases. Compound analytical/action questions use the general path.

Commands:

```sh
backend/.venv/bin/python -m pytest backend/tests eval/tests -q
backend/.venv/bin/python eval/run_step2.py --output-dir eval/results/step2/live-v1
backend/.venv/bin/python eval/run_step2.py --backend-root ../step2-baseline/backend --output-dir eval/results/step2/baseline-v1
```

Use fresh output directory names for another run; existing results are never overwritten.
