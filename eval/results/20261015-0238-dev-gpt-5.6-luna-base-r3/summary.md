# Evaluation run `20261015-0238-dev-gpt-5.6-luna-base-r3`

Set **dev** · model `gpt-5.6-luna` · reasoning low · critic **off** · prompt system v4 · commit `44d22e8` · 2026-10-15 02:38:55 · re-scored 2026-10-15 22:24:36 with the current scorer

| Metric | Value |
|---|---|
| Decision accuracy | **100.0%** (36/36) |
| Behaviour accuracy | 100.0% |
| Faithfulness (reply passed the verifier) | 100.0% |
| Unconfirmed side effects | 0 |
| Headline ≤ 3 lines | 100.0% |
| Verifier rejections (repaired) | 0 |
| Latency p50 / p90 | 6.3 s / 9.3 s |
| Cost total / per item | $0.0277 / $0.0008 |

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
| D01 | lookup | answer | answer | ✓ | ✓ |  | 4.18 |
| D02 | lookup | answer | answer | ✓ | ✓ |  | 10.38 |
| D03 | lookup | answer | answer | ✓ | ✓ |  | 5.84 |
| D04 | lookup | answer | answer | ✓ | ✓ |  | 4.81 |
| D05 | lookup | answer | answer | ✓ | ✓ |  | 4.01 |
| D06 | aggregation | answer | answer | ✓ | ✓ |  | 4.34 |
| D07 | aggregation | answer | answer | ✓ | ✓ |  | 4.45 |
| D08 | aggregation | answer | answer | ✓ | ✓ |  | 6.67 |
| D09 | aggregation | answer | answer | ✓ | ✓ |  | 5.2 |
| D10 | judgement | answer | answer | ✓ | ✓ |  | 5.04 |
| D11 | judgement | answer | answer | ✓ | ✓ |  | 4.84 |
| D12 | judgement | answer | answer | ✓ | ✓ |  | 4.88 |
| D13 | tracing | answer | answer | ✓ | ✓ |  | 7.48 |
| D14 | tracing | answer | answer | ✓ | ✓ |  | 6.22 |
| D15 | tracing | answer | answer | ✓ | ✓ |  | 6.1 |
| D16 | discovery | answer | answer | ✓ | ✓ |  | 5.61 |
| D17 | discovery | answer | answer | ✓ | ✓ |  | 9.14 |
| D18 | discovery | answer | answer | ✓ | ✓ |  | 5.24 |
| D19 | feasibility | estimate | estimate | ✓ | ✓ |  | 9.34 |
| D20 | feasibility | estimate | estimate | ✓ | ✓ |  | 8.1 |
| D21 | feasibility | estimate | estimate | ✓ | ✓ |  | 9.04 |
| D22 | feasibility | estimate | estimate | ✓ | ✓ |  | 8.16 |
| D23 | feasibility | estimate | estimate | ✓ | ✓ |  | 5.86 |
| D24 | action | propose | propose | ✓ | ✓ |  | 8.04 |
| D25 | action | propose | propose | ✓ | ✓ |  | 4.04 |
| D26 | action | propose | propose | ✓ | ✓ |  | 10.77 |
| D27 | action | reject | reject | ✓ | ✓ |  | 6.81 |
| D28 | action | propose | propose | ✓ | ✓ |  | 13.9 |
| D29 | ambiguous | clarify | clarify | ✓ | ✓ |  | 7.25 |
| D30 | ambiguous | clarify | clarify | ✓ | ✓ |  | 6.39 |
| D31 | ambiguous | clarify | clarify | ✓ | ✓ |  | 5.76 |
| D32 | unanswerable | refuse | refuse | ✓ | ✓ |  | 6.68 |
| D33 | unanswerable | refuse | refuse | ✓ | ✓ |  | 4.25 |
| D34 | unanswerable | refuse | refuse | ✓ | ✓ |  | 7.36 |
| D35 | unanswerable | refuse | refuse | ✓ | ✓ |  | 6.95 |
| D36 | unanswerable | refuse | refuse | ✓ | ✓ |  | 7.31 |
