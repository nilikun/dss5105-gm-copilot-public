# Evaluation run `20261015-2222-dev-gpt-5.6-luna-base-v6a`

Set **dev** · model `gpt-5.6-luna` · reasoning low · critic **off** · prompt system v6 · commit `6714fe0` · 2026-10-15 22:22:46

| Metric | Value |
|---|---|
| Decision accuracy | **97.2%** (35/36) |
| Behaviour accuracy | 100.0% |
| Faithfulness (reply passed the verifier) | 100.0% |
| Unconfirmed side effects | 0 |
| Headline ≤ 3 lines | 100.0% |
| Verifier rejections (repaired) | 1 |
| Latency p50 / p90 | 6.7 s / 11.1 s |
| Cost total / per item | $0.0272 / $0.0008 |

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
| D01 | lookup | answer | answer | ✓ | ✓ |  | 5.55 |
| D02 | lookup | answer | answer | ✓ | ✓ |  | 10.65 |
| D03 | lookup | answer | answer | ✓ | ✓ |  | 7.46 |
| D04 | lookup | answer | answer | ✓ | ✓ |  | 5.24 |
| D05 | lookup | answer | answer | ✓ | ✓ |  | 4.84 |
| D06 | aggregation | answer | answer | ✓ | ✓ |  | 4.97 |
| D07 | aggregation | answer | answer | ✓ | ✓ |  | 4.43 |
| D08 | aggregation | answer | answer | ✓ | ✓ |  | 6.44 |
| D09 | aggregation | answer | answer | ✓ | ✓ |  | 4.97 |
| D10 | judgement | answer | answer | ✓ | ✓ |  | 4.66 |
| D11 | judgement | answer | answer | ✓ | ✓ |  | 4.9 |
| D12 | judgement | answer | answer | ✓ | ✓ |  | 5.82 |
| D13 | tracing | answer | answer | ✓ | ✓ |  | 9.38 |
| D14 | tracing | answer | answer | ✓ | ✓ |  | 10.03 |
| D15 | tracing | answer | answer | ✓ | ✓ |  | 6.06 |
| D16 | discovery | answer | answer | ✓ | ✓ |  | 7.75 |
| D17 | discovery | answer | answer | ✓ | ✓ |  | 6.15 |
| D18 | discovery | answer | answer | ✓ | ✓ |  | 5.82 |
| D19 | feasibility | estimate | estimate | ✓ | ✓ |  | 10.24 |
| D20 | feasibility | estimate | estimate | ✓ | ✓ |  | 10.3 |
| D21 | feasibility | estimate | estimate | ✓ | ✓ |  | 9.63 |
| D22 | feasibility | estimate | estimate | ✓ | ✓ |  | 11.28 |
| D23 | feasibility | estimate | estimate | ✓ | ✓ |  | 9.45 |
| D24 | action | propose | propose | ✓ | ✓ |  | 9.46 |
| D25 | action | propose | propose | ✓ | ✓ |  | 5.57 |
| D26 | action | propose | propose | ✓ | ✓ |  | 11.24 |
| D27 | action | reject | reject | ✓ | ✓ |  | 11.42 |
| D28 | action | propose | propose | ✓ | ✓ |  | 6.34 |
| D29 | ambiguous | clarify | clarify | ✓ | ✓ |  | 6.18 |
| D30 | ambiguous | clarify | clarify | ✓ | ✓ |  | 8.04 |
| D31 | ambiguous | clarify | clarify | ✓ | ✓ |  | 6.15 |
| D32 | unanswerable | refuse | refuse | ✓ | ✓ |  | 5.95 |
| D33 | unanswerable | refuse | refuse | ✓ | ✓ |  | 9.19 |
| D34 | unanswerable | refuse | refuse | ✓ | ✓ |  | 10.66 |
| D35 | unanswerable | refuse | refuse | ✗ | ✓ | missing: -44% | -48.6% | 11.1 |
| D36 | unanswerable | refuse | refuse | ✓ | ✓ |  | 6.88 |
