"""Check PUBLIC scaffolding only. Never discover or open a real held-out file."""

import json
import subprocess
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
COVERAGE = {"lookup": 3, "aggregation": 2, "judgement": 2, "tracing": 2, "discovery": 1,
            "feasibility": 3, "action": 3, "ambiguous": 2, "unanswerable": 2}


def test_template_is_blank_and_preserves_twenty_question_coverage():
    template = yaml.safe_load((ROOT / "eval/questions_heldout.template.yaml").read_text(encoding="utf-8"))
    assert template["status"] == "authoring_template_not_runnable"
    assert template["version"] == 2
    assert template["author"] == "" and template["exposure_declaration"] == ""
    assert [item["id"] for item in template["items"]] == [f"H{i:02d}" for i in range(1, 21)]
    assert Counter(item["category"] for item in template["items"]) == COVERAGE
    for item in template["items"]:
        for field in ("question", "expected_behavior", "reference_answer", "verification"):
            assert item[field] == ""
        for field in ("context_turns", "required_facts", "reference_evidence", "prohibited_claims"):
            assert item[field] == []


def test_freeze_template_does_not_pretend_unset_values_are_frozen():
    template = json.loads((ROOT / "eval/heldout_freeze.template.json").read_text(encoding="utf-8"))
    assert template["status"] == "blank_template_not_frozen"
    assert template["questions_and_references"]["sha256"] is None
    assert template["questions_and_references"]["category_counts"] == COVERAGE
    assert template["versions"]["baseline_commit"] is None
    assert template["agent_settings"]["model"] is None
    assert template["execution"]["repetitions_per_item_per_version"] is None
    assert template["reporting"]["all_attempts_preserved"] is True


def test_ignore_guards_hidden_names_but_not_public_templates():
    hidden = ["eval/questions_heldout.yaml", "eval/heldout_freeze.json", "eval/private/references.yaml"]
    public = ["eval/questions_heldout.template.yaml", "eval/heldout_freeze.template.json"]
    result = subprocess.run(["git", "check-ignore", "--no-index", *hidden, *public],
                            cwd=ROOT, capture_output=True, text=True, check=False)
    assert set(result.stdout.splitlines()) == set(hidden)


def test_new_public_code_does_not_import_agent_truth_or_use_network_clients():
    # Dependency boundary: the reference calculator and contract checker are
    # standalone. This guards their independence from production tools.
    import ast
    for name in ("contract_reference.py", "answer_contracts.py"):
        tree = ast.parse((ROOT / "eval" / name).read_text(encoding="utf-8"))
        imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        imports += [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names]
        assert all(name and name.split(".")[0] not in {"app", "scoring", "openai", "requests", "httpx"}
                   for name in imports)
