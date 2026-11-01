# Evaluation run `20261101-2312-dev-gpt-5.6-luna-base-s3a`

Set **dev** · model `gpt-5.6-luna` · reasoning low · critic **off** · prompt system v10 · commit `5f5b43e` · 2026-11-01 23:12:06

| Metric | Value |
|---|---|
| Decision accuracy | **100.0%** (36/36) |
| Behaviour accuracy | 100.0% |
| Faithfulness (reply passed the verifier) | 100.0% |
| Unconfirmed side effects | 0 |
| Headline ≤ 3 lines | 100.0% |
| Verifier rejections (repaired) | 0 |
| Latency p50 / p90 | 5.6 s / 9.4 s |
| Cost total / per item | $0.0274 / $0.0008 |

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
| D01 | lookup | answer | answer | ✓ | ✓ |  | 4.98 |
| D02 | lookup | answer | answer | ✓ | ✓ |  | 6.04 |
| D03 | lookup | answer | answer | ✓ | ✓ |  | 5.72 |
| D04 | lookup | answer | answer | ✓ | ✓ |  | 4.13 |
| D05 | lookup | answer | answer | ✓ | ✓ |  | 4.11 |
| D06 | aggregation | answer | answer | ✓ | ✓ |  | 4.02 |
| D07 | aggregation | answer | answer | ✓ | ✓ |  | 4.49 |
| D08 | aggregation | answer | answer | ✓ | ✓ |  | 5.71 |
| D09 | aggregation | answer | answer | ✓ | ✓ |  | 4.11 |
| D10 | judgement | answer | answer | ✓ | ✓ |  | 4.14 |
| D11 | judgement | answer | answer | ✓ | ✓ |  | 3.95 |
| D12 | judgement | answer | answer | ✓ | ✓ |  | 4.6 |
| D13 | tracing | answer | answer | ✓ | ✓ |  | 7.15 |
| D14 | tracing | answer | answer | ✓ | ✓ |  | 6.34 |
| D15 | tracing | answer | answer | ✓ | ✓ |  | 4.98 |
| D16 | discovery | answer | answer | ✓ | ✓ |  | 6.06 |
| D17 | discovery | answer | answer | ✓ | ✓ |  | 6.88 |
| D18 | discovery | answer | answer | ✓ | ✓ |  | 5.48 |
| D19 | feasibility | estimate | estimate | ✓ | ✓ |  | 10.38 |
| D20 | feasibility | estimate | estimate | ✓ | ✓ |  | 9.46 |
| D21 | feasibility | estimate | estimate | ✓ | ✓ |  | 9.4 |
| D22 | feasibility | estimate | estimate | ✓ | ✓ |  | 8.47 |
| D23 | feasibility | estimate | estimate | ✓ | ✓ |  | 5.78 |
| D24 | action | propose | propose | ✓ | ✓ |  | 5.4 |
| D25 | action | propose | propose | ✓ | ✓ |  | 5.57 |
| D26 | action | propose | propose | ✓ | ✓ |  | 7.64 |
| D27 | action | reject | reject | ✓ | ✓ |  | 8.12 |
| D28 | action | propose | propose | ✓ | ✓ |  | 5.31 |
| D29 | ambiguous | clarify | clarify | ✓ | ✓ |  | 4.71 |
| D30 | ambiguous | clarify | clarify | ✓ | ✓ |  | 7.35 |
| D31 | ambiguous | clarify | clarify | ✓ | ✓ |  | 5.58 |
| D32 | unanswerable | refuse | refuse | ✓ | ✓ |  | 3.96 |
| D33 | unanswerable | refuse | refuse | ✓ | ✓ |  | 4.91 |
| D34 | unanswerable | refuse | refuse | ✓ | ✓ |  | 10.83 |
| D35 | unanswerable | refuse | refuse | ✓ | ✓ |  | 8.23 |
| D36 | unanswerable | refuse | refuse | ✓ | ✓ |  | 6.85 |
