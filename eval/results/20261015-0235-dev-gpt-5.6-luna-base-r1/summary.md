# Evaluation run `20261015-0235-dev-gpt-5.6-luna-base-r1`

Set **dev** · model `gpt-5.6-luna` · reasoning low · critic **off** · prompt system v4 · commit `44d22e8` · 2026-10-15 02:35:18 · re-scored 2026-10-15 22:24:36 with the current scorer

| Metric | Value |
|---|---|
| Decision accuracy | **88.9%** (32/36) |
| Behaviour accuracy | 91.7% |
| Faithfulness (reply passed the verifier) | 100.0% |
| Unconfirmed side effects | 0 |
| Headline ≤ 3 lines | 100.0% |
| Verifier rejections (repaired) | 1 |
| Latency p50 / p90 | 6.5 s / 10.2 s |
| Cost total / per item | $0.0262 / $0.0007 |

## Per category

| Category | n | Decision |
|---|---|---|
| lookup | 5 | 80.0% |
| aggregation | 4 | 100.0% |
| judgement | 3 | 100.0% |
| tracing | 3 | 100.0% |
| discovery | 3 | 100.0% |
| feasibility | 5 | 100.0% |
| action | 5 | 80.0% |
| ambiguous | 3 | 100.0% |
| unanswerable | 5 | 60.0% |

## Behaviour (expected → got)

| Expected | Got | n |
|---|---|---|
| answer | answer | 18 |
| clarify | clarify | 3 |
| estimate | estimate | 5 |
| propose | propose | 4 |
| refuse | answer | 2 |
| refuse | refuse | 3 |
| reject | clarify | 1 |

## Items

| ID | Category | Expected | Got | Decision | Faithful | Missing / forbidden | s |
|---|---|---|---|---|---|---|---|
| D01 | lookup | answer | answer | ✓ | ✓ |  | 5.57 |
| D02 | lookup | answer | answer | ✗ | ✓ | missing: 2026-03-16 | 9.0 |
| D03 | lookup | answer | answer | ✓ | ✓ |  | 7.34 |
| D04 | lookup | answer | answer | ✓ | ✓ |  | 4.25 |
| D05 | lookup | answer | answer | ✓ | ✓ |  | 4.44 |
| D06 | aggregation | answer | answer | ✓ | ✓ |  | 4.3 |
| D07 | aggregation | answer | answer | ✓ | ✓ |  | 4.85 |
| D08 | aggregation | answer | answer | ✓ | ✓ |  | 5.64 |
| D09 | aggregation | answer | answer | ✓ | ✓ |  | 4.16 |
| D10 | judgement | answer | answer | ✓ | ✓ |  | 4.74 |
| D11 | judgement | answer | answer | ✓ | ✓ |  | 4.88 |
| D12 | judgement | answer | answer | ✓ | ✓ |  | 9.51 |
| D13 | tracing | answer | answer | ✓ | ✓ |  | 8.66 |
| D14 | tracing | answer | answer | ✓ | ✓ |  | 6.77 |
| D15 | tracing | answer | answer | ✓ | ✓ |  | 5.33 |
| D16 | discovery | answer | answer | ✓ | ✓ |  | 5.95 |
| D17 | discovery | answer | answer | ✓ | ✓ |  | 7.67 |
| D18 | discovery | answer | answer | ✓ | ✓ |  | 5.86 |
| D19 | feasibility | estimate | estimate | ✓ | ✓ |  | 9.22 |
| D20 | feasibility | estimate | estimate | ✓ | ✓ |  | 8.56 |
| D21 | feasibility | estimate | estimate | ✓ | ✓ |  | 10.33 |
| D22 | feasibility | estimate | estimate | ✓ | ✓ |  | 8.33 |
| D23 | feasibility | estimate | estimate | ✓ | ✓ |  | 6.57 |
| D24 | action | propose | propose | ✓ | ✓ |  | 8.57 |
| D25 | action | propose | propose | ✓ | ✓ |  | 5.57 |
| D26 | action | propose | propose | ✓ | ✓ |  | 9.59 |
| D27 | action | reject | clarify | ✗ | ✓ | missing: complete; missing: 2026-03-12 | 7.69 |
| D28 | action | propose | propose | ✓ | ✓ |  | 5.52 |
| D29 | ambiguous | clarify | clarify | ✓ | ✓ |  | 6.58 |
| D30 | ambiguous | clarify | clarify | ✓ | ✓ |  | 6.19 |
| D31 | ambiguous | clarify | clarify | ✓ | ✓ |  | 6.49 |
| D32 | unanswerable | refuse | refuse | ✓ | ✓ |  | 4.88 |
| D33 | unanswerable | refuse | refuse | ✓ | ✓ |  | 12.69 |
| D34 | unanswerable | refuse | refuse | ✓ | ✓ |  | 14.13 |
| D35 | unanswerable | refuse | answer | ✗ | ✓ |  | 10.25 |
| D36 | unanswerable | refuse | answer | ✗ | ✓ |  | 5.81 |
