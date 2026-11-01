# Independent author handoff — no development answers included

Read `docs/HELDOUT_GUIDE.md` before writing. You should not be tuning the agent or viewing development
questions/answers. Work outside the development checkout. Use the source CSVs and data dictionary to
write exactly 20 realistic GM questions with the category coverage in the blank YAML template. Compute
references in your own Excel workbook or script; retain formulas/row filters and obtain a second check
where possible. Do not call the agent or its tools to obtain reference answers.

The simulated timestamp is 2026-04-01 at 07:00. Factory working days are Monday–Saturday. Record
inclusive windows, actual/baseline definitions, units, signed changes, missing fields and expected
clarification/refusal/action behavior. Do not replace missing rows with zero or invent causes.

For each required fact add:

- `criterion_id`, `subject`, `field`, `expected_value`, `unit`, `calculation` and `tolerance`.
- `value_type`: text, date, number or percentage.
- `pattern`: a contextual Python regex containing `(?P<value>...)`, extracting the fact's asserted value.
- Optional `aliases` for equivalent text; `scope_subject` and `scope_dates` to bind a value to its entity
  and exact date/window in the same sentence. Percentage tolerance is in percentage points.

Patterns are evaluated after date/Markdown normalization. A fictitious format example,
`deadline\s*:\s*(?P<value>\d{4}-\d{2}-\d{2})`, checks a deadline-labelled date rather than any date
in the answer. Include equivalent valid wording; test patterns against deliberately wrong values,
subjects and windows before freezing. Obtain help from an independent reviewer if necessary, without
exposing hidden questions to the tuning developer. The semantic judge is an additional check and
cannot rescue failed hard criteria. Keep required facts complete even when a question is difficult.

The judge fails any claim your evidence does not cover, even a true one. So list in `reference_evidence` the
directly relevant facts a good answer may add, not only the required ones. For a question about whether output is
normal, compute the published rule yourself (`docs/TOOL_SPEC.md`, tool 9): baseline median, robust sigma, z and tier.

Evidence entries require source_file, row_filter, calculation, result, workbook_cells_or_script, and
checker/provenance. Prohibited claims are contextual regex patterns, not words that also appear in an
honest refusal. Every item also needs a reference answer, expected behavior and verification notes.

Return to the custodian, privately: completed questions/references YAML, independent calculations,
checker and author names, authoring date, exposure declaration and file hashes. Do not share the actual
questions with the development chat. The custodian holds them until human calibration and code/settings
freeze are complete. Keep the blank freeze template for coordination with the operator; do not label
it frozen while any requirement is missing. Once hidden failures inform fixes, those questions are
regressions and fresh independent questions are needed for another unseen-performance claim.
