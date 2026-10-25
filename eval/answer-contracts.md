# Answer contracts: Step 1 requirements

Status: proposed contract for D02/D35 improvements, 20 October 2026. Development material;
not a held-out set. The runtime, prompts, existing scorer, and historical scores are unchanged.

## Order status

A status answer must identify the resolved order, state its current stage (or completion),
state its deadline, and explain its timing against the dataset clock. These facts must describe
**the same order**. A correct date appearing as a last-activity date or on a different order does
not meet the deadline requirement. Natural dates and equivalent wording are acceptable.

| Situation | Required meaning |
|---|---|
| Open, past deadline | Order ID, active stage, due date, calendar days overdue |
| Open, future deadline | Order ID, active stage, due date, calendar days remaining |
| Open, due today | Order ID, active stage, due date, explicitly due today |
| Complete | Order ID, complete, due date, completed date, days late/early or on time; no current-overdue claim |
| Missing due date | State that the deadline is unavailable; retain known identity/stage; do not calculate lateness |
| Missing stage | State that the stage is unavailable; retain other known facts |
| Missing completion date | State completion if known and disclose missing date; do not infer completion timing |
| Multiple matching orders | Ask which order; identify real candidates; do not select an order or attach one candidate's dates to another |
| No matching order | Explain that no match was found and request a usable identifier; invent no order facts |

Timing uses calendar-date subtraction, not factory working days: for open orders,
`as_of - due_date`; for completed orders, `completed_date - due_date`. An active stage implies
in-progress status. Explicitly contradictory statuses fail. The evaluation clock is
`2026-04-01T07:00:00`, a timezone-naive factory simulation, independent of the computer's date.

Development anchor D02: ORD-107 is in PACKING, due 2026-03-16, 16 calendar days overdue as of
2026-04-01. “ORD-107 is in packing. Deadline was 16 March. It is 16 days late.” preserves these
facts. “Packing, 16 days late” omits identity and deadline.

## Production comparisons

A comparison must state stage, observation date or inclusive window, actual output and units,
baseline value and its definition/window, percentage change with direction, and whether the
records establish a cause. A “why” request with no causal data must still report the observed
change and explicitly say the cause is unknown. For compatibility with the existing reply kind,
D35 remains `refuse` for the unanswerable causal part; it still requires the quantitative facts.
An ordinary comparison request is `answer` when its numeric facts are available.

`percentage change = 100 × (actual / baseline − 1)`; negative means below, positive above.
Compare like units: daily pieces to a daily baseline, or mean pieces per working day to that
baseline. Never compare a multi-day total directly to a one-day median. “48.6% of baseline”
means something different from “48.6% below baseline.” Sign and direction must agree.

| Development comparison | Observation | Fixed baseline | Correct change |
|---|---|---|---|
| D35, on 25 March | ASSEMBLY, 394 pieces on 2026-03-25 | 766.5 pieces/day: median of 20 working days, 2026-03-02–2026-03-24 | −48.5975…%, normally 48.6% below |
| Mean over 25–31 March | ASSEMBLY, 425.5 pieces/working day over 6 working days | Same fixed pre-25-March median | −44.4879…%, 44.5% below or approximately 44% below at whole-percent precision |

Sundays are excluded from working-day means and baselines; the second window includes Sunday
29 March but its zero does not enter the mean. For a new daily comparison the previous 20
working days precede that day; do not silently reuse D35's baseline. For the period comparison
above, explicitly use the fixed baseline preceding the period. Keep calculations unrounded and
round only for display. The historical value 426 is the whole-piece display of 425.5; 426 is not
the input to the percentage calculation.

For the question “on 25 March,” the single-day result is required. A period mean may be added
as context, but cannot replace it. For a period question, the mean and both endpoints are
required. The historical any-of acceptance of −44% or −48.6% is insufficient on its own.

| Edge case | Required behavior |
|---|---|
| Baseline missing / inadequate history | Report available actual output, disclose unavailable comparison, do not invent a percentage |
| Baseline zero | Report actual and zero baseline; percentage change is undefined, including 0/0 |
| Actual missing / incomplete window | Disclose missing observation/coverage; no invented output, no implicit missing-as-zero, no percentage for an incomplete requested window |
| Actual zero, positive baseline | Report zero and −100% if the zero is observed; distinguish closed Sundays |
| Stage or period ambiguous | Ask for clarification before attaching a percentage to a guessed scope |
| Cause unavailable | Explicitly say the records do not establish it; do not guess staffing, breakdowns, or other causes, even with “probably” |
| Cause supported in future data | Require separate causal evidence tied to this stage/window; correlation alone is insufficient |

Dates and IDs are exact. Daily displayed percentages may round to one decimal (0.05 percentage
point tolerance). Whole-percent period estimates may round within 0.5 percentage points; this
never excuses a different direction, denominator, statistic, or window. No sign-insensitive
numeric matching and no favourable judge score may override a failed hard requirement.

## Executable development checks

From the repository root:

```sh
python -m pytest eval/tests -q
python eval/record_step1_baseline.py --check
```

The public fixture file is `eval/fixtures/answer_contracts.json`. Each case contains a question,
provenance, reference facts, equivalent accepted answers, and deliberately incorrect answers
with a required failure reason. Synthetic edges are explicitly labelled. Source-backed references
are independently recomputed with Python's CSV/statistics modules, without importing agent tools,
the grounding verifier, or the old scorer.

`eval/answer_contracts.py` is a **bounded development checker**, not a complete natural-language
scorer. It binds the percentage to the short observation sentence and checks baseline facts in a
separate sentence. Its accepted date forms include ISO, “25 March [2026]”, and “March 25[, 2026]”.
Its unknown-cause phrases are deliberately limited; unrecognized extra production sentences are
flagged for review. Other valid prose may require manual review;
a pass does not certify that every possible extra claim is supported. Requirements above are the
full target; examples exercise selected edges, not every possible phrasing. Step 4 will add
independent full-answer scoring and a human-calibrated judge before held-out use.

These tests do not measure current agent accuracy and do not fix D02 or D35. No model or judge
is called. Do not substitute this checker or the existing scorer for the frozen evaluator.
