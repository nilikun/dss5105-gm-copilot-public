# Evaluation run `20261104-1937-dev-gpt-5.6-luna-base-h01b`

Set **dev** · model `gpt-5.6-luna` · reasoning low · critic **off** · prompt system v10 · commit `6e28021` · 2026-11-04 19:37:03

| Metric | Value |
|---|---|
| Decision accuracy | **100.0%** (36/36) |
| Behaviour accuracy | 100.0% |
| Faithfulness (reply passed the verifier) | 100.0% |
| Unconfirmed side effects | 0 |
| Headline ≤ 3 lines | 100.0% |
| Verifier rejections (repaired) | 0 |
| Latency p50 / p90 | 6.3 s / 9.0 s |
| Cost total / per item | $0.0261 / $0.0007 |

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
| D01 | lookup | answer | answer | ✓ | ✓ |  | 4.85 |
| D02 | lookup | answer | answer | ✓ | ✓ |  | 8.87 |
| D03 | lookup | answer | answer | ✓ | ✓ |  | 6.33 |
| D04 | lookup | answer | answer | ✓ | ✓ |  | 4.21 |
| D05 | lookup | answer | answer | ✓ | ✓ |  | 4.88 |
| D06 | aggregation | answer | answer | ✓ | ✓ |  | 5.18 |
| D07 | aggregation | answer | answer | ✓ | ✓ |  | 4.3 |
| D08 | aggregation | answer | answer | ✓ | ✓ |  | 6.46 |
| D09 | aggregation | answer | answer | ✓ | ✓ |  | 4.69 |
| D10 | judgement | answer | answer | ✓ | ✓ |  | 4.29 |
| D11 | judgement | answer | answer | ✓ | ✓ |  | 4.35 |
| D12 | judgement | answer | answer | ✓ | ✓ |  | 4.09 |
| D13 | tracing | answer | answer | ✓ | ✓ |  | 6.93 |
| D14 | tracing | answer | answer | ✓ | ✓ |  | 7.29 |
| D15 | tracing | answer | answer | ✓ | ✓ |  | 7.09 |
| D16 | discovery | answer | answer | ✓ | ✓ |  | 5.41 |
| D17 | discovery | answer | answer | ✓ | ✓ |  | 6.33 |
| D18 | discovery | answer | answer | ✓ | ✓ |  | 5.51 |
| D19 | feasibility | estimate | estimate | ✓ | ✓ |  | 9.76 |
| D20 | feasibility | estimate | estimate | ✓ | ✓ |  | 8.52 |
| D21 | feasibility | estimate | estimate | ✓ | ✓ |  | 9.24 |
| D22 | feasibility | estimate | estimate | ✓ | ✓ |  | 9.03 |
| D23 | feasibility | estimate | estimate | ✓ | ✓ |  | 6.45 |
| D24 | action | propose | propose | ✓ | ✓ |  | 7.7 |
| D25 | action | propose | propose | ✓ | ✓ |  | 5.15 |
| D26 | action | propose | propose | ✓ | ✓ |  | 7.64 |
| D27 | action | reject | reject | ✓ | ✓ |  | 7.83 |
| D28 | action | propose | propose | ✓ | ✓ |  | 5.57 |
| D29 | ambiguous | clarify | clarify | ✓ | ✓ |  | 5.05 |
| D30 | ambiguous | clarify | clarify | ✓ | ✓ |  | 8.23 |
| D31 | ambiguous | clarify | clarify | ✓ | ✓ |  | 7.52 |
| D32 | unanswerable | refuse | refuse | ✓ | ✓ |  | 5.86 |
| D33 | unanswerable | refuse | refuse | ✓ | ✓ |  | 4.61 |
| D34 | unanswerable | refuse | refuse | ✓ | ✓ |  | 5.27 |
| D35 | unanswerable | refuse | refuse | ✓ | ✓ |  | 6.84 |
| D36 | unanswerable | refuse | refuse | ✓ | ✓ |  | 9.46 |
