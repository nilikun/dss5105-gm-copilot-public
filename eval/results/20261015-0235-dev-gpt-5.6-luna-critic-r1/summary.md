# Evaluation run `20261015-0235-dev-gpt-5.6-luna-critic-r1`

Set **dev** · model `gpt-5.6-luna` · reasoning low · critic **on** · prompt system v4 · commit `44d22e8` · 2026-10-15 02:35:18 · re-scored 2026-10-15 22:24:36 with the current scorer

| Metric | Value |
|---|---|
| Decision accuracy | **91.7%** (33/36) |
| Behaviour accuracy | 91.7% |
| Faithfulness (reply passed the verifier) | 100.0% |
| Unconfirmed side effects | 0 |
| Headline ≤ 3 lines | 100.0% |
| Verifier rejections (repaired) | 1 |
| Latency p50 / p90 | 8.9 s / 20.2 s |
| Cost total / per item | $0.0443 / $0.0012 |

## Per category

| Category | n | Decision |
|---|---|---|
| lookup | 5 | 100.0% |
| aggregation | 4 | 100.0% |
| judgement | 3 | 100.0% |
| tracing | 3 | 66.7% |
| discovery | 3 | 100.0% |
| feasibility | 5 | 80.0% |
| action | 5 | 100.0% |
| ambiguous | 3 | 100.0% |
| unanswerable | 5 | 80.0% |

## Behaviour (expected → got)

| Expected | Got | n |
|---|---|---|
| answer | answer | 17 |
| answer | clarify | 1 |
| clarify | clarify | 3 |
| estimate | clarify | 1 |
| estimate | estimate | 4 |
| propose | propose | 4 |
| refuse | answer | 1 |
| refuse | refuse | 4 |
| reject | reject | 1 |

## Items

| ID | Category | Expected | Got | Decision | Faithful | Missing / forbidden | s |
|---|---|---|---|---|---|---|---|
| D01 | lookup | answer | answer | ✓ | ✓ |  | 6.89 |
| D02 | lookup | answer | answer | ✓ | ✓ |  | 13.97 |
| D03 | lookup | answer | answer | ✓ | ✓ |  | 7.84 |
| D04 | lookup | answer | answer | ✓ | ✓ |  | 5.55 |
| D05 | lookup | answer | answer | ✓ | ✓ |  | 5.64 |
| D06 | aggregation | answer | answer | ✓ | ✓ |  | 7.96 |
| D07 | aggregation | answer | answer | ✓ | ✓ |  | 6.78 |
| D08 | aggregation | answer | answer | ✓ | ✓ |  | 7.57 |
| D09 | aggregation | answer | answer | ✓ | ✓ |  | 6.18 |
| D10 | judgement | answer | answer | ✓ | ✓ |  | 6.39 |
| D11 | judgement | answer | answer | ✓ | ✓ |  | 7.27 |
| D12 | judgement | answer | answer | ✓ | ✓ |  | 8.96 |
| D13 | tracing | answer | answer | ✓ | ✓ |  | 20.34 |
| D14 | tracing | answer | answer | ✓ | ✓ |  | 10.86 |
| D15 | tracing | answer | clarify | ✗ | ✓ |  | 12.76 |
| D16 | discovery | answer | answer | ✓ | ✓ |  | 8.13 |
| D17 | discovery | answer | answer | ✓ | ✓ |  | 6.32 |
| D18 | discovery | answer | answer | ✓ | ✓ |  | 15.71 |
| D19 | feasibility | estimate | estimate | ✓ | ✓ |  | 21.5 |
| D20 | feasibility | estimate | estimate | ✓ | ✓ |  | 19.2 |
| D21 | feasibility | estimate | clarify | ✗ | ✓ |  | 22.81 |
| D22 | feasibility | estimate | estimate | ✓ | ✓ |  | 13.64 |
| D23 | feasibility | estimate | estimate | ✓ | ✓ |  | 15.45 |
| D24 | action | propose | propose | ✓ | ✓ |  | 10.85 |
| D25 | action | propose | propose | ✓ | ✓ |  | 6.76 |
| D26 | action | propose | propose | ✓ | ✓ |  | 20.17 |
| D27 | action | reject | reject | ✓ | ✓ |  | 10.08 |
| D28 | action | propose | propose | ✓ | ✓ |  | 16.59 |
| D29 | ambiguous | clarify | clarify | ✓ | ✓ |  | 7.57 |
| D30 | ambiguous | clarify | clarify | ✓ | ✓ |  | 8.27 |
| D31 | ambiguous | clarify | clarify | ✓ | ✓ |  | 6.23 |
| D32 | unanswerable | refuse | refuse | ✓ | ✓ |  | 7.86 |
| D33 | unanswerable | refuse | refuse | ✓ | ✓ |  | 15.29 |
| D34 | unanswerable | refuse | refuse | ✓ | ✓ |  | 8.89 |
| D35 | unanswerable | refuse | answer | ✗ | ✓ |  | 15.17 |
| D36 | unanswerable | refuse | refuse | ✓ | ✓ |  | 16.03 |
