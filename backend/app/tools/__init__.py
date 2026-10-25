"""Tools: typed, tested functions the agent can call. See docs/TOOL_SPEC.md and app/tools/registry.py."""

from app.tools.registry import REGISTRY, call, function_schemas, load_all

load_all()
TOOLS = {name: spec.fn for name, spec in REGISTRY.items()}

__all__ = ["REGISTRY", "TOOLS", "call", "function_schemas"]
