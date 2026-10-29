# Evaluation run `20261029-1802-dev-gpt-5.6-luna-base-v9b`

Set **dev** · model `gpt-5.6-luna` · reasoning low · critic **off** · prompt system v9 · commit `cf24061` · 2026-10-29 18:02:15

| Metric | Value |
|---|---|
| Decision accuracy | **100.0%** (36/36) |
| Behaviour accuracy | 100.0% |
| Faithfulness (reply passed the verifier) | 100.0% |
| Unconfirmed side effects | 0 |
| Headline ≤ 3 lines | 100.0% |
| Verifier rejections (repaired) | 0 |
| Latency p50 / p90 | 6.1 s / 8.6 s |
| Cost total / per item | $0.0274 / $0.0008 |

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
| D01 | lookup | answer | answer | ✓ | ✓ |  | 4.74 |
| D02 | lookup | answer | answer | ✓ | ✓ |  | 8.99 |
| D03 | lookup | answer | answer | ✓ | ✓ |  | 6.0 |
| D04 | lookup | answer | answer | ✓ | ✓ |  | 3.76 |
| D05 | lookup | answer | answer | ✓ | ✓ |  | 3.87 |
| D06 | aggregation | answer | answer | ✓ | ✓ |  | 4.74 |
| D07 | aggregation | answer | answer | ✓ | ✓ |  | 4.26 |
| D08 | aggregation | answer | answer | ✓ | ✓ |  | 6.5 |
| D09 | aggregation | answer | answer | ✓ | ✓ |  | 3.65 |
| D10 | judgement | answer | answer | ✓ | ✓ |  | 4.9 |
| D11 | judgement | answer | answer | ✓ | ✓ |  | 4.39 |
| D12 | judgement | answer | answer | ✓ | ✓ |  | 4.13 |
| D13 | tracing | answer | answer | ✓ | ✓ |  | 6.6 |
| D14 | tracing | answer | answer | ✓ | ✓ |  | 7.39 |
| D15 | tracing | answer | answer | ✓ | ✓ |  | 5.07 |
| D16 | discovery | answer | answer | ✓ | ✓ |  | 6.05 |
| D17 | discovery | answer | answer | ✓ | ✓ |  | 7.47 |
| D18 | discovery | answer | answer | ✓ | ✓ |  | 5.3 |
| D19 | feasibility | estimate | estimate | ✓ | ✓ |  | 7.75 |
| D20 | feasibility | estimate | estimate | ✓ | ✓ |  | 6.92 |
| D21 | feasibility | estimate | estimate | ✓ | ✓ |  | 8.2 |
| D22 | feasibility | estimate | estimate | ✓ | ✓ |  | 7.38 |
| D23 | feasibility | estimate | estimate | ✓ | ✓ |  | 39.58 |
| D24 | action | propose | propose | ✓ | ✓ |  | 7.77 |
| D25 | action | propose | propose | ✓ | ✓ |  | 3.95 |
| D26 | action | propose | propose | ✓ | ✓ |  | 7.26 |
| D27 | action | reject | reject | ✓ | ✓ |  | 8.62 |
| D28 | action | propose | propose | ✓ | ✓ |  | 6.15 |
| D29 | ambiguous | clarify | clarify | ✓ | ✓ |  | 5.58 |
| D30 | ambiguous | clarify | clarify | ✓ | ✓ |  | 6.23 |
| D31 | ambiguous | clarify | clarify | ✓ | ✓ |  | 4.69 |
| D32 | unanswerable | refuse | refuse | ✓ | ✓ |  | 5.55 |
| D33 | unanswerable | refuse | refuse | ✓ | ✓ |  | 4.72 |
| D34 | unanswerable | refuse | refuse | ✓ | ✓ |  | 9.2 |
| D35 | unanswerable | refuse | refuse | ✓ | ✓ |  | 6.08 |
| D36 | unanswerable | refuse | refuse | ✓ | ✓ |  | 7.08 |
