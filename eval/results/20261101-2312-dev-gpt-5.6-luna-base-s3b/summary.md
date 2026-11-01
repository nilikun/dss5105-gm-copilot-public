# Evaluation run `20261101-2312-dev-gpt-5.6-luna-base-s3b`

Set **dev** · model `gpt-5.6-luna` · reasoning low · critic **off** · prompt system v10 · commit `5f5b43e` · 2026-11-01 23:12:06

| Metric | Value |
|---|---|
| Decision accuracy | **100.0%** (36/36) |
| Behaviour accuracy | 100.0% |
| Faithfulness (reply passed the verifier) | 100.0% |
| Unconfirmed side effects | 0 |
| Headline ≤ 3 lines | 100.0% |
| Verifier rejections (repaired) | 0 |
| Latency p50 / p90 | 5.7 s / 8.8 s |
| Cost total / per item | $0.0270 / $0.0008 |

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
| D01 | lookup | answer | answer | ✓ | ✓ |  | 5.02 |
| D02 | lookup | answer | answer | ✓ | ✓ |  | 8.82 |
| D03 | lookup | answer | answer | ✓ | ✓ |  | 5.61 |
| D04 | lookup | answer | answer | ✓ | ✓ |  | 4.17 |
| D05 | lookup | answer | answer | ✓ | ✓ |  | 4.61 |
| D06 | aggregation | answer | answer | ✓ | ✓ |  | 4.91 |
| D07 | aggregation | answer | answer | ✓ | ✓ |  | 3.9 |
| D08 | aggregation | answer | answer | ✓ | ✓ |  | 5.4 |
| D09 | aggregation | answer | answer | ✓ | ✓ |  | 4.9 |
| D10 | judgement | answer | answer | ✓ | ✓ |  | 3.91 |
| D11 | judgement | answer | answer | ✓ | ✓ |  | 5.66 |
| D12 | judgement | answer | answer | ✓ | ✓ |  | 4.45 |
| D13 | tracing | answer | answer | ✓ | ✓ |  | 5.82 |
| D14 | tracing | answer | answer | ✓ | ✓ |  | 6.64 |
| D15 | tracing | answer | answer | ✓ | ✓ |  | 4.88 |
| D16 | discovery | answer | answer | ✓ | ✓ |  | 5.67 |
| D17 | discovery | answer | answer | ✓ | ✓ |  | 5.62 |
| D18 | discovery | answer | answer | ✓ | ✓ |  | 6.72 |
| D19 | feasibility | estimate | estimate | ✓ | ✓ |  | 10.23 |
| D20 | feasibility | estimate | estimate | ✓ | ✓ |  | 8.67 |
| D21 | feasibility | estimate | estimate | ✓ | ✓ |  | 6.95 |
| D22 | feasibility | estimate | estimate | ✓ | ✓ |  | 8.47 |
| D23 | feasibility | estimate | estimate | ✓ | ✓ |  | 5.7 |
| D24 | action | propose | propose | ✓ | ✓ |  | 6.07 |
| D25 | action | propose | propose | ✓ | ✓ |  | 4.7 |
| D26 | action | propose | propose | ✓ | ✓ |  | 7.06 |
| D27 | action | reject | reject | ✓ | ✓ |  | 9.36 |
| D28 | action | propose | propose | ✓ | ✓ |  | 6.64 |
| D29 | ambiguous | clarify | clarify | ✓ | ✓ |  | 4.74 |
| D30 | ambiguous | clarify | clarify | ✓ | ✓ |  | 6.15 |
| D31 | ambiguous | clarify | clarify | ✓ | ✓ |  | 5.31 |
| D32 | unanswerable | refuse | refuse | ✓ | ✓ |  | 11.01 |
| D33 | unanswerable | refuse | refuse | ✓ | ✓ |  | 5.44 |
| D34 | unanswerable | refuse | refuse | ✓ | ✓ |  | 5.88 |
| D35 | unanswerable | refuse | refuse | ✓ | ✓ |  | 6.46 |
| D36 | unanswerable | refuse | refuse | ✓ | ✓ |  | 6.73 |
