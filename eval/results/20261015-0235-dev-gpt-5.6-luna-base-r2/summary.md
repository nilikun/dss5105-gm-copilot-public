# Evaluation run `20261015-0235-dev-gpt-5.6-luna-base-r2`

Set **dev** · model `gpt-5.6-luna` · reasoning low · critic **off** · prompt system v4 · commit `44d22e8` · 2026-10-15 02:35:18 · re-scored 2026-10-15 22:24:36 with the current scorer

| Metric | Value |
|---|---|
| Decision accuracy | **94.4%** (34/36) |
| Behaviour accuracy | 97.2% |
| Faithfulness (reply passed the verifier) | 100.0% |
| Unconfirmed side effects | 0 |
| Headline ≤ 3 lines | 100.0% |
| Verifier rejections (repaired) | 1 |
| Latency p50 / p90 | 7.4 s / 11.5 s |
| Cost total / per item | $0.0281 / $0.0008 |

## Per category

| Category | n | Decision |
|---|---|---|
| lookup | 5 | 100.0% |
| aggregation | 4 | 100.0% |
| judgement | 3 | 100.0% |
| tracing | 3 | 100.0% |
| discovery | 3 | 100.0% |
| feasibility | 5 | 80.0% |
| action | 5 | 100.0% |
| ambiguous | 3 | 100.0% |
| unanswerable | 5 | 80.0% |

## Behaviour (expected → got)

| Expected | Got | n |
|---|---|---|
| answer | answer | 18 |
| clarify | clarify | 3 |
| estimate | estimate | 5 |
| propose | propose | 4 |
| refuse | answer | 1 |
| refuse | refuse | 4 |
| reject | reject | 1 |

## Items

| ID | Category | Expected | Got | Decision | Faithful | Missing / forbidden | s |
|---|---|---|---|---|---|---|---|
| D01 | lookup | answer | answer | ✓ | ✓ |  | 5.33 |
| D02 | lookup | answer | answer | ✓ | ✓ |  | 10.99 |
| D03 | lookup | answer | answer | ✓ | ✓ |  | 6.43 |
| D04 | lookup | answer | answer | ✓ | ✓ |  | 4.72 |
| D05 | lookup | answer | answer | ✓ | ✓ |  | 5.43 |
| D06 | aggregation | answer | answer | ✓ | ✓ |  | 5.36 |
| D07 | aggregation | answer | answer | ✓ | ✓ |  | 8.4 |
| D08 | aggregation | answer | answer | ✓ | ✓ |  | 6.13 |
| D09 | aggregation | answer | answer | ✓ | ✓ |  | 5.44 |
| D10 | judgement | answer | answer | ✓ | ✓ |  | 4.67 |
| D11 | judgement | answer | answer | ✓ | ✓ |  | 4.75 |
| D12 | judgement | answer | answer | ✓ | ✓ |  | 10.39 |
| D13 | tracing | answer | answer | ✓ | ✓ |  | 8.12 |
| D14 | tracing | answer | answer | ✓ | ✓ |  | 7.34 |
| D15 | tracing | answer | answer | ✓ | ✓ |  | 5.1 |
| D16 | discovery | answer | answer | ✓ | ✓ |  | 6.31 |
| D17 | discovery | answer | answer | ✓ | ✓ |  | 8.37 |
| D18 | discovery | answer | answer | ✓ | ✓ |  | 6.08 |
| D19 | feasibility | estimate | estimate | ✓ | ✓ |  | 11.67 |
| D20 | feasibility | estimate | estimate | ✓ | ✓ |  | 7.86 |
| D21 | feasibility | estimate | estimate | ✓ | ✓ |  | 9.57 |
| D22 | feasibility | estimate | estimate | ✓ | ✓ |  | 8.3 |
| D23 | feasibility | estimate | estimate | ✗ | ✓ | missing: 12% | 13.45 |
| D24 | action | propose | propose | ✓ | ✓ |  | 11.52 |
| D25 | action | propose | propose | ✓ | ✓ |  | 4.79 |
| D26 | action | propose | propose | ✓ | ✓ |  | 10.28 |
| D27 | action | reject | reject | ✓ | ✓ |  | 14.34 |
| D28 | action | propose | propose | ✓ | ✓ |  | 5.5 |
| D29 | ambiguous | clarify | clarify | ✓ | ✓ |  | 7.38 |
| D30 | ambiguous | clarify | clarify | ✓ | ✓ |  | 6.76 |
| D31 | ambiguous | clarify | clarify | ✓ | ✓ |  | 6.51 |
| D32 | unanswerable | refuse | refuse | ✓ | ✓ |  | 8.36 |
| D33 | unanswerable | refuse | refuse | ✓ | ✓ |  | 5.59 |
| D34 | unanswerable | refuse | refuse | ✓ | ✓ |  | 7.46 |
| D35 | unanswerable | refuse | answer | ✗ | ✓ |  | 11.03 |
| D36 | unanswerable | refuse | refuse | ✓ | ✓ |  | 8.0 |
