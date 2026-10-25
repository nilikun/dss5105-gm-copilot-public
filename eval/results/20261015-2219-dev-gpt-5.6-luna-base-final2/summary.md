# Evaluation run `20261015-2219-dev-gpt-5.6-luna-base-final2`

Set **dev** · model `gpt-5.6-luna` · reasoning low · critic **off** · prompt system v6 · commit `861f2d0` · 2026-10-15 22:19:46 · re-scored 2026-10-15 22:24:36 with the current scorer

| Metric | Value |
|---|---|
| Decision accuracy | **100.0%** (36/36) |
| Behaviour accuracy | 100.0% |
| Faithfulness (reply passed the verifier) | 100.0% |
| Unconfirmed side effects | 0 |
| Headline ≤ 3 lines | 100.0% |
| Verifier rejections (repaired) | 1 |
| Latency p50 / p90 | 7.3 s / 11.2 s |
| Cost total / per item | $0.0271 / $0.0008 |

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
| D01 | lookup | answer | answer | ✓ | ✓ |  | 6.59 |
| D02 | lookup | answer | answer | ✓ | ✓ |  | 13.55 |
| D03 | lookup | answer | answer | ✓ | ✓ |  | 8.12 |
| D04 | lookup | answer | answer | ✓ | ✓ |  | 4.93 |
| D05 | lookup | answer | answer | ✓ | ✓ |  | 6.26 |
| D06 | aggregation | answer | answer | ✓ | ✓ |  | 5.65 |
| D07 | aggregation | answer | answer | ✓ | ✓ |  | 6.08 |
| D08 | aggregation | answer | answer | ✓ | ✓ |  | 14.44 |
| D09 | aggregation | answer | answer | ✓ | ✓ |  | 5.43 |
| D10 | judgement | answer | answer | ✓ | ✓ |  | 4.91 |
| D11 | judgement | answer | answer | ✓ | ✓ |  | 5.52 |
| D12 | judgement | answer | answer | ✓ | ✓ |  | 5.56 |
| D13 | tracing | answer | answer | ✓ | ✓ |  | 7.58 |
| D14 | tracing | answer | answer | ✓ | ✓ |  | 8.08 |
| D15 | tracing | answer | answer | ✓ | ✓ |  | 5.74 |
| D16 | discovery | answer | answer | ✓ | ✓ |  | 7.0 |
| D17 | discovery | answer | answer | ✓ | ✓ |  | 10.7 |
| D18 | discovery | answer | answer | ✓ | ✓ |  | 6.31 |
| D19 | feasibility | estimate | estimate | ✓ | ✓ |  | 11.22 |
| D20 | feasibility | estimate | estimate | ✓ | ✓ |  | 9.81 |
| D21 | feasibility | estimate | estimate | ✓ | ✓ |  | 11.08 |
| D22 | feasibility | estimate | estimate | ✓ | ✓ |  | 9.2 |
| D23 | feasibility | estimate | estimate | ✓ | ✓ |  | 6.79 |
| D24 | action | propose | propose | ✓ | ✓ |  | 9.06 |
| D25 | action | propose | propose | ✓ | ✓ |  | 5.74 |
| D26 | action | propose | propose | ✓ | ✓ |  | 11.64 |
| D27 | action | reject | reject | ✓ | ✓ |  | 8.16 |
| D28 | action | propose | propose | ✓ | ✓ |  | 6.54 |
| D29 | ambiguous | clarify | clarify | ✓ | ✓ |  | 6.66 |
| D30 | ambiguous | clarify | clarify | ✓ | ✓ |  | 7.83 |
| D31 | ambiguous | clarify | clarify | ✓ | ✓ |  | 6.79 |
| D32 | unanswerable | refuse | refuse | ✓ | ✓ |  | 4.66 |
| D33 | unanswerable | refuse | refuse | ✓ | ✓ |  | 9.46 |
| D34 | unanswerable | refuse | refuse | ✓ | ✓ |  | 10.55 |
| D35 | unanswerable | refuse | refuse | ✓ | ✓ |  | 7.61 |
| D36 | unanswerable | refuse | refuse | ✓ | ✓ |  | 11.2 |
