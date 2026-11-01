# Evaluation run `20261101-2350-dev-gpt-5.6-luna-base-s4b`

Set **dev** · model `gpt-5.6-luna` · reasoning low · critic **off** · prompt system v10 · commit `3600933` · 2026-11-01 23:50:05

| Metric | Value |
|---|---|
| Decision accuracy | **100.0%** (36/36) |
| Behaviour accuracy | 100.0% |
| Faithfulness (reply passed the verifier) | 100.0% |
| Unconfirmed side effects | 0 |
| Headline ≤ 3 lines | 100.0% |
| Verifier rejections (repaired) | 0 |
| Latency p50 / p90 | 5.9 s / 8.1 s |
| Cost total / per item | $0.0271 / $0.0008 |

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
| D01 | lookup | answer | answer | ✓ | ✓ |  | 5.28 |
| D02 | lookup | answer | answer | ✓ | ✓ |  | 5.68 |
| D03 | lookup | answer | answer | ✓ | ✓ |  | 6.21 |
| D04 | lookup | answer | answer | ✓ | ✓ |  | 4.1 |
| D05 | lookup | answer | answer | ✓ | ✓ |  | 5.84 |
| D06 | aggregation | answer | answer | ✓ | ✓ |  | 4.92 |
| D07 | aggregation | answer | answer | ✓ | ✓ |  | 4.81 |
| D08 | aggregation | answer | answer | ✓ | ✓ |  | 5.52 |
| D09 | aggregation | answer | answer | ✓ | ✓ |  | 5.88 |
| D10 | judgement | answer | answer | ✓ | ✓ |  | 5.45 |
| D11 | judgement | answer | answer | ✓ | ✓ |  | 4.65 |
| D12 | judgement | answer | answer | ✓ | ✓ |  | 4.14 |
| D13 | tracing | answer | answer | ✓ | ✓ |  | 6.89 |
| D14 | tracing | answer | answer | ✓ | ✓ |  | 6.59 |
| D15 | tracing | answer | answer | ✓ | ✓ |  | 5.21 |
| D16 | discovery | answer | answer | ✓ | ✓ |  | 6.66 |
| D17 | discovery | answer | answer | ✓ | ✓ |  | 6.01 |
| D18 | discovery | answer | answer | ✓ | ✓ |  | 5.27 |
| D19 | feasibility | estimate | estimate | ✓ | ✓ |  | 9.86 |
| D20 | feasibility | estimate | estimate | ✓ | ✓ |  | 8.1 |
| D21 | feasibility | estimate | estimate | ✓ | ✓ |  | 5.87 |
| D22 | feasibility | estimate | estimate | ✓ | ✓ |  | 10.32 |
| D23 | feasibility | estimate | estimate | ✓ | ✓ |  | 7.4 |
| D24 | action | propose | propose | ✓ | ✓ |  | 8.85 |
| D25 | action | propose | propose | ✓ | ✓ |  | 4.5 |
| D26 | action | propose | propose | ✓ | ✓ |  | 8.14 |
| D27 | action | reject | reject | ✓ | ✓ |  | 6.95 |
| D28 | action | propose | propose | ✓ | ✓ |  | 5.55 |
| D29 | ambiguous | clarify | clarify | ✓ | ✓ |  | 5.9 |
| D30 | ambiguous | clarify | clarify | ✓ | ✓ |  | 6.74 |
| D31 | ambiguous | clarify | clarify | ✓ | ✓ |  | 5.88 |
| D32 | unanswerable | refuse | refuse | ✓ | ✓ |  | 5.41 |
| D33 | unanswerable | refuse | refuse | ✓ | ✓ |  | 4.78 |
| D34 | unanswerable | refuse | refuse | ✓ | ✓ |  | 6.19 |
| D35 | unanswerable | refuse | refuse | ✓ | ✓ |  | 5.83 |
| D36 | unanswerable | refuse | refuse | ✓ | ✓ |  | 6.67 |
