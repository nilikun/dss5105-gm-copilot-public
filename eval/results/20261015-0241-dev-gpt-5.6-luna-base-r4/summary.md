# Evaluation run `20261015-0241-dev-gpt-5.6-luna-base-r4`

Set **dev** · model `gpt-5.6-luna` · reasoning low · critic **off** · prompt system v5 · commit `44d22e8` · 2026-10-15 02:41:18 · re-scored 2026-10-15 22:24:36 with the current scorer

| Metric | Value |
|---|---|
| Decision accuracy | **94.4%** (34/36) |
| Behaviour accuracy | 100.0% |
| Faithfulness (reply passed the verifier) | 100.0% |
| Unconfirmed side effects | 0 |
| Headline ≤ 3 lines | 100.0% |
| Verifier rejections (repaired) | 1 |
| Latency p50 / p90 | 6.3 s / 9.4 s |
| Cost total / per item | $0.0287 / $0.0008 |

## Per category

| Category | n | Decision |
|---|---|---|
| lookup | 5 | 80.0% |
| aggregation | 4 | 100.0% |
| judgement | 3 | 100.0% |
| tracing | 3 | 100.0% |
| discovery | 3 | 100.0% |
| feasibility | 5 | 80.0% |
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
| D01 | lookup | answer | answer | ✓ | ✓ |  | 4.75 |
| D02 | lookup | answer | answer | ✗ | ✓ | missing: 2026-03-16 | 10.31 |
| D03 | lookup | answer | answer | ✓ | ✓ |  | 5.98 |
| D04 | lookup | answer | answer | ✓ | ✓ |  | 4.26 |
| D05 | lookup | answer | answer | ✓ | ✓ |  | 4.32 |
| D06 | aggregation | answer | answer | ✓ | ✓ |  | 4.5 |
| D07 | aggregation | answer | answer | ✓ | ✓ |  | 8.69 |
| D08 | aggregation | answer | answer | ✓ | ✓ |  | 5.98 |
| D09 | aggregation | answer | answer | ✓ | ✓ |  | 5.5 |
| D10 | judgement | answer | answer | ✓ | ✓ |  | 4.67 |
| D11 | judgement | answer | answer | ✓ | ✓ |  | 4.09 |
| D12 | judgement | answer | answer | ✓ | ✓ |  | 5.29 |
| D13 | tracing | answer | answer | ✓ | ✓ |  | 5.83 |
| D14 | tracing | answer | answer | ✓ | ✓ |  | 7.29 |
| D15 | tracing | answer | answer | ✓ | ✓ |  | 5.74 |
| D16 | discovery | answer | answer | ✓ | ✓ |  | 5.85 |
| D17 | discovery | answer | answer | ✓ | ✓ |  | 10.64 |
| D18 | discovery | answer | answer | ✓ | ✓ |  | 6.19 |
| D19 | feasibility | estimate | estimate | ✓ | ✓ |  | 9.05 |
| D20 | feasibility | estimate | estimate | ✓ | ✓ |  | 8.83 |
| D21 | feasibility | estimate | estimate | ✓ | ✓ |  | 8.66 |
| D22 | feasibility | estimate | estimate | ✓ | ✓ |  | 9.1 |
| D23 | feasibility | estimate | estimate | ✗ | ✓ | missing: 12% | 5.84 |
| D24 | action | propose | propose | ✓ | ✓ |  | 7.44 |
| D25 | action | propose | propose | ✓ | ✓ |  | 4.49 |
| D26 | action | propose | propose | ✓ | ✓ |  | 9.38 |
| D27 | action | reject | reject | ✓ | ✓ |  | 10.49 |
| D28 | action | propose | propose | ✓ | ✓ |  | 6.3 |
| D29 | ambiguous | clarify | clarify | ✓ | ✓ |  | 5.79 |
| D30 | ambiguous | clarify | clarify | ✓ | ✓ |  | 7.06 |
| D31 | ambiguous | clarify | clarify | ✓ | ✓ |  | 6.47 |
| D32 | unanswerable | refuse | refuse | ✓ | ✓ |  | 7.08 |
| D33 | unanswerable | refuse | refuse | ✓ | ✓ |  | 6.39 |
| D34 | unanswerable | refuse | refuse | ✓ | ✓ |  | 7.54 |
| D35 | unanswerable | refuse | refuse | ✓ | ✓ |  | 6.47 |
| D36 | unanswerable | refuse | refuse | ✓ | ✓ |  | 6.87 |
