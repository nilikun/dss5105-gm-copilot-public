"""A scripted LLM for tests: deterministic, free, and able to misbehave on purpose (e.g. state an unsupported
number) so the verifier and repair paths can be tested without an API."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from app.llm.base import FunctionCall, LLMResponse, Usage

Step = list[tuple[str, dict[str, Any]]] | str | dict[str, Any]


class ScriptedLLM:
    """Each step is either a list of (tool name, arguments) calls, or a callable that receives the input of the
    request and returns such a list (to react to tool outputs), or a dict for a json_schema answer."""

    model = "scripted"

    def __init__(self, steps: list[Step | Callable[[list[dict[str, Any]]], Step]]):
        self.steps = list(steps)
        self.requests: list[dict[str, Any]] = []

    def create(self, *, instructions, input, tools, tool_choice="auto", previous_response_id=None, json_schema=None):
        self.requests.append({"instructions": instructions, "input": input, "tools": tools,
                              "previous_response_id": previous_response_id, "json_schema": json_schema})
        if not self.steps:
            raise AssertionError("ScriptedLLM ran out of steps")
        step = self.steps.pop(0)
        if callable(step):
            step = step(input)
        n = len(self.requests)
        if isinstance(step, dict):
            return LLMResponse(id=f"resp_{n}", model=self.model, text=json.dumps(step), usage=Usage(100, 0, 20))
        if isinstance(step, str):
            return LLMResponse(id=f"resp_{n}", model=self.model, text=step, usage=Usage(100, 0, 20))
        calls = [FunctionCall(f"call_{n}_{i}", name, json.dumps(args)) for i, (name, args) in enumerate(step)]
        return LLMResponse(id=f"resp_{n}", model=self.model, calls=calls, usage=Usage(100, 0, 20), latency_ms=1)
