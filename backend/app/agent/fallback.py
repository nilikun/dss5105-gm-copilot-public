"""Degrade, never fabricate: when no reply passes the verifier, show what the tools actually returned."""

from __future__ import annotations

import json
from typing import Any


def render(tool_log: list[dict[str, Any]], reason: str) -> tuple[str, str]:
    headline = "I could not produce a verified answer, so here is exactly what the data tools returned."
    lines = [f"_Reason: {reason}_", ""]
    if not tool_log:
        lines.append("No tool was called in this turn.")
    for t in tool_log:
        status = "ok" if t["ok"] else f"error: {t.get('error')}"
        lines.append(f"- **{t['tool']}** {json.dumps(t['args'], ensure_ascii=False)} → {status}")
        if t["ok"] and t.get("summary"):
            lines.append(f"  - {t['summary']}")
    return headline, "\n".join(lines)
