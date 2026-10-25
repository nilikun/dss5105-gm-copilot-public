"""Action tools — they only PROPOSE (TOOL_SPEC tools 14–17).

Each creates a row in pending_actions and returns a preview. Execution happens only through the UI confirm
endpoint (app/actions/gateway.py), which the model cannot call. Blast radius: a wrong draft, note or watch,
visible before confirmation and undoable after.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.db.database import dumps, loads, next_id
from app.domain import grounding, watches
from app.domain.calendar import days
from app.tools.base import ErrorCode, ToolContext, ToolResult
from app.tools.registry import tool
from app.tools.retrieval.orders import _derive, normalize_order_id

ROLES = Literal["planner", "floor_supervisor", "workshop", "customer_service"]


def _create(ctx: ToolContext, kind: str, payload: dict[str, Any], preview: str) -> dict[str, Any]:
    aid = next_id(ctx.db, "action", "A-")
    ctx.db.execute("INSERT INTO pending_actions (action_id, kind, payload, preview, created_at, turn_id) "
                   "VALUES (?, ?, ?, ?, ?, ?)",
                   (aid, kind, dumps(payload), preview, ctx.clock.now().isoformat(timespec="minutes"), ctx.turn_id))
    ctx.db.commit()
    return {"proposal_id": aid, "kind": kind, "preview": preview, "status": "pending",
            "requires_confirmation": True,
            "note": "Nothing has happened yet. The manager must confirm this proposal in the UI."}


def _open_order(ctx: ToolContext, order_id: str) -> dict[str, Any] | ToolResult:
    oid = normalize_order_id(order_id)
    row = ctx.db.execute("SELECT * FROM orders WHERE order_id = ?", (oid,)).fetchone() if oid else None
    if row is None:
        return ctx.fail(ErrorCode.NOT_FOUND, f"order '{order_id}' does not exist")
    return _derive(dict(row), ctx.clock.today())


# ----------------------------------------------------------------- propose_message
class ProposeMessageParams(BaseModel):
    order_id: str = Field(description="The order the message is about")
    recipient_role: ROLES = "planner"
    intent: Literal["chase", "inform", "ask"] = "chase"
    body: str | None = Field(None, description="Optional draft text. Every number, date and id in it must come "
                                               "from the order's facts; omit it to use the standard draft.")


@tool("propose_message", "action",
      "Draft a chase-up or message about an order to a planner, floor supervisor, workshop or customer service. "
      "Creates a PROPOSAL only — nothing is sent. The manager confirms it in the UI; confirmed messages go to an "
      "outbox, never to a real channel.", ProposeMessageParams)
def propose_message(ctx: ToolContext, order_id: str, recipient_role: str = "planner", intent: str = "chase",
                    body: str | None = None) -> ToolResult:
    o = _open_order(ctx, order_id)
    if isinstance(o, ToolResult):
        return o
    if o["status"] == "COMPLETE" and intent == "chase":
        return ctx.fail(ErrorCode.PRECONDITION_FAILED,
                        f"{o['order_id']} was completed on {o['completed_date']}; there is nothing to chase")
    timing = (f"{days(-o['days_to_due'])} overdue" if o["is_overdue"] else f"due in {days(o['days_to_due'])}")
    if body:
        allowed = grounding.Allowed()
        allowed.absorb(o, ctx.clock.today().year)
        problems = grounding.violations(body, allowed, ctx.clock.today().year)
        if problems:
            return ctx.fail(ErrorCode.INVALID_ARGUMENT, "the draft states facts that are not in the order record: "
                            + "; ".join(problems) + ". Fix the draft or omit body for the standard draft.")
        text = body.strip()
    else:
        text = (f"Hi, could you check on {o['order_id']} ({o['pieces']} × {o['product']} for {o['customer']})? "
                f"It is in {o['current_stage']}, due {o['due_date']} ({timing}); last recorded activity "
                f"{o['last_activity_date']}. Please reply with the expected completion date.")
    preview = f"Message to {recipient_role.replace('_', ' ')} about {o['order_id']}: \"{text}\""
    ev = ctx.evidence.register("orders", [o["order_id"]], f"facts used in the draft for {o['order_id']}",
                               [{k: o[k] for k in ("order_id", "customer", "product", "pieces", "current_stage",
                                                   "due_date", "last_activity_date")}])
    data = _create(ctx, "message", {"order_id": o["order_id"], "recipient_role": recipient_role, "intent": intent,
                                     "body": text}, preview)
    return ctx.ok({**data, "facts": {"stage": o["current_stage"], "due_date": o["due_date"], "timing": timing,
                                     "last_activity_date": o["last_activity_date"]}}, [ev])


# ----------------------------------------------------------------- propose_note
class ProposeNoteParams(BaseModel):
    order_id: str
    text: str = Field(max_length=500, description="The note, in the manager's words")


@tool("propose_note", "action",
      "Propose attaching a note to an order (e.g. 'customer agreed to a one-week delay'). Creates a PROPOSAL "
      "only; the manager confirms it. Never changes order fields.", ProposeNoteParams)
def propose_note(ctx: ToolContext, order_id: str, text: str) -> ToolResult:
    o = _open_order(ctx, order_id)
    if isinstance(o, ToolResult):
        return o
    preview = f"Add a note to {o['order_id']}: \"{text.strip()}\""
    return ctx.ok(_create(ctx, "note", {"order_id": o["order_id"], "text": text.strip()}, preview))


# ----------------------------------------------------------------- propose_watch
class ProposeWatchParams(BaseModel):
    type: Literal["order_stage_unchanged", "order_not_complete", "stage_below_normal", "reminder"]
    order_id: str | None = Field(None, description="For order_* types")
    by: str | None = Field(None, description="ISO date to check order_* watches (checked at 07:00 that day)")
    stage: Literal["KNITTING", "ASSEMBLY", "WASHING", "PACKING"] | None = Field(
        None, description="For stage_below_normal; optional condition for reminder")
    tier: Literal["briefing", "interrupt"] = Field("briefing", description="For stage_below_normal")
    at: str | None = Field(None, description="For reminder: ISO date (07:00) or ISO datetime")
    text: str | None = Field(None, description="For reminder: what to remind")
    priority: Literal["interrupt", "briefing"] = Field("interrupt", description="interrupt = push now; briefing = "
                                                                                 "put in the next briefing")
    expires_in_days: int = Field(14, ge=1, le=60)


@tool("propose_watch", "action",
      "Propose a standing check that fires on its own: order_stage_unchanged (order still in the same stage on a "
      "date), order_not_complete (order not done by a date), stage_below_normal (a stage's output drops), or "
      "reminder (at a time, optionally only if a stage is still below normal). Creates a PROPOSAL with a "
      "plain-language restatement; the manager confirms it. Rejects watches on completed orders.",
      ProposeWatchParams)
def propose_watch(ctx: ToolContext, type: str, order_id: str | None = None, by: str | None = None,
                  stage: str | None = None, tier: str = "briefing", at: str | None = None, text: str | None = None,
                  priority: str = "interrupt", expires_in_days: int = 14) -> ToolResult:
    now = ctx.clock.now()
    params: dict[str, Any] = {}
    snapshot: dict[str, Any] = {}
    if type in ("order_stage_unchanged", "order_not_complete"):
        if not order_id or not by:
            return ctx.fail(ErrorCode.INVALID_ARGUMENT, f"{type} needs order_id and by (ISO date)")
        o = _open_order(ctx, order_id)
        if isinstance(o, ToolResult):
            return o
        if o["status"] == "COMPLETE":
            return ctx.fail(ErrorCode.PRECONDITION_FAILED, f"{o['order_id']} was already completed on "
                            f"{o['completed_date']}; there is nothing to watch")
        try:
            when = watches.parse_when(by)
        except ValueError:
            return ctx.fail(ErrorCode.INVALID_ARGUMENT, "by must be an ISO date; resolve it with resolve_time first")
        if when <= now:
            return ctx.fail(ErrorCode.PRECONDITION_FAILED,
                            f"{by} 07:00 is not in the future (now {now:%Y-%m-%d %H:%M})")
        params, snapshot = {"order_id": o["order_id"], "by": when.date().isoformat()}, {"stage": o["current_stage"]}
        expires = when + timedelta(days=1)
    elif type == "stage_below_normal":
        if not stage:
            return ctx.fail(ErrorCode.INVALID_ARGUMENT, "stage_below_normal needs a stage")
        params, expires = {"stage": stage, "tier": tier}, now + timedelta(days=expires_in_days)
    else:
        if not at or not text:
            return ctx.fail(ErrorCode.INVALID_ARGUMENT, "reminder needs at (ISO date or datetime) and text")
        try:
            when = watches.parse_when(at)
        except ValueError:
            return ctx.fail(ErrorCode.INVALID_ARGUMENT, "at must be ISO; resolve it with resolve_time first")
        if when <= now:
            return ctx.fail(ErrorCode.PRECONDITION_FAILED, f"{at} is not in the future")
        params = {"at": when.isoformat(timespec="minutes"), "text": text.strip(), **({"stage": stage} if stage else {})}
        expires = when + timedelta(days=1)
    for r in ctx.db.execute("SELECT * FROM watches WHERE status = 'active' AND type = ?", (type,)):
        if loads(r["params"]) == params:
            return ctx.ok({"duplicate_of": r["watch_id"], "description": r["description"],
                           "note": "An identical watch is already active; no new proposal created."})
    description = watches.describe(type, params, snapshot)
    payload = {"type": type, "params": params, "snapshot": snapshot, "priority": priority,
               "expires_at": expires.isoformat(timespec="minutes"), "description": description}
    return ctx.ok(_create(ctx, "watch", payload, f"Set a watch: {description}"))


# ----------------------------------------------------------------- propose_cancel_watch
class ProposeCancelWatchParams(BaseModel):
    watch_id: str = Field(description="Watch id such as WT-3 (see get_activity)")


@tool("propose_cancel_watch", "action",
      "Propose cancelling an active watch. Creates a PROPOSAL; the manager confirms it. History is kept.",
      ProposeCancelWatchParams)
def propose_cancel_watch(ctx: ToolContext, watch_id: str) -> ToolResult:
    r = ctx.db.execute("SELECT * FROM watches WHERE watch_id = ?", (watch_id.strip().upper(),)).fetchone()
    if r is None:
        return ctx.fail(ErrorCode.NOT_FOUND, f"no watch {watch_id}")
    if r["status"] != "active":
        return ctx.fail(ErrorCode.PRECONDITION_FAILED, f"{r['watch_id']} is {r['status']}, not active")
    return ctx.ok(_create(ctx, "cancel_watch", {"watch_id": r["watch_id"]},
                          f"Cancel watch {r['watch_id']}: {r['description']}"))

