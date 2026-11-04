# Evaluation run `20261104-1732-dev-gpt-5.6-luna-base-s5b`

Set **dev** · model `gpt-5.6-luna` · reasoning low · critic **off** · prompt system v10 · commit `19a7dd6` · 2026-11-04 17:32:30

| Metric | Value |
|---|---|
| Decision accuracy | **100.0%** (36/36) |
| Behaviour accuracy | 100.0% |
| Faithfulness (reply passed the verifier) | 100.0% |
| Unconfirmed side effects | 0 |
| Headline ≤ 3 lines | 100.0% |
| Verifier rejections (repaired) | 0 |
| Latency p50 / p90 | 5.5 s / 9.2 s |
| Cost total / per item | $0.0251 / $0.0007 |

## Per category

| Category | n | Decision |
|---|---|---|
| lookup | 5 | 100.0% |
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
| D01 | lookup | answer | answer | ✓ | ✓ |  | 5.14 |
| D02 | lookup | answer | answer | ✓ | ✓ |  | 7.01 |
| D03 | lookup | answer | answer | ✓ | ✓ |  | 5.16 |
| D04 | lookup | answer | answer | ✓ | ✓ |  | 4.31 |
| D05 | lookup | answer | answer | ✓ | ✓ |  | 5.14 |
| D06 | aggregation | answer | answer | ✓ | ✓ |  | 5.22 |
| D07 | aggregation | answer | answer | ✓ | ✓ |  | 4.24 |
| D08 | aggregation | answer | answer | ✓ | ✓ |  | 6.62 |
| D09 | aggregation | answer | answer | ✓ | ✓ |  | 4.65 |
| D10 | judgement | answer | answer | ✓ | ✓ |  | 4.44 |
| D11 | judgement | answer | answer | ✓ | ✓ |  | 4.98 |
| D12 | judgement | answer | answer | ✓ | ✓ |  | 4.71 |
| D13 | tracing | answer | answer | ✓ | ✓ |  | 9.06 |
| D14 | tracing | answer | answer | ✓ | ✓ |  | 7.04 |
| D15 | tracing | answer | answer | ✓ | ✓ |  | 5.56 |
| D16 | discovery | answer | answer | ✓ | ✓ |  | 5.59 |
| D17 | discovery | answer | answer | ✓ | ✓ |  | 5.53 |
| D18 | discovery | answer | answer | ✓ | ✓ |  | 5.04 |
| D19 | feasibility | estimate | estimate | ✓ | ✓ |  | 9.2 |
| D20 | feasibility | estimate | estimate | ✓ | ✓ |  | 8.1 |
| D21 | feasibility | estimate | estimate | ✓ | ✓ |  | 10.14 |
| D22 | feasibility | estimate | estimate | ✓ | ✓ |  | 9.45 |
| D23 | feasibility | estimate | estimate | ✓ | ✓ |  | 4.47 |
| D24 | action | propose | propose | ✓ | ✓ |  | 8.7 |
| D25 | action | propose | propose | ✓ | ✓ |  | 4.82 |
| D26 | action | propose | propose | ✓ | ✓ |  | 9.77 |
| D27 | action | reject | reject | ✓ | ✓ |  | 9.22 |
| D28 | action | propose | propose | ✓ | ✓ |  | 7.51 |
| D29 | ambiguous | clarify | clarify | ✓ | ✓ |  | 4.91 |
| D30 | ambiguous | clarify | clarify | ✓ | ✓ |  | 6.14 |
| D31 | ambiguous | clarify | clarify | ✓ | ✓ |  | 4.81 |
| D32 | unanswerable | refuse | refuse | ✓ | ✓ |  | 4.93 |
| D33 | unanswerable | refuse | refuse | ✓ | ✓ |  | 5.01 |
| D34 | unanswerable | refuse | refuse | ✓ | ✓ |  | 7.17 |
| D35 | unanswerable | refuse | refuse | ✓ | ✓ |  | 7.34 |
| D36 | unanswerable | refuse | refuse | ✓ | ✓ |  | 6.78 |
