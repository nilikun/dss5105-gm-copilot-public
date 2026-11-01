> **Note, 1 Nov 2026.** Copied from PR #3 unchanged. `real-replies-v1` and `v2` were added on `main`: the judge on
> replies the current system really wrote. Human calibration is still pending.

# Step 4 integration evidence — not human calibration

The independent judge returned **20/20 valid criterion-level responses**, including short literal
supporting excerpts. Combined decisions matched the 10 intended correct and 10 deliberately flawed
public engineering examples. Intentions were authored by the developer/assistant, **not human labels**.
No human agreement, accepted calibration, or frozen-judge claim is made.

The hard checks independently reject wrong deadlines, omitted percentages, reversed direction and
wrong windows even with a favourable judge. They do not import agent tools or use `reply.grounded`.
The semantic judge reviews required facts, unsupported claims, relevance and clarity. A malformed
response is unscored; every hard failure and every negative semantic decision vetoes final acceptance.

Usage: 23981 input tokens, 0 cached input,
6393 output tokens (including 0 reported reasoning tokens).
Judge: gpt-6-astra, low effort, output limit 4,000, no automatic retries. All 20 raw outputs, criteria,
excerpts, usage and latency remain in `judge-v1.jsonl`. No billing cost is asserted.

The reviewer packet contains 20 candidates and blank human labels, separately from these predictions.
The user confirmed that reviewers have not supplied labels yet. Final protocol changes after this
integration run invalidate it for a formal freeze: rerun predictions with final code when calibration
is ready. The comparison command rejects stale hashes rather than treating this run as calibration.

Limitations: hard extraction remains conservative and needs human validation on equivalent natural
wording. The semantic judge is limited by the supplied reference evidence: an extra factual claim can
be unsupported by that package without being false in the original data. Human reviewers must resolve
these gaps before formal scoring is frozen. No general judge reliability is established here.
