"""Provider-agnostic LLM interface (decision D3). The agent depends only on this module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class FunctionCall:
    call_id: str
    name: str
    arguments: str  # raw JSON text as produced by the model


@dataclass
class Usage:
    input_tokens: int = 0
    cached_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0


@dataclass
class LLMResponse:
    id: str
    model: str
    calls: list[FunctionCall] = field(default_factory=list)
    text: str = ""
    reasoning_summary: list[str] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    latency_ms: int = 0


class LLMClient(Protocol):
    model: str

    def create(self, *, instructions: str | None, input: list[dict[str, Any]], tools: list[dict[str, Any]] | None,
               tool_choice: str = "auto", previous_response_id: str | None = None,
               json_schema: dict[str, Any] | None = None) -> LLMResponse:
        """One model call. `input` holds messages or function_call_output items; with `previous_response_id` the
        provider keeps the earlier context. `json_schema` asks for a structured text answer (no tools)."""
        ...


class LLMError(Exception):
    pass


class BudgetExceeded(LLMError):
    pass
