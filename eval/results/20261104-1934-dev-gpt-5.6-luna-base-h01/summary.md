# Evaluation run `20261104-1934-dev-gpt-5.6-luna-base-h01`

Set **dev** · model `gpt-5.6-luna` · reasoning low · critic **off** · prompt system v10 · commit `6e28021` · 2026-11-04 19:34:44

| Metric | Value |
|---|---|
| Decision accuracy | **97.2%** (35/36) |
| Behaviour accuracy | 100.0% |
| Faithfulness (reply passed the verifier) | 100.0% |
| Unconfirmed side effects | 0 |
| Headline ≤ 3 lines | 100.0% |
| Verifier rejections (repaired) | 0 |
| Latency p50 / p90 | 6.0 s / 9.4 s |
| Cost total / per item | $0.0298 / $0.0008 |

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
| D01 | lookup | answer | answer | ✓ | ✓ |  | 9.36 |
| D02 | lookup | answer | answer | ✓ | ✓ |  | 12.56 |
| D03 | lookup | answer | answer | ✓ | ✓ |  | 8.43 |
| D04 | lookup | answer | answer | ✓ | ✓ |  | 4.52 |
| D05 | lookup | answer | answer | ✓ | ✓ |  | 3.93 |
| D06 | aggregation | answer | answer | ✓ | ✓ |  | 4.46 |
| D07 | aggregation | answer | answer | ✓ | ✓ |  | 4.98 |
| D08 | aggregation | answer | answer | ✓ | ✓ |  | 6.71 |
| D09 | aggregation | answer | answer | ✓ | ✓ |  | 4.46 |
| D10 | judgement | answer | answer | ✓ | ✓ |  | 5.3 |
| D11 | judgement | answer | answer | ✓ | ✓ |  | 6.03 |
| D12 | judgement | answer | answer | ✓ | ✓ |  | 5.07 |
| D13 | tracing | answer | answer | ✓ | ✓ |  | 5.92 |
| D14 | tracing | answer | answer | ✓ | ✓ |  | 6.81 |
| D15 | tracing | answer | answer | ✓ | ✓ |  | 5.58 |
| D16 | discovery | answer | answer | ✓ | ✓ |  | 5.54 |
| D17 | discovery | answer | answer | ✓ | ✓ |  | 7.74 |
| D18 | discovery | answer | answer | ✓ | ✓ |  | 5.15 |
| D19 | feasibility | estimate | estimate | ✓ | ✓ |  | 9.85 |
| D20 | feasibility | estimate | estimate | ✓ | ✓ |  | 9.44 |
| D21 | feasibility | estimate | estimate | ✓ | ✓ |  | 9.06 |
| D22 | feasibility | estimate | estimate | ✓ | ✓ |  | 8.54 |
| D23 | feasibility | estimate | estimate | ✓ | ✓ |  | 5.5 |
| D24 | action | propose | propose | ✓ | ✓ |  | 6.69 |
| D25 | action | propose | propose | ✓ | ✓ |  | 4.44 |
| D26 | action | propose | propose | ✓ | ✓ |  | 8.14 |
| D27 | action | reject | reject | ✓ | ✓ |  | 9.17 |
| D28 | action | propose | propose | ✓ | ✓ |  | 5.05 |
| D29 | ambiguous | clarify | clarify | ✓ | ✓ |  | 6.13 |
| D30 | ambiguous | clarify | clarify | ✓ | ✓ |  | 5.59 |
| D31 | ambiguous | clarify | clarify | ✓ | ✓ |  | 4.79 |
| D32 | unanswerable | refuse | refuse | ✓ | ✓ |  | 4.84 |
| D33 | unanswerable | refuse | refuse | ✓ | ✓ |  | 5.1 |
| D34 | unanswerable | refuse | refuse | ✓ | ✓ |  | 10.38 |
| D35 | unanswerable | refuse | refuse | ✓ | ✓ |  | 6.22 |
| D36 | unanswerable | refuse | refuse | ✗ | ✓ | missing: 640 | 6.35 |
