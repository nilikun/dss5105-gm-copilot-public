# Evaluation run `20261015-2219-dev-gpt-5.6-luna-base-final1`

Set **dev** · model `gpt-5.6-luna` · reasoning low · critic **off** · prompt system v6 · commit `861f2d0` · 2026-10-15 22:19:46 · re-scored 2026-10-15 22:24:36 with the current scorer

| Metric | Value |
|---|---|
| Decision accuracy | **97.2%** (35/36) |
| Behaviour accuracy | 100.0% |
| Faithfulness (reply passed the verifier) | 100.0% |
| Unconfirmed side effects | 0 |
| Headline ≤ 3 lines | 100.0% |
| Verifier rejections (repaired) | 0 |
| Latency p50 / p90 | 7.2 s / 10.7 s |
| Cost total / per item | $0.0276 / $0.0008 |

## Per category

| Category | n | Decision |
|---|---|---|
| lookup | 5 | 80.0% |
| aggregation | 4 | 100.0% |
| judgement | 3 | 100.0% |
| tracing | 3 | 100.0% |
| discovery | 3 | 100.0% |
| feasibility | 5 | 100.0% |
| action | 5 | 100.0% |
| ambiguous | 3 | 100.0% |
| unanswerable | 5 | 100.0% |

## Behaviour (expected → got)

| Expected | Got | n |
|---|---|---|
| answer | answer | 18 |
| clarify | clarify | 3 |
| estimate | estimate | 5 |
| propose | propose | 4 |
| refuse | refuse | 5 |
| reject | reject | 1 |

## Items

| ID | Category | Expected | Got | Decision | Faithful | Missing / forbidden | s |
|---|---|---|---|---|---|---|---|
| D01 | lookup | answer | answer | ✓ | ✓ |  | 8.65 |
| D02 | lookup | answer | answer | ✗ | ✓ | missing: 2026-03-16 | 10.98 |
| D03 | lookup | answer | answer | ✓ | ✓ |  | 8.23 |
| D04 | lookup | answer | answer | ✓ | ✓ |  | 4.84 |
| D05 | lookup | answer | answer | ✓ | ✓ |  | 5.91 |
| D06 | aggregation | answer | answer | ✓ | ✓ |  | 5.32 |
| D07 | aggregation | answer | answer | ✓ | ✓ |  | 5.05 |
| D08 | aggregation | answer | answer | ✓ | ✓ |  | 6.7 |
| D09 | aggregation | answer | answer | ✓ | ✓ |  | 4.81 |
| D10 | judgement | answer | answer | ✓ | ✓ |  | 5.52 |
| D11 | judgement | answer | answer | ✓ | ✓ |  | 4.96 |
| D12 | judgement | answer | answer | ✓ | ✓ |  | 5.81 |
| D13 | tracing | answer | answer | ✓ | ✓ |  | 7.28 |
| D14 | tracing | answer | answer | ✓ | ✓ |  | 7.41 |
| D15 | tracing | answer | answer | ✓ | ✓ |  | 6.58 |
| D16 | discovery | answer | answer | ✓ | ✓ |  | 6.81 |
| D17 | discovery | answer | answer | ✓ | ✓ |  | 6.64 |
| D18 | discovery | answer | answer | ✓ | ✓ |  | 7.81 |
| D19 | feasibility | estimate | estimate | ✓ | ✓ |  | 7.78 |
| D20 | feasibility | estimate | estimate | ✓ | ✓ |  | 10.0 |
| D21 | feasibility | estimate | estimate | ✓ | ✓ |  | 10.02 |
| D22 | feasibility | estimate | estimate | ✓ | ✓ |  | 10.38 |
| D23 | feasibility | estimate | estimate | ✓ | ✓ |  | 6.39 |
| D24 | action | propose | propose | ✓ | ✓ |  | 7.88 |
| D25 | action | propose | propose | ✓ | ✓ |  | 6.07 |
| D26 | action | propose | propose | ✓ | ✓ |  | 10.71 |
| D27 | action | reject | reject | ✓ | ✓ |  | 19.07 |
| D28 | action | propose | propose | ✓ | ✓ |  | 7.0 |
| D29 | ambiguous | clarify | clarify | ✓ | ✓ |  | 5.83 |
| D30 | ambiguous | clarify | clarify | ✓ | ✓ |  | 7.67 |
| D31 | ambiguous | clarify | clarify | ✓ | ✓ |  | 7.17 |
| D32 | unanswerable | refuse | refuse | ✓ | ✓ |  | 6.9 |
| D33 | unanswerable | refuse | refuse | ✓ | ✓ |  | 12.03 |
| D34 | unanswerable | refuse | refuse | ✓ | ✓ |  | 7.27 |
| D35 | unanswerable | refuse | refuse | ✓ | ✓ |  | 7.89 |
| D36 | unanswerable | refuse | refuse | ✓ | ✓ |  | 8.39 |
