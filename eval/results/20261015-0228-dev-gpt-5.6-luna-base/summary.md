# Evaluation run `20261015-0228-dev-gpt-5.6-luna-base`

Set **dev** · model `gpt-5.6-luna` · reasoning low · critic **off** · prompt system v3 · commit `03f5a01` · 2026-10-15 02:28:48

| Metric | Value |
|---|---|
| Decision accuracy | **83.3%** (30/36) |
| Behaviour accuracy | 97.2% |
| Faithfulness (reply passed the verifier) | 100.0% |
| Unconfirmed side effects | 0 |
| Headline ≤ 3 lines | 100.0% |
| Verifier rejections (repaired) | 1 |
| Latency p50 / p90 | 6.8 s / 10.7 s |
| Cost total / per item | $0.0269 / $0.0008 |

## Per category

| Category | n | Decision |
|---|---|---|
| lookup | 5 | 60.0% |
| aggregation | 4 | 100.0% |
| judgement | 3 | 66.7% |
| tracing | 3 | 100.0% |
| discovery | 3 | 100.0% |
| feasibility | 5 | 80.0% |
| action | 5 | 100.0% |
| ambiguous | 3 | 100.0% |
| unanswerable | 5 | 60.0% |

## Behaviour (expected → got)

| Expected | Got | n |
|---|---|---|
| answer | answer | 18 |
| clarify | clarify | 3 |
| estimate | clarify | 1 |
| estimate | estimate | 4 |
| propose | propose | 4 |
| refuse | refuse | 5 |
| reject | reject | 1 |

## Items

| ID | Category | Expected | Got | Decision | Faithful | Missing / forbidden | s |
|---|---|---|---|---|---|---|---|
| D01 | lookup | answer | answer | ✗ | ✓ | missing: 15 | 5.54 |
| D02 | lookup | answer | answer | ✗ | ✓ | missing: ORD-107 | 10.69 |
| D03 | lookup | answer | answer | ✓ | ✓ |  | 6.92 |
| D04 | lookup | answer | answer | ✓ | ✓ |  | 5.19 |
| D05 | lookup | answer | answer | ✓ | ✓ |  | 4.63 |
| D06 | aggregation | answer | answer | ✓ | ✓ |  | 4.88 |
| D07 | aggregation | answer | answer | ✓ | ✓ |  | 5.75 |
| D08 | aggregation | answer | answer | ✓ | ✓ |  | 5.97 |
| D09 | aggregation | answer | answer | ✓ | ✓ |  | 5.34 |
| D10 | judgement | answer | answer | ✗ | ✓ | missing: not normal | 4.53 |
| D11 | judgement | answer | answer | ✓ | ✓ |  | 5.65 |
| D12 | judgement | answer | answer | ✓ | ✓ |  | 4.78 |
| D13 | tracing | answer | answer | ✓ | ✓ |  | 7.41 |
| D14 | tracing | answer | answer | ✓ | ✓ |  | 6.91 |
| D15 | tracing | answer | answer | ✓ | ✓ |  | 6.52 |
| D16 | discovery | answer | answer | ✓ | ✓ |  | 6.49 |
| D17 | discovery | answer | answer | ✓ | ✓ |  | 8.69 |
| D18 | discovery | answer | answer | ✓ | ✓ |  | 5.26 |
| D19 | feasibility | estimate | estimate | ✓ | ✓ |  | 11.82 |
| D20 | feasibility | estimate | estimate | ✓ | ✓ |  | 8.24 |
| D21 | feasibility | estimate | estimate | ✓ | ✓ |  | 8.54 |
| D22 | feasibility | estimate | estimate | ✓ | ✓ |  | 9.17 |
| D23 | feasibility | estimate | clarify | ✗ | ✓ | missing: QuickStitch; missing: 12% | 13.26 |
| D24 | action | propose | propose | ✓ | ✓ |  | 7.9 |
| D25 | action | propose | propose | ✓ | ✓ |  | 5.57 |
| D26 | action | propose | propose | ✓ | ✓ |  | 8.7 |
| D27 | action | reject | reject | ✓ | ✓ |  | 9.8 |
| D28 | action | propose | propose | ✓ | ✓ |  | 7.01 |
| D29 | ambiguous | clarify | clarify | ✓ | ✓ |  | 6.39 |
| D30 | ambiguous | clarify | clarify | ✓ | ✓ |  | 6.5 |
| D31 | ambiguous | clarify | clarify | ✓ | ✓ |  | 6.72 |
| D32 | unanswerable | refuse | refuse | ✓ | ✓ |  | 5.65 |
| D33 | unanswerable | refuse | refuse | ✓ | ✓ |  | 12.34 |
| D34 | unanswerable | refuse | refuse | ✓ | ✓ |  | 6.98 |
| D35 | unanswerable | refuse | refuse | ✗ | ✓ | missing: -44% | 10.21 |
| D36 | unanswerable | refuse | refuse | ✗ | ✓ | missing: 640 | 8.09 |
