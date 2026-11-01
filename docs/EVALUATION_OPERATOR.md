# Independent evaluation operator guide (Steps 4–5)

Status: implementation and public tests prepared; **human calibration and the formal held-out run are
pending**. The user confirmed that teammate materials are not ready and requested author/reviewer packets.
Do not describe public fixtures, the judge integration check, or the pipeline smoke test as held-out.

The commands below use `backend/.venv/bin/python`. On Windows use `backend/.venv/Scripts/python.exe`, or
`uv run --project backend python`. Text files are read and written as UTF-8 on every platform. Take the hashes on one
machine from fresh checkouts, because a working copy with converted line endings hashes differently.

Before release, every answer whose hard checks pass but whose judge failed `unsupported_claims` or `clarity` goes to a
person who did not build the system, and the report gives both totals (see the rubric). Hard failures marked
`missing_or_unrecognized` also need that review: the patterns can reject correct natural wording.

## Roles and files

- The independent **author** receives only `HELDOUT_GUIDE.md`, the blank question/freeze templates,
  this extraction schema, and source CSVs/data dictionary. They must not see the reviewer packet or
  development results. Keep completed files outside the development checkout.
- The **reviewer** receives `eval/calibration/reviewer-packet-v1/` and `eval/protocol/rubric.md`.
  Label all 20 answers without seeing judge predictions. Return `human_labels.jsonl` privately.
  Obtain a second reviewer where possible and retain adjudications.
- The **operator** runs calibration, captures the freeze, and executes the formal runner after release.
  Hashes and signed declarations preserve custody; code cannot prove a human was independent.

## Required-fact schema

Every item needs nonempty reference evidence and at least one required criterion, including clarification,
refusal, estimate or action criteria when appropriate. Every required fact is a mapping:

| Field | Meaning |
|---|---|
| `criterion_id` | Unique stable ID; reserve unsupported_claims, relevance and clarity for the judge |
| `subject`, `field` | Which entity and attribute are being checked |
| `expected_value` | Independently calculated number, ISO date or nonempty text |
| `value_type` | `number`, `percentage`, `date` or `text` |
| `pattern` | Case-insensitive Python regex with one named `(?P<value>...)` capture; capture the asserted value, not a disconnected number |
| `tolerance` | Nonnegative absolute tolerance; percentage-point tolerance for percentages; normally zero for dates/counts |
| `unit`, `calculation` | Unit and independent derivation; explicit `not_applicable` where appropriate |
| `aliases` | Optional equivalent text values, frozen before evaluation |
| `scope_subject` | Optional entity that must appear in the same sentence as the value |
| `scope_dates` | Optional ordered list of exact ISO dates in that sentence; one date or inclusive start/end |

The scorer normalizes English date spellings, Markdown and Unicode minus. Context patterns bind values
to their meaning. For a fictitious format example, `deadline\s*:\s*(?P<value>\d{4}-\d{2}-\d{2})`
extracts the date after a deadline label; it cannot count a last-activity date as the deadline. Broaden
patterns for equivalent wording using PUBLIC examples before freezing. Overly broad patterns can match
unrelated facts; overly narrow ones reject correct prose. A teammate checks both directions. Final
acceptance also requires the independent semantic judge. Regex recognition is not universal semantics.

`reference_evidence` entries require `source_file`, `row_filter`, `calculation`, `result`, and
`workbook_cells_or_script`; record the checker as well. `prohibited_claims` is a list of contextual regex
patterns for explicitly forbidden claims, not keywords that also occur in honest refusals.
The judge independently reviews other unsupported assertions. For order status, include identity,
stage, deadline and timing. For production change, include actual, baseline definition/window, statistic,
unit, signed magnitude, observation window and cause availability. Do not omit a criterion just because
the system may struggle with it. Never derive reference values from the agent's output or tools.

## Calibration commands

From the repository root, with the backend environment installed:

```sh
backend/.venv/bin/python eval/calibrate.py judge \
  --packet eval/calibration/reviewer-packet-v1/candidates.jsonl \
  --output /private-evaluation/judge-predictions.jsonl
backend/.venv/bin/python eval/calibrate.py compare \
  --packet eval/calibration/reviewer-packet-v1/candidates.jsonl \
  --labels /private-evaluation/human_labels.jsonl \
  --judgments /private-evaluation/judge-predictions.jsonl \
  --output /private-evaluation/calibration-report.json
```

Replace example external paths with the custodian's directory. Use no real key in shell arguments.
The API key comes from the configured environment. Outputs never overwrite prior runs. Predictions
record packet/scoring hashes and exact judge settings. Stale predictions, missing/duplicate criteria,
blank labels and invalid judge excerpts cannot produce an accepted calibration report.

Prospective acceptance: >=90% criterion agreement, both labels represented, zero critical judge false
passes, and no unresolved hard-check disagreements. Report confusion counts and every disagreement.
The public integration predictions in `eval/results/step4/judge-v1.jsonl` predate final release-gate changes
and are **not eligible as frozen calibration**. Run the command above after code is finalized and labels
are ready. Do not copy assistant intentions into human labels.

## Freeze and execute

After any approved GitHub publication/commit, use clean baseline and improved checkouts. The Step 1
baseline recorded in `eval/baselines/step1.json` is `36a44c7e4965154f78853526333b8219c54ad1ad`.
The Step 3 development comparison used Step 2 commit `c33e4af...`; do not confuse it with the before-both-fixes
baseline for the formal comparison. The frozen operator chooses and records the intended full SHA.

```sh
backend/.venv/bin/python eval/prepare_freeze.py \
  --baseline /baseline-checkout --improved /improved-checkout \
  --output /private-evaluation/freeze-candidate.json
```

This captures only PUBLIC code/data/settings metadata and stays `provisional_not_releasable`.
It never reads questions or labels. The custodian fills author/checker/exposure records, independently
computed reference file hashes, question hash, accepted calibration report filename/hash, current pricing
source/date and rates, budget, freeze/release times and remaining protocol fields. Copy the accepted
report and independent workbook/script beside the manifest. Set both package and manifest status to
`frozen` only after checks. Hidden content is parsed only after code/data/calibration gates pass.

The scorer, rubric, prompts, Python/SDK versions, agent/judge settings and references must remain fixed.
Any subsequent scoring change requires recalibration and a fresh freeze before release. If evaluation
questions were exposed to tuning, replace them for an unseen claim.

```sh
backend/.venv/bin/python eval/run_frozen.py \
  --freeze /private-evaluation/heldout_freeze.json \
  --baseline /baseline-checkout --improved /improved-checkout \
  --output-dir /private-evaluation/results-run-1
```

The v2 runner is separate from legacy `eval/run.py`. It serially randomizes 20 questions × 3 repetitions ×
2 versions, resets data/clock per item, replays context independently, disables SDK retries, and does not
confirm actions. Every attempt, error, trace, answer, judge decision and available usage is saved. An
interrupted call remains usage-unknown. Errors/unknown billing halt rather than repeatedly charging;
unattempted cases remain in the planned denominator. The budget is an estimate checked between items,
with per-item API-call/output/timeout caps. Never treat it as a strict billing ceiling.

Review `REPORT.md`, `summary.json`, `results.jsonl` and the frozen schedule. Metrics include correctness,
recognized completeness, unsupported claims/unscored counts, appropriate clarification/refusal, categories,
latency, API usage and a paired question-level bootstrap interval when complete. Twenty questions are a
small sample. Report every failure, and preserve original denominators if adjudication later excludes items.
Obtain publication approval before sharing private evaluation contents or uploading changes.
