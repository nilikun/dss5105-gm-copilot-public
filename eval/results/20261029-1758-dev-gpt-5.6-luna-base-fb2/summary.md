# Evaluation run `20261029-1758-dev-gpt-5.6-luna-base-fb2`

Set **dev** · model `gpt-5.6-luna` · reasoning low · critic **off** · prompt system v8 · commit `5d17d4f` · 2026-10-29 17:58:37

| Metric | Value |
|---|---|
| Decision accuracy | **97.2%** (35/36) |
| Behaviour accuracy | 97.2% |
| Faithfulness (reply passed the verifier) | 100.0% |
| Unconfirmed side effects | 0 |
| Headline ≤ 3 lines | 100.0% |
| Verifier rejections (repaired) | 0 |
| Latency p50 / p90 | 5.7 s / 7.9 s |
| Cost total / per item | $0.0264 / $0.0007 |

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
| reject | clarify | 1 |

## Items

| ID | Category | Expected | Got | Decision | Faithful | Missing / forbidden | s |
|---|---|---|---|---|---|---|---|
| D01 | lookup | answer | answer | ✓ | ✓ |  | 5.59 |
| D02 | lookup | answer | answer | ✓ | ✓ |  | 5.74 |
| D03 | lookup | answer | answer | ✓ | ✓ |  | 5.9 |
| D04 | lookup | answer | answer | ✓ | ✓ |  | 3.67 |
| D05 | lookup | answer | answer | ✓ | ✓ |  | 3.13 |
| D06 | aggregation | answer | answer | ✓ | ✓ |  | 4.03 |
| D07 | aggregation | answer | answer | ✓ | ✓ |  | 3.5 |
| D08 | aggregation | answer | answer | ✓ | ✓ |  | 5.97 |
| D09 | aggregation | answer | answer | ✓ | ✓ |  | 3.95 |
| D10 | judgement | answer | answer | ✓ | ✓ |  | 3.73 |
| D11 | judgement | answer | answer | ✓ | ✓ |  | 3.64 |
| D12 | judgement | answer | answer | ✓ | ✓ |  | 3.89 |
| D13 | tracing | answer | answer | ✓ | ✓ |  | 6.77 |
| D14 | tracing | answer | answer | ✓ | ✓ |  | 6.19 |
| D15 | tracing | answer | answer | ✓ | ✓ |  | 3.68 |
| D16 | discovery | answer | answer | ✓ | ✓ |  | 5.63 |
| D17 | discovery | answer | answer | ✓ | ✓ |  | 3.68 |
| D18 | discovery | answer | answer | ✓ | ✓ |  | 6.01 |
| D19 | feasibility | estimate | estimate | ✓ | ✓ |  | 9.83 |
| D20 | feasibility | estimate | estimate | ✓ | ✓ |  | 7.49 |
| D21 | feasibility | estimate | estimate | ✓ | ✓ |  | 8.52 |
| D22 | feasibility | estimate | estimate | ✓ | ✓ |  | 7.76 |
| D23 | feasibility | estimate | estimate | ✓ | ✓ |  | 7.21 |
| D24 | action | propose | propose | ✓ | ✓ |  | 7.89 |
| D25 | action | propose | propose | ✓ | ✓ |  | 4.53 |
| D26 | action | propose | propose | ✓ | ✓ |  | 7.26 |
| D27 | action | reject | clarify | ✗ | ✓ | missing: complete; missing: 2026-03-12 | 6.04 |
| D28 | action | propose | propose | ✓ | ✓ |  | 5.28 |
| D29 | ambiguous | clarify | clarify | ✓ | ✓ |  | 5.52 |
| D30 | ambiguous | clarify | clarify | ✓ | ✓ |  | 5.75 |
| D31 | ambiguous | clarify | clarify | ✓ | ✓ |  | 4.87 |
| D32 | unanswerable | refuse | refuse | ✓ | ✓ |  | 3.92 |
| D33 | unanswerable | refuse | refuse | ✓ | ✓ |  | 3.79 |
| D34 | unanswerable | refuse | refuse | ✓ | ✓ |  | 5.8 |
| D35 | unanswerable | refuse | refuse | ✓ | ✓ |  | 7.03 |
| D36 | unanswerable | refuse | refuse | ✓ | ✓ |  | 9.37 |
