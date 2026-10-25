"""get_evidence — any figure back to the rows behind it (Tracing; TOOL_SPEC tool 11)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.tools.base import ErrorCode, ToolContext, ToolResult
from app.tools.registry import tool


class GetEvidenceParams(BaseModel):
    evidence_ids: list[str] = Field(description="Evidence ids such as E12, from earlier tool results", max_length=10)


@tool("get_evidence", "tracing",
      "Return the source rows behind evidence ids (e.g. when the manager asks 'why?' or 'show me'). Goes back to "
      "the data rather than paraphrasing an earlier answer. Flags evidence created before the clock last moved "
      "as possibly stale.", GetEvidenceParams)
def get_evidence(ctx: ToolContext, evidence_ids: list[str]) -> ToolResult:
    found, missing = [], []
    now = ctx.clock.now().isoformat(timespec="minutes")
    for eid in evidence_ids:
        item = ctx.evidence.get(eid.strip().upper())
        if item is None:
            missing.append(eid)
            continue
        item["stale"] = item["as_of"][:10] != now[:10]
        item["row_count"] = len(item["rows"])
        found.append(item)
    if not found:
        return ctx.fail(ErrorCode.NOT_FOUND, f"no evidence with ids {missing}")
    # re-register so the rows shown in this turn are evidence of this turn
    refs = [ctx.evidence.register(f["source"], f["keys"], f"re-opened {f['evidence_id']}: {f['description']}",
                                  f["rows"]) for f in found]
    warnings = [f"evidence {f['evidence_id']} was recorded at {f['as_of']}; the data may have changed since"
                for f in found if f["stale"]]
    if missing:
        warnings.append(f"not found: {missing}")
    return ctx.ok({"evidence": found}, refs, warnings=warnings)
