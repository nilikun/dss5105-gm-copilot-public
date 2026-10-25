# Evaluation run `20261015-2222-dev-gpt-5.6-luna-base-v6b`

Set **dev** · model `gpt-5.6-luna` · reasoning low · critic **off** · prompt system v6 · commit `6714fe0` · 2026-10-15 22:22:46

| Metric | Value |
|---|---|
| Decision accuracy | **100.0%** (36/36) |
| Behaviour accuracy | 100.0% |
| Faithfulness (reply passed the verifier) | 100.0% |
| Unconfirmed side effects | 0 |
| Headline ≤ 3 lines | 100.0% |
| Verifier rejections (repaired) | 0 |
| Latency p50 / p90 | 6.7 s / 11.3 s |
| Cost total / per item | $0.0270 / $0.0008 |

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
| D01 | lookup | answer | answer | ✓ | ✓ |  | 6.21 |
| D02 | lookup | answer | answer | ✓ | ✓ |  | 13.33 |
| D03 | lookup | answer | answer | ✓ | ✓ |  | 7.96 |
| D04 | lookup | answer | answer | ✓ | ✓ |  | 4.69 |
| D05 | lookup | answer | answer | ✓ | ✓ |  | 5.13 |
| D06 | aggregation | answer | answer | ✓ | ✓ |  | 5.88 |
| D07 | aggregation | answer | answer | ✓ | ✓ |  | 4.55 |
| D08 | aggregation | answer | answer | ✓ | ✓ |  | 6.88 |
| D09 | aggregation | answer | answer | ✓ | ✓ |  | 5.7 |
| D10 | judgement | answer | answer | ✓ | ✓ |  | 5.86 |
| D11 | judgement | answer | answer | ✓ | ✓ |  | 4.18 |
| D12 | judgement | answer | answer | ✓ | ✓ |  | 5.92 |
| D13 | tracing | answer | answer | ✓ | ✓ |  | 7.33 |
| D14 | tracing | answer | answer | ✓ | ✓ |  | 6.76 |
| D15 | tracing | answer | answer | ✓ | ✓ |  | 5.33 |
| D16 | discovery | answer | answer | ✓ | ✓ |  | 6.2 |
| D17 | discovery | answer | answer | ✓ | ✓ |  | 6.36 |
| D18 | discovery | answer | answer | ✓ | ✓ |  | 7.26 |
| D19 | feasibility | estimate | estimate | ✓ | ✓ |  | 11.35 |
| D20 | feasibility | estimate | estimate | ✓ | ✓ |  | 9.69 |
| D21 | feasibility | estimate | estimate | ✓ | ✓ |  | 9.08 |
| D22 | feasibility | estimate | estimate | ✓ | ✓ |  | 10.43 |
| D23 | feasibility | estimate | estimate | ✓ | ✓ |  | 6.92 |
| D24 | action | propose | propose | ✓ | ✓ |  | 10.1 |
| D25 | action | propose | propose | ✓ | ✓ |  | 4.5 |
| D26 | action | propose | propose | ✓ | ✓ |  | 19.14 |
| D27 | action | reject | reject | ✓ | ✓ |  | 14.87 |
| D28 | action | propose | propose | ✓ | ✓ |  | 6.12 |
| D29 | ambiguous | clarify | clarify | ✓ | ✓ |  | 6.37 |
| D30 | ambiguous | clarify | clarify | ✓ | ✓ |  | 6.84 |
| D31 | ambiguous | clarify | clarify | ✓ | ✓ |  | 6.31 |
| D32 | unanswerable | refuse | refuse | ✓ | ✓ |  | 5.36 |
| D33 | unanswerable | refuse | refuse | ✓ | ✓ |  | 6.6 |
| D34 | unanswerable | refuse | refuse | ✓ | ✓ |  | 7.76 |
| D35 | unanswerable | refuse | refuse | ✓ | ✓ |  | 8.04 |
| D36 | unanswerable | refuse | refuse | ✓ | ✓ |  | 7.64 |
