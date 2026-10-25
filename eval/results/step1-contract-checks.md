# Step 1 offline validation — 20 October 2026

This is a development-contract check, not a live agent benchmark or held-out score.

| Check | Result |
|---|---|
| New contract/reference/template tests (`python -m pytest eval/tests -q`) | 278 passed |
| Existing scorer tests (`PYTHON_DOTENV_DISABLED=1 python -m pytest tests/test_eval_scoring.py -q`, from backend/) | 6 passed |
| Ruff over new Python code, using backend/pyproject.toml | Passed |
| Baseline source and current data hash verification | Passed |
| Git diff whitespace check | Passed |
| Public cases / equivalent accepted answers / deliberately rejected answers | 26 / 53 / 196 |
| Agent / judge API calls | 0 / 0 |

Test environment: Python 3.13.9, pytest 8.4.2, PyYAML 6.0.3.
The complete backend suite was not run: this installed environment lacks FastAPI and the pinned packages were unavailable to offline `uv sync`. The relevant existing scorer tests ran successfully.

## Representative observed checks

| Example | Result |
|---|---|
| D02: complete correct answer | Accepted |
| D02: missing deadline | Rejected: `deadline` |
| D02: wrong deadline | Rejected: `deadline`, `unexpected_date` |
| D35: complete correct answer | Accepted |
| D35: missing percentage | Rejected: `percentage`, `percentage_scope` |
| D35: reversed direction | Rejected: `percentage` |
| D35: day and period percentage swapped | Rejected: `percentage` |
| D35: cause invented | Rejected: `unreviewed_claim`, `unsupported_cause` |
| P01: complete correct answer | Accepted |
| P01: day and period percentage swapped | Rejected: `percentage` |
| P01: wrong averaging denominator | Rejected: `units` |

## Limits and next steps

Checks recognize a bounded set of short English fact sentences. They accept equivalent date formats and wording, preserve percentage sign/window, and flag unrecognized extra production sentences for review. They do not replace full independent claim scoring or a calibrated judge.

The runtime, prompts, old scorer, source CSVs and historical results remain unchanged. This step does not claim D02/D35 are fixed. Step 2 implements the order-answer fix; Step 3 implements production comparisons. Step 4 must integrate external held-out input, full fact scoring, calibration and actual usage capture. The blank held-out template is not runnable by the current evaluation runner.

Baseline commit: `36a44c7e4965154f78853526333b8219c54ad1ad`. Snapshot details: `eval/baselines/step1.json`. No hidden questions or answers were authored or read.
