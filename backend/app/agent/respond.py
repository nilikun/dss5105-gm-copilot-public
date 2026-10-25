"""The structured final answer (`respond`), and the reply object the API returns."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.agent import prompts

Kind = Literal["answer", "estimate", "clarify", "refuse", "propose", "reject"]


class Option(BaseModel):
    label: str = Field(description="Short button label, e.g. 'ORD-120 · Vest · 1,500'")
    value: str = Field(description="The exact message the manager would send if they pick it")


class RespondArgs(BaseModel):
    kind: Kind
    headline: str = Field(description="At most 3 short lines; the direct answer first")
    details: str | None = Field(None, description="Optional markdown with supporting figures and assumptions")
    evidence_ids: list[str] = Field(default_factory=list, description="Evidence ids (E…) the reply relies on")
    clarification_question: str | None = Field(None, description="For kind=clarify")
    options: list[Option] = Field(default_factory=list, description="For kind=clarify: 2–6 choices", max_length=6)
    proposal_ids: list[str] = Field(default_factory=list, description="For kind=propose: ids from propose_* tools")
    followups: list[str] = Field(default_factory=list, description="Up to 3 short next questions", max_length=3)


def respond_tool_schema() -> dict[str, Any]:
    from app.tools.registry import _strict_schema

    return {"type": "function", "name": "respond", "description": prompts.load("respond_tool").body,
            "parameters": _strict_schema(RespondArgs.model_json_schema()), "strict": True}


def parse_respond(arguments: str) -> RespondArgs:
    """Strict-mode calls send null for unused fields; drop them so the model's defaults apply."""
    import json

    raw = json.loads(arguments or "{}")
    return RespondArgs.model_validate({k: v for k, v in raw.items() if v is not None})


class Reply(BaseModel):
    turn_id: str
    conversation_id: str
    kind: str  # Kind, or "fallback" when no verified reply could be produced
    headline: str
    details: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    clarification_question: str | None = None
    options: list[Option] = Field(default_factory=list)
    proposals: list[dict[str, Any]] = Field(default_factory=list)
    followups: list[str] = Field(default_factory=list)
    grounded: bool = True
    verifier_rejections: int = 0
    critic: dict[str, Any] | None = None
    llm_calls: int = 0
    cost_usd: float = 0.0
    latency_s: float = 0.0
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
