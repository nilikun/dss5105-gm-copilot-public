# Step 2: order deadlines

Implementation on `eval/step-2-order-deadlines`, based on Step 1 commit
`44af3eed66d6a5f2aa8247c1f73c5df7218ec922`. The user approved branch publication on 20 October 2026; merging into `main` is a separate action.

## Behavior

The purpose-built `get_order_status` tool resolves the supplied order ID or customer/product
and returns validated status fields. The runtime constructs the final status answer from them.
For D02, the resulting answer is:

> ORD-107 is in packing. Due date 2026-03-16. 16 calendar days overdue.
>
> As of 2026-04-01 (dataset clock).

The tool computes timing by subtracting calendar dates. Open orders use the simulated current
date; completed orders use the completion date and report early/late/on-time completion.
The `days_late` column is not trusted for this calculation. Invalid or missing deadlines and
completion dates are disclosed; no timing is inferred from them. Missing stages are explicit.
Future completion dates are treated as invalid, rather than as completed historical facts.

The original model draft, details, follow-ups, and any critic revision cannot overwrite the
status response. The existing verifier still checks the constructed reply and its evidence.
An unsuccessful model formatting loop can recover the verified status already retrieved.

An ambiguous lookup returns actual candidates and asks which order. A later model guess in
the same turn cannot override that ambiguity. Candidate lists remain complete in the details;
at most six buttons are shown. No matches produce a request for an identifier, without
inventing alternatives. Free-text clarification is now valid when there are no candidates.
A mismatch with an order ID explicitly supplied by the user also requests clarification.

## Scope and limits

System prompt v7 directs order-status/stage/deadline/lateness questions to `get_order_status`.
The deterministic route is used when the turn contains that tool and only order lookup or
time-resolution support tools. Analytical, action, and compound questions keep the general
response path, preserving proposals and their confirmation requirement.

The renderer guarantees completeness **once this status route is selected and valid data is
retrieved**. Tool selection and interpreting an indirect description still depend on the model;
they must be measured by live development runs and later the independent held-out evaluation.
The existing `get_order` tool remains a general fact-sheet tool. Its behavior and the production
answer path are not changed by this step. D35 belongs to Step 3.

## Checks and reproducibility

`eval/fixtures/step2_order_status.json` contains D02 and ten additional public development
cases. The suite includes direct and indirect references, future/today/past deadlines,
completion, ambiguity, no match, blank/invalid dates, a missing stage, and a conversation that
switches from one order to another. Synthetic changes affect fresh in-memory databases only.
The source CSVs are unchanged. All eleven cases run three times against an intentionally
incomplete model draft; these are controlled tests, not measured model accuracy.

References are recomputed from source CSV rows with `eval/step2_reference.py`; it does not
import agent tools or the verifier. It uses the Step 1 bounded answer-contract checker with
Markdown emphasis removed. Passes do not depend on the reply's `grounded` flag. Other valid
prose can need manual review; this is not the Step 4 evaluator or an LLM judge.

Additional regression checks cover every source order, wrong-order dates, contradictory
stages, an incorrect refusal, critic revisions, clock boundaries, missing completion dates,
stale recorded lateness, more than six candidates, and proposal confirmation.

From the repository root:

```sh
backend/.venv/bin/python -m pytest backend/tests eval/tests -q
backend/.venv/bin/python eval/run_step2.py --output-dir eval/results/step2/live-v1
```

The second command uses the project's configured OpenAI model and credentials and sends
questions and retrieved tool data to that API. The user explicitly approved that transfer before execution. Both the baseline and improved
versions have now completed 33 live cases; the improved version passes all 33. See
`../eval/results/step2/README.md` for the comparison, retained failures, actual usage and scoring limitations.

The runner writes a manifest **before** calling the API: code version and source hashes,
data hashes, fixture/checker/reference/runner hashes, simulated date, model settings,
repetitions, critic state, and configured cost rates. Every attempted answer, error, trace,
reference and score is retained. Actual API-reported tokens are separate from the cost estimate;
configured rates are not a provider bill. Failed requests may have unreported usage.
The suite has a configured-cost cap and will not overwrite an existing run directory.

For a baseline comparison, pass `--backend-root /path/to/unchanged-baseline/backend` to the same
runner; the baseline should be a clean checkout of the commit above. Both versions use the
same questions, clock, data, model settings and checker. All failed runs must remain available.
No held-out questions are opened or generated by this command.

## Review and upload

This local branch is named `eval/step-2-order-deadlines` (no `codex/` prefix). The `eval/`
portion is a Git branch namespace, separate from the repository's `eval/` directory.
The existing `eval/answer-contracts.md` stays the Step 1 contract; the new fixture, runner,
reference helper and results live under `eval/`. Runtime implementation lives under `backend/`.
The user reviewed the patch and file-by-file package and approved upload on 20 October 2026.
A Git push publishes this branch for review; it does not merge it into `main`.
