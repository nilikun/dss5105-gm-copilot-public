"""OpenAI adapter on the Responses API.

Why Responses and not Chat Completions: for GPT-5.x reasoning models, function tools combined with reasoning
are only supported on /v1/responses (tested 2026-10-14 with gpt-5.6-luna). Context across tool steps is kept
server-side via previous_response_id.
"""

from __future__ import annotations

import time
from typing import Any

from openai import APIError, OpenAI

from app.config import SETTINGS
from app.llm.base import FunctionCall, LLMError, LLMResponse, Usage


class OpenAIResponsesClient:
    def __init__(self, model: str | None = None, api_key: str | None = None, reasoning_effort: str | None = None,
                 timeout: float = 60.0):
        key = api_key or SETTINGS.openai_api_key
        if not key:
            raise LLMError("OPENAI_API_KEY is not set (backend/.env)")
        self.model = model or SETTINGS.llm_model
        self.effort = reasoning_effort or SETTINGS.reasoning_effort
        self.client = OpenAI(api_key=key, timeout=timeout, max_retries=2)

    def create(self, *, instructions: str | None, input: list[dict[str, Any]], tools: list[dict[str, Any]] | None,
               tool_choice: str = "auto", previous_response_id: str | None = None,
               json_schema: dict[str, Any] | None = None) -> LLMResponse:
        kwargs: dict[str, Any] = {"model": self.model, "input": input}
        if instructions:
            kwargs["instructions"] = instructions
        if previous_response_id:
            kwargs["previous_response_id"] = previous_response_id
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice
            kwargs["parallel_tool_calls"] = True
        if json_schema:
            kwargs["text"] = {"format": {"type": "json_schema", "name": json_schema.get("name", "answer"),
                                         "schema": json_schema["schema"], "strict": True}}
        if self.effort and self.effort != "none":
            kwargs["reasoning"] = {"effort": self.effort, "summary": "auto"}
        t0 = time.perf_counter()
        try:
            r = self.client.responses.create(**kwargs)
        except APIError as e:
            raise LLMError(f"OpenAI API error: {e}") from e
        latency = int((time.perf_counter() - t0) * 1000)
        out = LLMResponse(id=r.id, model=r.model, latency_ms=latency)
        for item in r.output:
            if item.type == "function_call":
                out.calls.append(FunctionCall(item.call_id, item.name, item.arguments))
            elif item.type == "reasoning":
                out.reasoning_summary += [s.text for s in (item.summary or []) if getattr(s, "text", None)]
            elif item.type == "message":
                out.text += "".join(getattr(c, "text", "") or "" for c in item.content)
        u = r.usage
        if u is not None:
            out.usage = Usage(input_tokens=u.input_tokens or 0,
                              cached_tokens=getattr(u.input_tokens_details, "cached_tokens", 0) or 0,
                              output_tokens=u.output_tokens or 0,
                              reasoning_tokens=getattr(u.output_tokens_details, "reasoning_tokens", 0) or 0)
        return out
