# Evaluation run `20261029-1802-dev-gpt-5.6-luna-base-v9a`

Set **dev** · model `gpt-5.6-luna` · reasoning low · critic **off** · prompt system v9 · commit `cf24061` · 2026-10-29 18:02:15

| Metric | Value |
|---|---|
| Decision accuracy | **97.2%** (35/36) |
| Behaviour accuracy | 100.0% |
| Faithfulness (reply passed the verifier) | 100.0% |
| Unconfirmed side effects | 0 |
| Headline ≤ 3 lines | 100.0% |
| Verifier rejections (repaired) | 1 |
| Latency p50 / p90 | 6.1 s / 7.9 s |
| Cost total / per item | $0.0263 / $0.0007 |

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
| unanswerable | 5 | 80.0% |

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
| D02 | lookup | answer | answer | ✓ | ✓ |  | 6.86 |
| D03 | lookup | answer | answer | ✓ | ✓ |  | 5.94 |
| D04 | lookup | answer | answer | ✓ | ✓ |  | 4.25 |
| D05 | lookup | answer | answer | ✓ | ✓ |  | 4.22 |
| D06 | aggregation | answer | answer | ✓ | ✓ |  | 4.24 |
| D07 | aggregation | answer | answer | ✓ | ✓ |  | 6.42 |
| D08 | aggregation | answer | answer | ✓ | ✓ |  | 6.39 |
| D09 | aggregation | answer | answer | ✓ | ✓ |  | 4.73 |
| D10 | judgement | answer | answer | ✓ | ✓ |  | 3.94 |
| D11 | judgement | answer | answer | ✓ | ✓ |  | 4.03 |
| D12 | judgement | answer | answer | ✓ | ✓ |  | 5.52 |
| D13 | tracing | answer | answer | ✓ | ✓ |  | 7.69 |
| D14 | tracing | answer | answer | ✓ | ✓ |  | 7.19 |
| D15 | tracing | answer | answer | ✓ | ✓ |  | 6.4 |
| D16 | discovery | answer | answer | ✓ | ✓ |  | 5.99 |
| D17 | discovery | answer | answer | ✓ | ✓ |  | 4.71 |
| D18 | discovery | answer | answer | ✓ | ✓ |  | 6.18 |
| D19 | feasibility | estimate | estimate | ✓ | ✓ |  | 9.78 |
| D20 | feasibility | estimate | estimate | ✓ | ✓ |  | 8.97 |
| D21 | feasibility | estimate | estimate | ✓ | ✓ |  | 6.49 |
| D22 | feasibility | estimate | estimate | ✓ | ✓ |  | 6.88 |
| D23 | feasibility | estimate | estimate | ✓ | ✓ |  | 6.58 |
| D24 | action | propose | propose | ✓ | ✓ |  | 5.54 |
| D25 | action | propose | propose | ✓ | ✓ |  | 3.91 |
| D26 | action | propose | propose | ✓ | ✓ |  | 6.72 |
| D27 | action | reject | reject | ✓ | ✓ |  | 5.08 |
| D28 | action | propose | propose | ✓ | ✓ |  | 5.88 |
| D29 | ambiguous | clarify | clarify | ✓ | ✓ |  | 5.56 |
| D30 | ambiguous | clarify | clarify | ✓ | ✓ |  | 4.64 |
| D31 | ambiguous | clarify | clarify | ✓ | ✓ |  | 6.19 |
| D32 | unanswerable | refuse | refuse | ✓ | ✓ |  | 3.95 |
| D33 | unanswerable | refuse | refuse | ✓ | ✓ |  | 7.93 |
| D34 | unanswerable | refuse | refuse | ✓ | ✓ |  | 8.09 |
| D35 | unanswerable | refuse | refuse | ✗ | ✓ | missing: -44% | -48.6% | 6.83 |
| D36 | unanswerable | refuse | refuse | ✓ | ✓ |  | 6.5 |
