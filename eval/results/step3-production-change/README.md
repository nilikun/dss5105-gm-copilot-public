> **Note, 1 Nov 2026.** These runs are on PR #3's own code. Its `get_production_change` route is not on `main`,
> which has a different implementation (`docs/STEP3_COMPARISONS.md`). The numbers below describe that code.

# Step 3 production-change verification

**Improved: 33/33 live development checks passed.** D35 plus ten variants, three planned repetitions,
fixed before the calls. The archived D35 percentage omission is also repaired in a controlled replay.
These are public development results, not unseen performance or human calibration.

| Comparison | Observed output | Fixed prior baseline | Change |
|---|---:|---:|---:|
| ASSEMBLY on 25 March 2026 | 394 pieces | median 766.5 pieces/day, 2–24 March | 48.6% below |
| ASSEMBLY over 25–31 March 2026 | mean 425.5 pieces/working day, 6 days | same preperiod baseline | 44.5% below |

The cause remains unknown. Sundays are excluded. Missing records are not zero; a partial observation
window or incomplete fixed baseline cannot produce a full-window percentage. Zero baseline has an
undefined percentage. These conventions are explicit changes from the legacy available-row baseline.

## What the comparison establishes

The fresh baseline D35 answers included 48.6% in **3/3** runs. There is no observed daily D35 omission
improvement in this fresh sample. The archived `20261015-2222-dev-gpt-5.6-luna-base-v6a` answer did omit
the percentage, and the regression test repairs that exact draft. In the new live runs, 0 final
model drafts omitted a required percent symbol; the validated renderer supplied it before display.

Both period-comparison cases failed to report the requested mean/percentage in all **6 baseline runs**
and passed in all **6 improved runs**. Zero/missing-baseline and missing-observation cases also passed
on the new route. The factory tool does the arithmetic; the renderer replaces the critical answer
with validated fields and explicitly discloses unavailable causes.

The bounded Step 1 checker accepts baseline **3/33** versus improved **33/33**, but it rejects several
correct natural baseline answers. **Do not interpret that as 30 newly corrected factual errors.**
An explicitly post-hoc assistant review finds **17/33 baseline answers contain the correct core
comparison/clarification**, versus 33/33 improved contract checks. This is a different, narrower metric,
not a human-calibrated score. Every per-answer decision and limitation is in `core-comparison-review.json`.

## Execution and usage

Baseline commit: `c33e4af7f6c311a1eae8b45097ea27cdc065f377` (Step 2). Improved code was uncommitted;
its exact backend/prompt hashes are recorded in `live-v1/manifest.json`. Model `gpt-5.6-luna`, low effort,
critic off, fresh database per item, dataset clock 1 April 2026. All replies, drafts, traces, synthetic
row overrides, references, errors and API-reported usage are retained. No action was executed.

| Version | Calls | Input tokens | Cached input | Output (includes reasoning) | Reasoning | p50 / p90 seconds |
|---|---:|---:|---:|---:|---:|---:|
| Baseline | 94 | 496819 | 449718 | 13615 | 4863 | 9.00 / 13.56 |
| Improved | 68 | 356359 | 327350 | 6501 | 774 | 6.33 / 8.37 |

Configured cost estimates are preserved in JSON, not represented as verified billing. Cached input is
part of total input; reasoning is part of total output. SDK automatic retries in this development
runner may have unreported usage. The new formal runner disables automatic retries and journals
unknown/interrupted usage explicitly.

## Limits

The guarantee applies after the model selects `get_production_change` for a single stage/window.
Mixed analytical/action turns retain the general path. Arbitrary incorrect tool routing is not eliminated.
All 33 live cases selected a path that passed the intended contract. This sample does not prove general
reliability. The independent held-out set and human labels are not ready, so no Step 5 result is claimed.
