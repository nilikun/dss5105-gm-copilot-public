"""get_activity — the co-pilot's own memory: notes, messages, watches, actions, alerts (Retrieval; tool 7)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.db.database import loads
from app.tools.base import ToolContext, ToolResult
from app.tools.registry import tool
from app.tools.retrieval.orders import normalize_order_id

# Which pending proposals each `kind` filter covers (None = all kinds, empty = none).
PENDING_KINDS: dict[str, set[str] | None] = {"all": None, "action": None, "watch": {"watch", "cancel_watch"},
                                             "note": {"note"}, "message": {"message", "outsourcing"}, "alert": set()}


class GetActivityParams(BaseModel):
    order_id: str | None = Field(None, description="Only activity about this order")
    kind: Literal["all", "note", "message", "watch", "action", "alert"] = "all"
    since: str | None = Field(None, description="ISO date; only activity on or after it")
    include_pending: bool = Field(True, description="Include proposals still waiting for confirmation")


@tool("get_activity", "retrieval",
      "What the co-pilot has recorded: notes on orders, messages in the outbox, watches (active / fired / "
      "cancelled), executed actions from the audit log, pending proposals, and alerts. Answers 'what did I ask "
      "you to do?' or 'any notes on ORD-120?'. An empty result is an answer, not an error.", GetActivityParams)
def get_activity(ctx: ToolContext, order_id: str | None = None, kind: str = "all", since: str | None = None,
                 include_pending: bool = True) -> ToolResult:
    oid = normalize_order_id(order_id) if order_id else None
    since_s = since or "0000"
    out: dict[str, list] = {}

    def about(text: str | None) -> bool:
        return oid is None or (text is not None and oid in text)

    if kind in ("all", "note"):
        out["notes"] = [dict(r) for r in ctx.db.execute(
            "SELECT note_id, order_id, text, created_at FROM notes WHERE deleted_at IS NULL AND created_at >= ? "
            "ORDER BY created_at", (since_s,)) if about(r["order_id"])]
    if kind in ("all", "message"):
        out["messages"] = [dict(r) for r in ctx.db.execute(
            "SELECT message_id, order_id, workshop_id, recipient_role, intent, body, created_at, status FROM outbox "
            "WHERE created_at >= ? ORDER BY created_at", (since_s,)) if about(r["order_id"] or r["body"])]
    if kind in ("all", "watch"):
        out["watches"] = []
        for r in ctx.db.execute("SELECT * FROM watches WHERE created_at >= ? ORDER BY created_at", (since_s,)):
            if about(r["params"]):
                w = dict(r)
                w["params"], w["snapshot"] = loads(w["params"]), loads(w["snapshot"])
                out["watches"].append(w)
    if kind in ("all", "action"):
        out["executed_actions"] = [dict(r) for r in ctx.db.execute(
            "SELECT audit_id, action_id, kind, executed_at, summary, undone_at FROM audit_log "
            "WHERE executed_at >= ? ORDER BY executed_at", (since_s,)) if about(r["summary"])]
    pending_kinds = PENDING_KINDS.get(kind)
    if include_pending and pending_kinds != set():
        # a watch proposed but not yet confirmed belongs to "watch" too (red-team R12: "so the watch is set now?")
        out["pending_proposals"] = [{"action_id": r["action_id"], "kind": r["kind"], "preview": r["preview"],
                                     "created_at": r["created_at"]}
                                    for r in ctx.db.execute(
                                        "SELECT * FROM pending_actions WHERE status = 'pending' "
                                        "ORDER BY created_at")
                                    if about(r["payload"]) and (pending_kinds is None or r["kind"] in pending_kinds)]
    if kind in ("all", "alert"):
        out["alerts"] = [dict(r) for r in ctx.db.execute(
            "SELECT notification_id, created_at, priority, kind, title, body, read FROM notifications "
            "WHERE created_at >= ? ORDER BY created_at DESC LIMIT 20", (since_s,)) if about(r["title"] + r["body"])]
    counts = {k: len(v) for k, v in out.items()}
    ev = ctx.evidence.register("activity", [k for k, v in counts.items() if v], "system activity records",
                               [{"kind": k, "items": v} for k, v in out.items()])
    return ctx.ok({"order_id": oid, "counts": counts, **out}, [ev])
