# Evaluation run `20261029-1805-dev-gpt-5.6-luna-base-v9c`

Set **dev** · model `gpt-5.6-luna` · reasoning low · critic **off** · prompt system v9 · commit `b52acad` · 2026-10-29 18:05:11

| Metric | Value |
|---|---|
| Decision accuracy | **100.0%** (36/36) |
| Behaviour accuracy | 100.0% |
| Faithfulness (reply passed the verifier) | 100.0% |
| Unconfirmed side effects | 0 |
| Headline ≤ 3 lines | 100.0% |
| Verifier rejections (repaired) | 0 |
| Latency p50 / p90 | 5.7 s / 8.2 s |
| Cost total / per item | $0.0254 / $0.0007 |

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
| D01 | lookup | answer | answer | ✓ | ✓ |  | 5.13 |
| D02 | lookup | answer | answer | ✓ | ✓ |  | 5.69 |
| D03 | lookup | answer | answer | ✓ | ✓ |  | 5.46 |
| D04 | lookup | answer | answer | ✓ | ✓ |  | 4.07 |
| D05 | lookup | answer | answer | ✓ | ✓ |  | 3.8 |
| D06 | aggregation | answer | answer | ✓ | ✓ |  | 4.71 |
| D07 | aggregation | answer | answer | ✓ | ✓ |  | 5.02 |
| D08 | aggregation | answer | answer | ✓ | ✓ |  | 6.71 |
| D09 | aggregation | answer | answer | ✓ | ✓ |  | 4.54 |
| D10 | judgement | answer | answer | ✓ | ✓ |  | 3.97 |
| D11 | judgement | answer | answer | ✓ | ✓ |  | 3.46 |
| D12 | judgement | answer | answer | ✓ | ✓ |  | 4.55 |
| D13 | tracing | answer | answer | ✓ | ✓ |  | 9.76 |
| D14 | tracing | answer | answer | ✓ | ✓ |  | 7.59 |
| D15 | tracing | answer | answer | ✓ | ✓ |  | 5.39 |
| D16 | discovery | answer | answer | ✓ | ✓ |  | 5.92 |
| D17 | discovery | answer | answer | ✓ | ✓ |  | 8.15 |
| D18 | discovery | answer | answer | ✓ | ✓ |  | 6.55 |
| D19 | feasibility | estimate | estimate | ✓ | ✓ |  | 8.17 |
| D20 | feasibility | estimate | estimate | ✓ | ✓ |  | 8.28 |
| D21 | feasibility | estimate | estimate | ✓ | ✓ |  | 5.47 |
| D22 | feasibility | estimate | estimate | ✓ | ✓ |  | 6.84 |
| D23 | feasibility | estimate | estimate | ✓ | ✓ |  | 7.73 |
| D24 | action | propose | propose | ✓ | ✓ |  | 5.01 |
| D25 | action | propose | propose | ✓ | ✓ |  | 3.55 |
| D26 | action | propose | propose | ✓ | ✓ |  | 7.07 |
| D27 | action | reject | reject | ✓ | ✓ |  | 7.94 |
| D28 | action | propose | propose | ✓ | ✓ |  | 4.62 |
| D29 | ambiguous | clarify | clarify | ✓ | ✓ |  | 8.21 |
| D30 | ambiguous | clarify | clarify | ✓ | ✓ |  | 6.01 |
| D31 | ambiguous | clarify | clarify | ✓ | ✓ |  | 5.69 |
| D32 | unanswerable | refuse | refuse | ✓ | ✓ |  | 4.21 |
| D33 | unanswerable | refuse | refuse | ✓ | ✓ |  | 4.79 |
| D34 | unanswerable | refuse | refuse | ✓ | ✓ |  | 10.4 |
| D35 | unanswerable | refuse | refuse | ✓ | ✓ |  | 7.31 |
| D36 | unanswerable | refuse | refuse | ✓ | ✓ |  | 5.75 |
