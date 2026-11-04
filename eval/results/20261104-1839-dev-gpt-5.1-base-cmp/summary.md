# Evaluation run `20261104-1839-dev-gpt-5.1-base-cmp`

Set **dev** · model `gpt-5.1` · reasoning low · critic **off** · prompt system v10 · commit `a180488` · 2026-11-04 18:39:22

| Metric | Value |
|---|---|
| Decision accuracy | **97.2%** (35/36) |
| Behaviour accuracy | 100.0% |
| Faithfulness (reply passed the verifier) | 100.0% |
| Unconfirmed side effects | 0 |
| Headline ≤ 3 lines | 100.0% |
| Verifier rejections (repaired) | 0 |
| Latency p50 / p90 | 7.9 s / 12.0 s |
| Cost total / per item | $0.0367 / $0.0010 |

## Per category

| Category | n | Decision |
|---|---|---|
| lookup | 5 | 100.0% |
| aggregation | 4 | 100.0% |
| judgement | 3 | 100.0% |
| tracing | 3 | 100.0% |
| discovery | 3 | 100.0% |
| feasibility | 5 | 100.0% |
| action | 5 | 80.0% |
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
| D01 | lookup | answer | answer | ✓ | ✓ |  | 5.96 |
| D02 | lookup | answer | answer | ✓ | ✓ |  | 7.25 |
| D03 | lookup | answer | answer | ✓ | ✓ |  | 9.06 |
| D04 | lookup | answer | answer | ✓ | ✓ |  | 6.25 |
| D05 | lookup | answer | answer | ✓ | ✓ |  | 5.95 |
| D06 | aggregation | answer | answer | ✓ | ✓ |  | 5.73 |
| D07 | aggregation | answer | answer | ✓ | ✓ |  | 8.04 |
| D08 | aggregation | answer | answer | ✓ | ✓ |  | 10.03 |
| D09 | aggregation | answer | answer | ✓ | ✓ |  | 6.22 |
| D10 | judgement | answer | answer | ✓ | ✓ |  | 6.31 |
| D11 | judgement | answer | answer | ✓ | ✓ |  | 8.42 |
| D12 | judgement | answer | answer | ✓ | ✓ |  | 8.12 |
| D13 | tracing | answer | answer | ✓ | ✓ |  | 9.65 |
| D14 | tracing | answer | answer | ✓ | ✓ |  | 8.03 |
| D15 | tracing | answer | answer | ✓ | ✓ |  | 8.48 |
| D16 | discovery | answer | answer | ✓ | ✓ |  | 9.01 |
| D17 | discovery | answer | answer | ✓ | ✓ |  | 5.32 |
| D18 | discovery | answer | answer | ✓ | ✓ |  | 6.56 |
| D19 | feasibility | estimate | estimate | ✓ | ✓ |  | 11.74 |
| D20 | feasibility | estimate | estimate | ✓ | ✓ |  | 11.67 |
| D21 | feasibility | estimate | estimate | ✓ | ✓ |  | 13.2 |
| D22 | feasibility | estimate | estimate | ✓ | ✓ |  | 10.72 |
| D23 | feasibility | estimate | estimate | ✓ | ✓ |  | 7.87 |
| D24 | action | propose | propose | ✓ | ✓ |  | 7.62 |
| D25 | action | propose | propose | ✗ | ✓ | missing: confirm | 5.67 |
| D26 | action | propose | propose | ✓ | ✓ |  | 12.94 |
| D27 | action | reject | reject | ✓ | ✓ |  | 12.81 |
| D28 | action | propose | propose | ✓ | ✓ |  | 6.87 |
| D29 | ambiguous | clarify | clarify | ✓ | ✓ |  | 6.1 |
| D30 | ambiguous | clarify | clarify | ✓ | ✓ |  | 6.12 |
| D31 | ambiguous | clarify | clarify | ✓ | ✓ |  | 6.66 |
| D32 | unanswerable | refuse | refuse | ✓ | ✓ |  | 8.68 |
| D33 | unanswerable | refuse | refuse | ✓ | ✓ |  | 6.45 |
| D34 | unanswerable | refuse | refuse | ✓ | ✓ |  | 12.01 |
| D35 | unanswerable | refuse | refuse | ✓ | ✓ |  | 7.64 |
| D36 | unanswerable | refuse | refuse | ✓ | ✓ |  | 9.45 |
