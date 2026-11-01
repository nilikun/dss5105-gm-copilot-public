"""Independent Responses-API judge. No agent imports, tool outputs or self-grounding flags."""

from __future__ import annotations

import json
import time
from pathlib import Path

from independent_scoring import SEMANTIC, answer_text

PROMPT = Path(__file__).parent / "protocol/judge_prompt.md"
SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["decisions"],
    "properties": {
        "decisions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["criterion_id", "pass", "excerpt", "reason"],
                "properties": {
                    "criterion_id": {"type": "string"},
                    "pass": {"type": "boolean"},
                    "excerpt": {"type": "string"},
                    "reason": {"type": "string"},
                },
            },
        }
    },
}


def validate_decisions(result, item, candidate):
    expected = [f["criterion_id"] for f in item["required_facts"]] + list(SEMANTIC)
    decisions = result.get("decisions", [])
    if sorted(c.get("criterion_id", "") for c in decisions) != sorted(expected):
        raise ValueError("Missing, duplicated or unknown judge criteria")
    for c in decisions:
        if type(c.get("pass")) is not bool or not c.get("reason") or not isinstance(c.get("excerpt"), str):
            raise ValueError("Malformed criterion")
        excerpt = c["excerpt"]
        if len(excerpt) > 240 or (excerpt and excerpt not in candidate):
            raise ValueError("Judge excerpt is not a short literal candidate substring")
        if c["pass"] and not excerpt:
            raise ValueError("A passing criterion requires supporting text")
    return {"valid": True, "decisions": decisions}


def evaluate(item, reply, *, api_key, model="gpt-6-astra", effort="low", max_output_tokens=4000, timeout=60):
    from openai import OpenAI

    candidate = answer_text(reply)
    payload = {
        "question": item["question"],
        "reference_answer": item["reference_answer"],
        "reference_evidence": item["reference_evidence"],
        "required_facts": item["required_facts"],
        "expected_behavior": item["expected_behavior"],
        "prohibited_claims": item.get("prohibited_claims", []),
        "criteria": [f["criterion_id"] for f in item["required_facts"]] + list(SEMANTIC),
        "candidate_answer": candidate,
        "candidate_behavior": reply.get("kind"),
    }
    started = time.perf_counter()
    result = {"valid": False, "decisions": [], "usage": None, "error": None, "raw": None}
    try:
        client = OpenAI(api_key=api_key, timeout=timeout, max_retries=0)
        response = client.responses.create(
            model=model,
            reasoning={"effort": effort},
            instructions=PROMPT.read_text(encoding="utf-8"),
            input=[{"role": "user", "content": json.dumps(payload)}],
            text={"format": {"type": "json_schema", "name": "independent_judge", "schema": SCHEMA, "strict": True}},
            max_output_tokens=max_output_tokens,
        )
        result["model"] = response.model
        result["raw"] = response.output_text
        if response.usage:
            u = response.usage
            result["usage"] = {
                "input_tokens": u.input_tokens,
                "cached_input_tokens": u.input_tokens_details.cached_tokens,
                "output_tokens": u.output_tokens,
                "reasoning_tokens": u.output_tokens_details.reasoning_tokens,
            }
        result.update(validate_decisions(json.loads(response.output_text), item, candidate))
    except Exception as exc:
        result["error"] = {"type": type(exc).__name__, "message": str(exc).replace(api_key, "[redacted]")[:1000]}
    result["latency_seconds"] = time.perf_counter() - started
    result["settings"] = {
        "model": model,
        "reasoning_effort": effort,
        "max_output_tokens": max_output_tokens,
        "timeout_seconds": timeout,
        "max_retries": 0,
    }
    return result
