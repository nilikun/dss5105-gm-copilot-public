# Evaluation run `20261015-0232-dev-gpt-5.6-luna-base`

Set **dev** · model `gpt-5.6-luna` · reasoning low · critic **off** · prompt system v4 · commit `03f5a01` · 2026-10-15 02:32:20

| Metric | Value |
|---|---|
| Decision accuracy | **88.9%** (32/36) |
| Behaviour accuracy | 97.2% |
| Faithfulness (reply passed the verifier) | 100.0% |
| Unconfirmed side effects | 0 |
| Headline ≤ 3 lines | 100.0% |
| Verifier rejections (repaired) | 0 |
| Latency p50 / p90 | 6.7 s / 10.7 s |
| Cost total / per item | $0.0291 / $0.0008 |

## Per category

| Category | n | Decision |
|---|---|---|
| lookup | 5 | 80.0% |
| aggregation | 4 | 100.0% |
| judgement | 3 | 100.0% |
| tracing | 3 | 100.0% |
| discovery | 3 | 100.0% |
| feasibility | 5 | 80.0% |
| action | 5 | 80.0% |
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
| reject | clarify | 1 |

## Items

| ID | Category | Expected | Got | Decision | Faithful | Missing / forbidden | s |
|---|---|---|---|---|---|---|---|
| D01 | lookup | answer | answer | ✓ | ✓ |  | 7.16 |
| D02 | lookup | answer | answer | ✗ | ✓ | missing: 2026-03-16 | 11.8 |
| D03 | lookup | answer | answer | ✓ | ✓ |  | 6.3 |
| D04 | lookup | answer | answer | ✓ | ✓ |  | 7.04 |
| D05 | lookup | answer | answer | ✓ | ✓ |  | 5.34 |
| D06 | aggregation | answer | answer | ✓ | ✓ |  | 4.95 |
| D07 | aggregation | answer | answer | ✓ | ✓ |  | 5.55 |
| D08 | aggregation | answer | answer | ✓ | ✓ |  | 5.77 |
| D09 | aggregation | answer | answer | ✓ | ✓ |  | 4.88 |
| D10 | judgement | answer | answer | ✓ | ✓ |  | 4.6 |
| D11 | judgement | answer | answer | ✓ | ✓ |  | 4.99 |
| D12 | judgement | answer | answer | ✓ | ✓ |  | 5.19 |
| D13 | tracing | answer | answer | ✓ | ✓ |  | 6.99 |
| D14 | tracing | answer | answer | ✓ | ✓ |  | 6.26 |
| D15 | tracing | answer | answer | ✓ | ✓ |  | 5.82 |
| D16 | discovery | answer | answer | ✓ | ✓ |  | 6.72 |
| D17 | discovery | answer | answer | ✓ | ✓ |  | 7.72 |
| D18 | discovery | answer | answer | ✓ | ✓ |  | 6.54 |
| D19 | feasibility | estimate | estimate | ✓ | ✓ |  | 9.28 |
| D20 | feasibility | estimate | estimate | ✓ | ✓ |  | 9.71 |
| D21 | feasibility | estimate | estimate | ✓ | ✓ |  | 9.94 |
| D22 | feasibility | estimate | estimate | ✓ | ✓ |  | 9.56 |
| D23 | feasibility | estimate | estimate | ✗ | ✓ | missing: 12% | 6.33 |
| D24 | action | propose | propose | ✓ | ✓ |  | 11.99 |
| D25 | action | propose | propose | ✓ | ✓ |  | 5.06 |
| D26 | action | propose | propose | ✓ | ✓ |  | 11.08 |
| D27 | action | reject | clarify | ✗ | ✓ | missing: complete; missing: 2026-03-12 | 7.47 |
| D28 | action | propose | propose | ✓ | ✓ |  | 6.98 |
| D29 | ambiguous | clarify | clarify | ✓ | ✓ |  | 6.25 |
| D30 | ambiguous | clarify | clarify | ✓ | ✓ |  | 6.81 |
| D31 | ambiguous | clarify | clarify | ✓ | ✓ |  | 6.66 |
| D32 | unanswerable | refuse | refuse | ✓ | ✓ |  | 6.05 |
| D33 | unanswerable | refuse | refuse | ✗ | ✓ | missing: no | 6.06 |
| D34 | unanswerable | refuse | refuse | ✓ | ✓ |  | 7.45 |
| D35 | unanswerable | refuse | refuse | ✓ | ✓ |  | 10.69 |
| D36 | unanswerable | refuse | refuse | ✓ | ✓ |  | 7.23 |
