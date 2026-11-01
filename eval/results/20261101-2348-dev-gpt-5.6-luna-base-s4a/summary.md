# Evaluation run `20261101-2348-dev-gpt-5.6-luna-base-s4a`

Set **dev** · model `gpt-5.6-luna` · reasoning low · critic **off** · prompt system v10 · commit `3600933` · 2026-11-01 23:48:45

| Metric | Value |
|---|---|
| Decision accuracy | **100.0%** (36/36) |
| Behaviour accuracy | 100.0% |
| Faithfulness (reply passed the verifier) | 100.0% |
| Unconfirmed side effects | 0 |
| Headline ≤ 3 lines | 100.0% |
| Verifier rejections (repaired) | 0 |
| Latency p50 / p90 | 5.8 s / 8.1 s |
| Cost total / per item | $0.0273 / $0.0008 |

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
| D01 | lookup | answer | answer | ✓ | ✓ |  | 5.24 |
| D02 | lookup | answer | answer | ✓ | ✓ |  | 5.97 |
| D03 | lookup | answer | answer | ✓ | ✓ |  | 5.93 |
| D04 | lookup | answer | answer | ✓ | ✓ |  | 4.82 |
| D05 | lookup | answer | answer | ✓ | ✓ |  | 4.42 |
| D06 | aggregation | answer | answer | ✓ | ✓ |  | 5.09 |
| D07 | aggregation | answer | answer | ✓ | ✓ |  | 5.02 |
| D08 | aggregation | answer | answer | ✓ | ✓ |  | 5.51 |
| D09 | aggregation | answer | answer | ✓ | ✓ |  | 4.94 |
| D10 | judgement | answer | answer | ✓ | ✓ |  | 4.62 |
| D11 | judgement | answer | answer | ✓ | ✓ |  | 4.53 |
| D12 | judgement | answer | answer | ✓ | ✓ |  | 5.65 |
| D13 | tracing | answer | answer | ✓ | ✓ |  | 6.97 |
| D14 | tracing | answer | answer | ✓ | ✓ |  | 6.42 |
| D15 | tracing | answer | answer | ✓ | ✓ |  | 5.72 |
| D16 | discovery | answer | answer | ✓ | ✓ |  | 5.91 |
| D17 | discovery | answer | answer | ✓ | ✓ |  | 5.3 |
| D18 | discovery | answer | answer | ✓ | ✓ |  | 5.84 |
| D19 | feasibility | estimate | estimate | ✓ | ✓ |  | 8.12 |
| D20 | feasibility | estimate | estimate | ✓ | ✓ |  | 8.71 |
| D21 | feasibility | estimate | estimate | ✓ | ✓ |  | 5.79 |
| D22 | feasibility | estimate | estimate | ✓ | ✓ |  | 8.16 |
| D23 | feasibility | estimate | estimate | ✓ | ✓ |  | 6.08 |
| D24 | action | propose | propose | ✓ | ✓ |  | 9.33 |
| D25 | action | propose | propose | ✓ | ✓ |  | 4.79 |
| D26 | action | propose | propose | ✓ | ✓ |  | 8.06 |
| D27 | action | reject | reject | ✓ | ✓ |  | 7.35 |
| D28 | action | propose | propose | ✓ | ✓ |  | 5.3 |
| D29 | ambiguous | clarify | clarify | ✓ | ✓ |  | 5.23 |
| D30 | ambiguous | clarify | clarify | ✓ | ✓ |  | 6.3 |
| D31 | ambiguous | clarify | clarify | ✓ | ✓ |  | 5.22 |
| D32 | unanswerable | refuse | refuse | ✓ | ✓ |  | 5.35 |
| D33 | unanswerable | refuse | refuse | ✓ | ✓ |  | 5.0 |
| D34 | unanswerable | refuse | refuse | ✓ | ✓ |  | 7.53 |
| D35 | unanswerable | refuse | refuse | ✓ | ✓ |  | 6.27 |
| D36 | unanswerable | refuse | refuse | ✓ | ✓ |  | 6.66 |
