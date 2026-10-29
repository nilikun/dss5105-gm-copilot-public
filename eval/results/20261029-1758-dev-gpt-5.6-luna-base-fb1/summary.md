# Evaluation run `20261029-1758-dev-gpt-5.6-luna-base-fb1`

Set **dev** · model `gpt-5.6-luna` · reasoning low · critic **off** · prompt system v8 · commit `5d17d4f` · 2026-10-29 17:58:37

| Metric | Value |
|---|---|
| Decision accuracy | **94.4%** (34/36) |
| Behaviour accuracy | 97.2% |
| Faithfulness (reply passed the verifier) | 100.0% |
| Unconfirmed side effects | 0 |
| Headline ≤ 3 lines | 100.0% |
| Verifier rejections (repaired) | 0 |
| Latency p50 / p90 | 5.3 s / 7.7 s |
| Cost total / per item | $0.0261 / $0.0007 |

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
| D01 | lookup | answer | answer | ✓ | ✓ |  | 4.16 |
| D02 | lookup | answer | answer | ✓ | ✓ |  | 4.76 |
| D03 | lookup | answer | answer | ✓ | ✓ |  | 5.52 |
| D04 | lookup | answer | answer | ✓ | ✓ |  | 4.15 |
| D05 | lookup | answer | answer | ✓ | ✓ |  | 4.07 |
| D06 | aggregation | answer | answer | ✓ | ✓ |  | 4.15 |
| D07 | aggregation | answer | answer | ✓ | ✓ |  | 3.96 |
| D08 | aggregation | answer | answer | ✓ | ✓ |  | 7.68 |
| D09 | aggregation | answer | answer | ✓ | ✓ |  | 4.0 |
| D10 | judgement | answer | answer | ✓ | ✓ |  | 3.71 |
| D11 | judgement | answer | answer | ✓ | ✓ |  | 4.61 |
| D12 | judgement | answer | answer | ✓ | ✓ |  | 4.38 |
| D13 | tracing | answer | answer | ✓ | ✓ |  | 6.04 |
| D14 | tracing | answer | answer | ✓ | ✓ |  | 5.49 |
| D15 | tracing | answer | answer | ✓ | ✓ |  | 5.43 |
| D16 | discovery | answer | answer | ✓ | ✓ |  | 5.24 |
| D17 | discovery | answer | answer | ✓ | ✓ |  | 6.63 |
| D18 | discovery | answer | answer | ✓ | ✓ |  | 6.21 |
| D19 | feasibility | estimate | estimate | ✓ | ✓ |  | 7.7 |
| D20 | feasibility | estimate | estimate | ✓ | ✓ |  | 8.88 |
| D21 | feasibility | estimate | estimate | ✓ | ✓ |  | 4.26 |
| D22 | feasibility | estimate | estimate | ✓ | ✓ |  | 8.31 |
| D23 | feasibility | estimate | estimate | ✓ | ✓ |  | 6.55 |
| D24 | action | propose | propose | ✓ | ✓ |  | 7.07 |
| D25 | action | propose | propose | ✓ | ✓ |  | 4.5 |
| D26 | action | propose | propose | ✓ | ✓ |  | 6.78 |
| D27 | action | reject | clarify | ✗ | ✓ | missing: complete; missing: 2026-03-12 | 5.7 |
| D28 | action | propose | propose | ✓ | ✓ |  | 5.35 |
| D29 | ambiguous | clarify | clarify | ✓ | ✓ |  | 5.15 |
| D30 | ambiguous | clarify | clarify | ✓ | ✓ |  | 4.83 |
| D31 | ambiguous | clarify | clarify | ✓ | ✓ |  | 5.03 |
| D32 | unanswerable | refuse | refuse | ✓ | ✓ |  | 4.12 |
| D33 | unanswerable | refuse | refuse | ✓ | ✓ |  | 4.09 |
| D34 | unanswerable | refuse | refuse | ✓ | ✓ |  | 6.22 |
| D35 | unanswerable | refuse | refuse | ✗ | ✓ | missing: -44% | -48.6% | 5.63 |
| D36 | unanswerable | refuse | refuse | ✓ | ✓ |  | 5.77 |
