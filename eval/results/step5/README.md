> **Note, 1 Nov 2026.** Copied from PR #3 unchanged. `public-smoke-v2-main` repeats the smoke test on `main`.
> The held-out set is still pending, and no held-out result exists.

# Step 5 readiness — formal evaluation pending

The user confirmed that independent hidden questions/references and human development labels are not
ready. **No held-out question has been created, read or evaluated. No unseen-performance claim is made.**
The author/reviewer packets, frozen-release gates, paired runner and report generator are prepared.

A PUBLIC D35 end-to-end smoke test executed one improved and one Step-2-baseline attempt through the
new subprocess runner and independent judge. Both completed without transport/worker errors; all four
agent calls and two judge calls have recorded usage. The improved answer passed the provisional checks.
The baseline correctly reported 48.6% but was rejected for unrecognized prose/missing baseline window;
the judge also flagged an interrupt classification absent from its limited reference evidence. That is
an evidence-package limitation, not proof that the classification is false in the source data.

This one-question smoke test validates plumbing, not performance or calibrated judgement. It has no
meaningful confidence interval. The reporting count/interval handling was corrected after the smoke;
initial reports are preserved alongside corrected reports, and raw answers and scores are unchanged.

Before the formal 20-question comparison: obtain real human labels, resolve scorer/judge disagreements,
rerun calibration on final code, approve/commit code, then have the independent custodian complete the
freeze with question/reference/calculation hashes, exact versions/settings and a budget. The release
gate rejects provisional manifests. See `docs/EVALUATION_OPERATOR.md` for the commands and responsibilities.
