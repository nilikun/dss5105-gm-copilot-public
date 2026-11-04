# Evaluation run `20261104-1731-dev-gpt-5.6-luna-base-s5a`

Set **dev** · model `gpt-5.6-luna` · reasoning low · critic **off** · prompt system v10 · commit `19a7dd6` · 2026-11-04 17:31:02

| Metric | Value |
|---|---|
| Decision accuracy | **100.0%** (36/36) |
| Behaviour accuracy | 100.0% |
| Faithfulness (reply passed the verifier) | 100.0% |
| Unconfirmed side effects | 0 |
| Headline ≤ 3 lines | 100.0% |
| Verifier rejections (repaired) | 0 |
| Latency p50 / p90 | 6.3 s / 9.2 s |
| Cost total / per item | $0.0290 / $0.0008 |

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
| D01 | lookup | answer | answer | ✓ | ✓ |  | 7.88 |
| D02 | lookup | answer | answer | ✓ | ✓ |  | 10.48 |
| D03 | lookup | answer | answer | ✓ | ✓ |  | 7.42 |
| D04 | lookup | answer | answer | ✓ | ✓ |  | 4.4 |
| D05 | lookup | answer | answer | ✓ | ✓ |  | 4.71 |
| D06 | aggregation | answer | answer | ✓ | ✓ |  | 5.38 |
| D07 | aggregation | answer | answer | ✓ | ✓ |  | 4.61 |
| D08 | aggregation | answer | answer | ✓ | ✓ |  | 5.96 |
| D09 | aggregation | answer | answer | ✓ | ✓ |  | 6.98 |
| D10 | judgement | answer | answer | ✓ | ✓ |  | 4.34 |
| D11 | judgement | answer | answer | ✓ | ✓ |  | 6.0 |
| D12 | judgement | answer | answer | ✓ | ✓ |  | 4.57 |
| D13 | tracing | answer | answer | ✓ | ✓ |  | 6.42 |
| D14 | tracing | answer | answer | ✓ | ✓ |  | 6.92 |
| D15 | tracing | answer | answer | ✓ | ✓ |  | 6.16 |
| D16 | discovery | answer | answer | ✓ | ✓ |  | 5.78 |
| D17 | discovery | answer | answer | ✓ | ✓ |  | 6.14 |
| D18 | discovery | answer | answer | ✓ | ✓ |  | 5.22 |
| D19 | feasibility | estimate | estimate | ✓ | ✓ |  | 8.51 |
| D20 | feasibility | estimate | estimate | ✓ | ✓ |  | 9.87 |
| D21 | feasibility | estimate | estimate | ✓ | ✓ |  | 5.41 |
| D22 | feasibility | estimate | estimate | ✓ | ✓ |  | 8.93 |
| D23 | feasibility | estimate | estimate | ✓ | ✓ |  | 6.67 |
| D24 | action | propose | propose | ✓ | ✓ |  | 9.17 |
| D25 | action | propose | propose | ✓ | ✓ |  | 4.76 |
| D26 | action | propose | propose | ✓ | ✓ |  | 7.68 |
| D27 | action | reject | reject | ✓ | ✓ |  | 12.24 |
| D28 | action | propose | propose | ✓ | ✓ |  | 5.94 |
| D29 | ambiguous | clarify | clarify | ✓ | ✓ |  | 7.0 |
| D30 | ambiguous | clarify | clarify | ✓ | ✓ |  | 7.5 |
| D31 | ambiguous | clarify | clarify | ✓ | ✓ |  | 6.27 |
| D32 | unanswerable | refuse | refuse | ✓ | ✓ |  | 4.62 |
| D33 | unanswerable | refuse | refuse | ✓ | ✓ |  | 5.04 |
| D34 | unanswerable | refuse | refuse | ✓ | ✓ |  | 7.19 |
| D35 | unanswerable | refuse | refuse | ✓ | ✓ |  | 8.4 |
| D36 | unanswerable | refuse | refuse | ✓ | ✓ |  | 6.6 |
