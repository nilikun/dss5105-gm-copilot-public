# Step 1 reproducibility record

The baseline is local `main` at **36a44c7e4965154f78853526333b8219c54ad1ad**, the clean source
checkout observed on 20 October 2026. Historical final-run results were associated with `6714fe0`
and other earlier commits; those scores are not relabelled as measurements of this baseline.

`eval/baselines/step1.json` records SHA-256 hashes and byte sizes of 86 source/data files from the
baseline commit, CSV row counts, the production date range, and a combined data snapshot digest.
The combined digest is SHA-256 over the UTF-8 bytes of Python `json.dumps(mapping, sort_keys=True)`,
where mapping contains every recorded `data/` relative path and its SHA-256. Individual file hashes
are also available to authors using other tools.

`python eval/record_step1_baseline.py --check` verifies the recorded Git objects and that current
data still matches. Later runtime changes are expected; the baseline source remains retrievable by
commit. The recorder refuses to overwrite an existing baseline and checks source/data against HEAD
when initially recording it. New Step 1 tests/docs are intentionally outside the historical baseline.
The manifest contains no credentials, `.env` values or private held-out questions.

| Setting | Step 1 state |
|---|---|
| Dataset time | 2026-04-01T07:00:00, timezone-naive factory simulation |
| Production observations | 2026-01-01–2026-03-31; 360 stage/day rows |
| Orders / workshops | 120 / 8 rows |
| Baseline evaluation | Not run in Step 1 |
| Model settings | Source defaults recorded for context only; actual execution settings remain to be frozen |
| Engineering model budget | Planning estimate only; not an evaluation configuration or measured usage |
| Agent/judge calls for Step 1 checks | Zero; checks use local Python and source CSVs |
| Held-out questions / hash | Awaiting independent author; null is not a frozen hash |
| Runtime fixes | Steps 2–3 |
| Full scorer/judge integration | Step 4 |
| Paired held-out comparison | Step 5 |

Before the formal run, complete the private freeze manifest and require all required values to be
filled and verified. Freeze actual models/settings, code/prompt/rubric hashes, question/data hashes,
planned repetitions, concurrency, retries, timeouts and usage accounting. This is a checklist, not
an assertion that the current evaluation runner already captures all these fields.

Run the Step 1 checks from the repository root with Python 3.11+ and pytest:

```sh
python -m pytest eval/tests -q
python eval/record_step1_baseline.py --check
```

Existing backend tests continue to run with the project's normal environment:

```sh
uv run --project backend pytest backend/tests
```

For the independent author, supply only `docs/HELDOUT_GUIDE.md`, the two empty templates,
`data/data_dictionary.md`, the frozen source CSVs, and the data hash portion of the baseline manifest.
Development fixtures and output logs are not required to prepare hidden questions.
