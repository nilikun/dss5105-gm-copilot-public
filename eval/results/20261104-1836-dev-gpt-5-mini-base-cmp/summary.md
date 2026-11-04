# Evaluation run `20261104-1836-dev-gpt-5-mini-base-cmp`

Set **dev** · model `gpt-5-mini` · reasoning low · critic **off** · prompt system v10 · commit `a180488` · 2026-11-04 18:36:37

| Metric | Value |
|---|---|
| Decision accuracy | **100.0%** (36/36) |
| Behaviour accuracy | 100.0% |
| Faithfulness (reply passed the verifier) | 100.0% |
| Unconfirmed side effects | 0 |
| Headline ≤ 3 lines | 100.0% |
| Verifier rejections (repaired) | 3 |
| Latency p50 / p90 | 10.5 s / 17.6 s |
| Cost total / per item | $0.0572 / $0.0016 |

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
| D01 | lookup | answer | answer | ✓ | ✓ |  | 8.84 |
| D02 | lookup | answer | answer | ✓ | ✓ |  | 12.08 |
| D03 | lookup | answer | answer | ✓ | ✓ |  | 13.29 |
| D04 | lookup | answer | answer | ✓ | ✓ |  | 8.59 |
| D05 | lookup | answer | answer | ✓ | ✓ |  | 8.16 |
| D06 | aggregation | answer | answer | ✓ | ✓ |  | 12.65 |
| D07 | aggregation | answer | answer | ✓ | ✓ |  | 10.4 |
| D08 | aggregation | answer | answer | ✓ | ✓ |  | 12.88 |
| D09 | aggregation | answer | answer | ✓ | ✓ |  | 10.57 |
| D10 | judgement | answer | answer | ✓ | ✓ |  | 10.41 |
| D11 | judgement | answer | answer | ✓ | ✓ |  | 11.57 |
| D12 | judgement | answer | answer | ✓ | ✓ |  | 9.93 |
| D13 | tracing | answer | answer | ✓ | ✓ |  | 25.99 |
| D14 | tracing | answer | answer | ✓ | ✓ |  | 10.31 |
| D15 | tracing | answer | answer | ✓ | ✓ |  | 10.42 |
| D16 | discovery | answer | answer | ✓ | ✓ |  | 10.05 |
| D17 | discovery | answer | answer | ✓ | ✓ |  | 8.84 |
| D18 | discovery | answer | answer | ✓ | ✓ |  | 10.54 |
| D19 | feasibility | estimate | estimate | ✓ | ✓ |  | 14.82 |
| D20 | feasibility | estimate | estimate | ✓ | ✓ |  | 12.44 |
| D21 | feasibility | estimate | estimate | ✓ | ✓ |  | 15.87 |
| D22 | feasibility | estimate | estimate | ✓ | ✓ |  | 15.57 |
| D23 | feasibility | estimate | estimate | ✓ | ✓ |  | 9.83 |
| D24 | action | propose | propose | ✓ | ✓ |  | 9.2 |
| D25 | action | propose | propose | ✓ | ✓ |  | 7.87 |
| D26 | action | propose | propose | ✓ | ✓ |  | 11.54 |
| D27 | action | reject | reject | ✓ | ✓ |  | 17.64 |
| D28 | action | propose | propose | ✓ | ✓ |  | 8.7 |
| D29 | ambiguous | clarify | clarify | ✓ | ✓ |  | 10.32 |
| D30 | ambiguous | clarify | clarify | ✓ | ✓ |  | 9.7 |
| D31 | ambiguous | clarify | clarify | ✓ | ✓ |  | 9.61 |
| D32 | unanswerable | refuse | refuse | ✓ | ✓ |  | 10.88 |
| D33 | unanswerable | refuse | refuse | ✓ | ✓ |  | 21.61 |
| D34 | unanswerable | refuse | refuse | ✓ | ✓ |  | 19.64 |
| D35 | unanswerable | refuse | refuse | ✓ | ✓ |  | 9.05 |
| D36 | unanswerable | refuse | refuse | ✓ | ✓ |  | 16.74 |
