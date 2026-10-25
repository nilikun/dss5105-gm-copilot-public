"""Tool registry: one place that knows every tool's name, kind, description and typed parameters.

Each tool module declares a Pydantic parameter model and registers its function with `@tool(...)`. The agent
gets JSON schemas generated from those models, and every call is validated before it runs — a malformed call
becomes an INVALID_ARGUMENT result the model can correct, never an exception.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

from app.tools.base import ErrorCode, ToolContext, ToolResult


@dataclass(frozen=True)
class ToolSpec:
    name: str
    kind: str  # retrieval | judgement | tracing | discovery | feasibility | action
    description: str
    params: type[BaseModel]
    fn: Callable[..., ToolResult]


REGISTRY: dict[str, ToolSpec] = {}


def tool(name: str, kind: str, description: str, params: type[BaseModel]):
    def register(fn: Callable[..., ToolResult]) -> Callable[..., ToolResult]:
        if name in REGISTRY:
            raise ValueError(f"tool {name} registered twice")
        REGISTRY[name] = ToolSpec(name, kind, description, params, fn)
        return fn
    return register


_STRIP = {"title", "default", "examples", "minLength", "maxLength", "minimum", "maximum", "exclusiveMinimum",
          "exclusiveMaximum", "minItems", "maxItems"}


def _strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Pydantic JSON schema → OpenAI strict function schema.

    Strict mode (the Responses API default) requires every property to be listed in `required` and
    additionalProperties=false. Optional parameters therefore become nullable (the model passes null) instead of
    being dropped — otherwise the model invents a value for them (observed: value=0, product=""). Range and length
    constraints are removed from the schema and enforced by Pydantic when the call is validated.
    """
    def walk(node: Any) -> Any:
        if isinstance(node, list):
            return [walk(v) for v in node]
        if not isinstance(node, dict):
            return node
        node = {k: walk(v) for k, v in node.items() if k not in _STRIP}
        if node.get("type") == "object" and "properties" in node:
            originally_required = set(node.get("required", []))
            for name, prop in node["properties"].items():
                if name not in originally_required:
                    node["properties"][name] = _nullable(prop)
            node["required"] = list(node["properties"])
            node["additionalProperties"] = False
        return node
    return walk(schema)


def _nullable(prop: dict[str, Any]) -> dict[str, Any]:
    if "anyOf" in prop:
        if not any(o.get("type") == "null" for o in prop["anyOf"]):
            prop = {**prop, "anyOf": prop["anyOf"] + [{"type": "null"}]}
        return prop
    if "$ref" in prop or "enum" in prop and "type" not in prop:
        desc = prop.get("description")
        inner = {k: v for k, v in prop.items() if k != "description"}
        out: dict[str, Any] = {"anyOf": [inner, {"type": "null"}]}
        if desc:
            out["description"] = desc
        return out
    t = prop.get("type")
    if isinstance(t, str):
        prop = {**prop, "type": [t, "null"]}
        if "enum" in prop:
            prop["enum"] = list(prop["enum"]) + [None]
    return prop


def _clean_schema(schema: dict[str, Any]) -> dict[str, Any]:
    return _strict_schema(schema)


def function_schemas(names: list[str] | None = None) -> list[dict[str, Any]]:
    """Tool definitions in the OpenAI Responses API format (strict)."""
    specs = [REGISTRY[n] for n in names] if names else list(REGISTRY.values())
    out = []
    for s in specs:
        params = _strict_schema(s.params.model_json_schema())
        params.setdefault("properties", {})
        params.setdefault("required", [])
        params["additionalProperties"] = False
        out.append({"type": "function", "name": s.name, "description": s.description, "parameters": params,
                    "strict": True})
    return out


def _sanitise(arguments: dict[str, Any]) -> dict[str, Any]:
    """Treat empty strings and nulls as 'not given', so the parameter model's defaults apply."""
    return {k: v for k, v in (arguments or {}).items() if v is not None and v != ""}


def call(ctx: ToolContext, name: str, arguments: dict[str, Any]) -> tuple[ToolResult, float]:
    """Validate and run one tool call. Returns the result and its duration in milliseconds."""
    t0 = time.perf_counter()
    spec = REGISTRY.get(name)
    if spec is None:
        res = ctx.fail(ErrorCode.INVALID_ARGUMENT, f"unknown tool '{name}'; available: {sorted(REGISTRY)}")
        return res, (time.perf_counter() - t0) * 1000
    try:
        params = spec.params(**_sanitise(arguments))
    except ValidationError as e:
        problems = "; ".join(f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in e.errors())
        res = ctx.fail(ErrorCode.INVALID_ARGUMENT, f"invalid arguments for {name}: {problems}")
        return res, (time.perf_counter() - t0) * 1000
    try:
        res = spec.fn(ctx, **params.model_dump())
    except Exception as e:  # a tool bug must not crash the turn; it is logged and reported as an error
        res = ctx.fail(ErrorCode.INVALID_ARGUMENT, f"{name} failed internally: {type(e).__name__}: {e}")
    return res, (time.perf_counter() - t0) * 1000


def load_all() -> dict[str, ToolSpec]:
    """Import every tool module so their @tool decorators run."""
    from app.tools.actions import proposals  # noqa: F401
    from app.tools.discovery import exceptions  # noqa: F401
    from app.tools.feasibility import feasibility  # noqa: F401
    from app.tools.judgement import normal, risk  # noqa: F401
    from app.tools.retrieval import activity, coverage, order_status, orders, production, time, workshops  # noqa: F401
    from app.tools.tracing import evidence  # noqa: F401
    return REGISTRY
