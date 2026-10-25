"""Optional LLM critic (decision D16). Runs only after the deterministic verifier has passed a reply; it checks
what code cannot (answers the question? asked when ambiguous? honest refusal? misleading?). Its revisions go back
through the verifier, so it can never introduce an unsupported number. On by setting, measured by ablation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from app.agent import prompts
from app.agent.respond import RespondArgs
from app.llm.base import LLMClient, LLMResponse

SCHEMA = {"name": "critique", "schema": {
    "type": "object", "additionalProperties": False, "required": ["verdict", "issues"],
    "properties": {"verdict": {"type": "string", "enum": ["pass", "revise"]},
                   "issues": {"type": "array", "items": {"type": "string"}, "maxItems": 3}}}}


@dataclass
class Critique:
    verdict: str
    issues: list[str] = field(default_factory=list)
    response: LLMResponse | None = None


def abridge(outputs: list[Any], per_item: int = 1500, total: int = 7000) -> str:
    parts, used = [], 0
    for o in outputs:
        s = json.dumps(o, ensure_ascii=False, default=str)[:per_item]
        if used + len(s) > total:
            parts.append("…")
            break
        parts.append(s)
        used += len(s)
    return "\n".join(parts) or "(no tool results)"


def review(llm: LLMClient, question: str, draft: RespondArgs, tool_outputs: list[Any]) -> Critique:
    p = prompts.load("critic")
    text = p.render(question=question, tool_results=abridge(tool_outputs),
                    draft=draft.model_dump_json(exclude_none=True, indent=1))
    resp = llm.create(instructions=None, input=[{"role": "user", "content": text}], tools=None, json_schema=SCHEMA)
    try:
        data = json.loads(resp.text)
        return Critique(verdict=data.get("verdict", "pass"), issues=data.get("issues", [])[:3], response=resp)
    except (json.JSONDecodeError, AttributeError):
        return Critique(verdict="pass", issues=["critic output unreadable; ignored"], response=resp)
