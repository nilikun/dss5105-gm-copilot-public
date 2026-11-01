# Independent evaluation rubric v1 — provisional until human calibration

Unit: one final answer to one question on one planned repetition. Include every displayed field,
including details, follow-ups, options and proposal fields. Never score using `grounded`, the agent's
critic, or its own calculation as reference truth. Source references come from separate CSV calculations
for development, and an independent teammate's calculation workbook/script for held-out evaluation.

## Hard facts and semantic review

Each required fact has a contextual extraction pattern with a named `value` group, expected value,
subject, field, units, calculation, numeric tolerance, and when relevant `scope_subject` and
`scope_dates`. Input text is normalized for Markdown, Unicode minus and English date spelling.
Numeric comparison preserves sign. Percentage rules also parse direction. All matches must agree;
one correct mention cannot rescue a contradiction. A missing/unrecognized pattern fails automatic
acceptance and needs review; do not equate a pattern failure with proven factual error.

Dates and percentage scope are checked in the same sentence as the extracted fact. This is deliberately
conservative. Natural wording can express scope across sentences; human calibration must quantify
these false rejections before freeze. Authors and reviewers validate patterns against correct equivalent
wording and wrong entity/date/sign/window examples before release. Do not change patterns after seeing
hidden system answers. Full semantic equivalence is not guaranteed by regular expressions.

A separate LLM judge assesses each required fact plus unsupported claims, relevance and clarity. It
receives the question, independent reference evidence and candidate answer, and returns criterion-level
boolean decisions, exact short supporting excerpts and reasons. Empty excerpts are allowed for omissions.
Invalid output, missing criteria or fabricated quotations are unscored, never an automatic pass.
Unknown cause must coexist with available observed production magnitude. Unsupported assertions fail.

Final pass requires **every hard fact, expected behavior, absence of prohibited claims, and every judge
criterion** to pass. A favourable judge cannot override a failed deadline, percentage, sign or window
check. There is no weighted average that compensates for a critical failure.

## Claims outside the reference evidence (fixed before any hidden answer is seen)

The judge can only check against the supplied package, so it fails a true statement the package omits. In a
development check on 13 real replies, 6 failed this way on a correct z-score. Strict final pass does not change. In
addition, every answer whose hard checks all pass but whose judge failed `unsupported_claims` or `clarity` is reviewed
by a person who did not build the system, against the source CSVs, claim by claim. The report gives strict pass and
reviewed pass side by side, with each decision recorded. A claim the CSVs do not support stays a failure.

## Human calibration (must happen before release)

Use at least 20 blinded, human-labelled public development answers, including equivalent correct prose,
omissions, wrong dates, signs/windows, unsupported causes and honest refusals. Labels require reviewer
identity, review time and criterion-level reasons. Retain all labels and judge predictions.

Prospective acceptance: at least **90% criterion agreement**, both positive and negative human labels,
and **zero false passes on critical facts or unsupported claims** in the calibration sample.
All hard-check disagreements must also be resolved before release. Report
confusion counts, every disagreement, and hard-check rejection disagreements separately. Revise only
on development material; any change to scorer/prompt/settings invalidates the freeze and requires
fresh calibration. A second reviewer adjudicates where possible. This threshold is an engineering
release gate, not proof of general judge reliability; the small sample remains a limitation.

## Metrics and denominator

- Final pass: all gates above. Planned attempts are the primary denominator; skipped attempts remain visible.
- Correctness: all required hard facts correct; report independently of semantic judge acceptance.
- Completeness: fraction of required facts recognized as present; wrong recognized values still count
  as present but fail correctness. Unrecognized wording can lower this measure; inspect disagreements.
- Unsupported claims: judge-identified unsupported answers; report unavailable judge decisions separately.
- Appropriate clarification/refusal: expected behavior matched, reported separately for both categories;
  final pass additionally requires relevant question/candidates and no invented facts.
- Latency: wall-clock agent time including context, p50/p90; judge latency retained separately.
- API usage: actual provider input/cached/output/reasoning tokens for every call, including context and
  enabled critic. Output already includes reasoning. Retries are disabled. Missing usage is unknown.
- Uncertainty: paired question-level bootstrap, 2,000 draws, seed 5105; repetitions are not independent
  questions. Twenty questions provide limited evidence. No interval on an incomplete run.

Serial item/version order is randomized with a frozen seed. Fresh databases/clocks per item. No action
is confirmed. Preserve attempts and failures; do not repeat until success. Budget is a soft item-boundary
cap using frozen documented rates, not a billing guarantee. API call/output/timeout caps limit each item.
Unknown usage or execution errors stop the run and leave remaining attempts explicitly unattempted.
All post-release exclusions require a separate adjudication record and both original/adjusted totals.
After hidden failures inform changes, those questions become regression material; further unseen claims
require fresh independent questions.

Guidance: [OpenAI evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices).
