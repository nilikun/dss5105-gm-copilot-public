# Evaluation run `20261015-0235-dev-gpt-5.6-luna-critic-r2`

Set **dev** · model `gpt-5.6-luna` · reasoning low · critic **on** · prompt system v4 · commit `44d22e8` · 2026-10-15 02:35:18 · re-scored 2026-10-15 22:24:36 with the current scorer

| Metric | Value |
|---|---|
| Decision accuracy | **94.4%** (34/36) |
| Behaviour accuracy | 97.2% |
| Faithfulness (reply passed the verifier) | 100.0% |
| Unconfirmed side effects | 0 |
| Headline ≤ 3 lines | 100.0% |
| Verifier rejections (repaired) | 1 |
| Latency p50 / p90 | 8.9 s / 18.1 s |
| Cost total / per item | $0.0447 / $0.0012 |

## Per category

| Category | n | Decision |
|---|---|---|
| lookup | 5 | 100.0% |
| aggregation | 4 | 100.0% |
| judgement | 3 | 100.0% |
| tracing | 3 | 66.7% |
| discovery | 3 | 100.0% |
| feasibility | 5 | 80.0% |
| action | 5 | 100.0% |
| ambiguous | 3 | 100.0% |
| unanswerable | 5 | 100.0% |

## Behaviour (expected → got)

| Expected | Got | n |
|---|---|---|
| answer | answer | 17 |
| answer | clarify | 1 |
| clarify | clarify | 3 |
| estimate | estimate | 5 |
| propose | propose | 4 |
| refuse | refuse | 5 |
| reject | reject | 1 |

## Items

| ID | Category | Expected | Got | Decision | Faithful | Missing / forbidden | s |
|---|---|---|---|---|---|---|---|
| D01 | lookup | answer | answer | ✓ | ✓ |  | 6.46 |
| D02 | lookup | answer | answer | ✓ | ✓ |  | 14.62 |
| D03 | lookup | answer | answer | ✓ | ✓ |  | 8.11 |
| D04 | lookup | answer | answer | ✓ | ✓ |  | 6.15 |
| D05 | lookup | answer | answer | ✓ | ✓ |  | 5.54 |
| D06 | aggregation | answer | answer | ✓ | ✓ |  | 5.21 |
| D07 | aggregation | answer | answer | ✓ | ✓ |  | 7.46 |
| D08 | aggregation | answer | answer | ✓ | ✓ |  | 7.06 |
| D09 | aggregation | answer | answer | ✓ | ✓ |  | 5.74 |
| D10 | judgement | answer | answer | ✓ | ✓ |  | 6.73 |
| D11 | judgement | answer | answer | ✓ | ✓ |  | 7.04 |
| D12 | judgement | answer | answer | ✓ | ✓ |  | 10.14 |
| D13 | tracing | answer | answer | ✓ | ✓ |  | 19.91 |
| D14 | tracing | answer | clarify | ✗ | ✓ | missing: 8; missing: 11; missing: 10.9 | 13.59 |
| D15 | tracing | answer | answer | ✓ | ✓ |  | 9.0 |
| D16 | discovery | answer | answer | ✓ | ✓ |  | 8.78 |
| D17 | discovery | answer | answer | ✓ | ✓ |  | 7.62 |
| D18 | discovery | answer | answer | ✓ | ✓ |  | 17.0 |
| D19 | feasibility | estimate | estimate | ✓ | ✓ |  | 15.24 |
| D20 | feasibility | estimate | estimate | ✓ | ✓ |  | 15.79 |
| D21 | feasibility | estimate | estimate | ✓ | ✓ |  | 21.62 |
| D22 | feasibility | estimate | estimate | ✓ | ✓ |  | 18.08 |
| D23 | feasibility | estimate | estimate | ✗ | ✓ | missing: 12% | 13.55 |
| D24 | action | propose | propose | ✓ | ✓ |  | 11.36 |
| D25 | action | propose | propose | ✓ | ✓ |  | 6.13 |
| D26 | action | propose | propose | ✓ | ✓ |  | 18.57 |
| D27 | action | reject | reject | ✓ | ✓ |  | 14.4 |
| D28 | action | propose | propose | ✓ | ✓ |  | 9.0 |
| D29 | ambiguous | clarify | clarify | ✓ | ✓ |  | 7.39 |
| D30 | ambiguous | clarify | clarify | ✓ | ✓ |  | 8.25 |
| D31 | ambiguous | clarify | clarify | ✓ | ✓ |  | 7.97 |
| D32 | unanswerable | refuse | refuse | ✓ | ✓ |  | 6.67 |
| D33 | unanswerable | refuse | refuse | ✓ | ✓ |  | 9.46 |
| D34 | unanswerable | refuse | refuse | ✓ | ✓ |  | 9.41 |
| D35 | unanswerable | refuse | refuse | ✓ | ✓ |  | 11.77 |
| D36 | unanswerable | refuse | refuse | ✓ | ✓ |  | 7.73 |
