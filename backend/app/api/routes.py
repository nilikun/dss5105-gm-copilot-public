"""Everything except chat: briefing, evidence, actions, watches, alerts, clock, settings, traces, usage, tools."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.actions import gateway
from app.api.deps import get_db, get_llm, rate_limited, require_access
from app.clock import DbClock
from app.clock.advancer import list_scenarios
from app.config import SETTINGS
from app.db.database import get_setting, loads, reset_in_place, set_setting
from app.llm import budget
from app.observability.trace import load_turn, recent_turns
from app.tools import REGISTRY
from app.tools.base import EvidenceStore
from app.workflows import briefing, notifications, scheduler

router = APIRouter(prefix="/api", dependencies=[Depends(require_access)])
public = APIRouter(prefix="/api")


@public.get("/health")
def health() -> dict:
    return {"ok": True}


# ----------------------------------------------------------------- overview
@router.get("/state")
def state(db=Depends(get_db)) -> dict:
    clock = DbClock(db)
    s = clock.state()
    return {
        "now": clock.now().isoformat(timespec="minutes"), "mode": s["mode"], "scenario": s["scenario"],
        "data_through": db.execute("SELECT MAX(date) FROM production_log").fetchone()[0],
        "unread_alerts": db.execute("SELECT COUNT(*) FROM notifications WHERE read = 0").fetchone()[0],
        "unread_p1": db.execute("SELECT COUNT(*) FROM notifications WHERE read = 0 AND priority = 'P1'").fetchone()[0],
        "pending_actions": db.execute("SELECT COUNT(*) FROM pending_actions WHERE status = 'pending'").fetchone()[0],
        "active_watches": db.execute("SELECT COUNT(*) FROM watches WHERE status = 'active'").fetchone()[0],
        "usage": budget.summary(db), "settings": _settings(db),
    }


def _settings(db) -> dict:
    return {"critic_enabled": get_setting(db, "critic_enabled", SETTINGS.critic_enabled_default),
            "interrupt_cap": get_setting(db, "interrupt_cap", notifications.DEFAULT_INTERRUPT_CAP),
            "model": SETTINGS.llm_model, "reasoning_effort": SETTINGS.reasoning_effort,
            "daily_budget_usd": SETTINGS.daily_budget_usd}


class SettingsIn(BaseModel):
    critic_enabled: bool | None = None
    interrupt_cap: int | None = Field(None, ge=0, le=20)


@router.get("/settings")
def get_settings(db=Depends(get_db)) -> dict:
    return _settings(db)


@router.patch("/settings")
def patch_settings(body: SettingsIn, db=Depends(get_db)) -> dict:
    for k, v in body.model_dump(exclude_none=True).items():
        set_setting(db, k, v)
    return _settings(db)


# ----------------------------------------------------------------- briefing
@router.get("/briefing")
def get_briefing(db=Depends(get_db)) -> dict:
    return briefing.ensure(db, DbClock(db))


@router.post("/briefing/narrate", dependencies=[Depends(rate_limited)])
def narrate_briefing(force: bool = False, db=Depends(get_db), llm=Depends(get_llm)) -> dict:
    """Write the summary; force=true rewrites one that already exists."""
    return briefing.narrate(db, DbClock(db), llm, force=force)


@router.post("/briefing/rebuild")
def rebuild_briefing(db=Depends(get_db)) -> dict:
    """Recompute today's structured briefing from the current data; the written summary is cleared."""
    return briefing.ensure(db, DbClock(db), rebuild=True)


# ----------------------------------------------------------------- evidence
@router.get("/evidence/{eid}")
def evidence(eid: str, db=Depends(get_db)) -> dict:
    item = EvidenceStore(db, DbClock(db)).get(eid.upper())
    if item is None:
        raise HTTPException(status_code=404, detail=f"no evidence {eid}")
    return item


# ----------------------------------------------------------------- actions (the only way anything is executed)
@router.get("/proposals")
def proposals(status: str = "pending", db=Depends(get_db)) -> list[dict]:
    return [{**dict(r), "payload": loads(r["payload"])}
            for r in db.execute("SELECT * FROM pending_actions WHERE status = ? ORDER BY created_at DESC", (status,))]


@router.post("/proposals/{action_id}/confirm")
def confirm(action_id: str, db=Depends(get_db)) -> dict:
    try:
        return gateway.confirm(db, DbClock(db), action_id)
    except gateway.GatewayError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.post("/proposals/{action_id}/cancel")
def cancel(action_id: str, db=Depends(get_db)) -> dict:
    try:
        return gateway.cancel(db, DbClock(db), action_id)
    except gateway.GatewayError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.get("/audit")
def audit(db=Depends(get_db)) -> list[dict]:
    return gateway.audit_log(db)


@router.post("/audit/{audit_id}/undo")
def undo(audit_id: str, db=Depends(get_db)) -> dict:
    try:
        return gateway.undo(db, DbClock(db), audit_id)
    except gateway.GatewayError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.get("/outbox")
def outbox(db=Depends(get_db)) -> list[dict]:
    return [dict(r) for r in db.execute("SELECT * FROM outbox ORDER BY message_id DESC")]


# ----------------------------------------------------------------- watches and alerts
@router.get("/watches")
def watches(db=Depends(get_db)) -> list[dict]:
    return [{**dict(r), "params": loads(r["params"]), "snapshot": loads(r["snapshot"])}
            for r in db.execute("SELECT * FROM watches ORDER BY created_at DESC")]


@router.post("/watches/{watch_id}/cancel")
def cancel_watch(watch_id: str, db=Depends(get_db)) -> dict:
    """The manager cancels a watch from the Watches page: their click is the confirmation. It goes through the
    gateway like any action, so it is audited and can be undone."""
    try:
        return gateway.cancel_watch_by_manager(db, DbClock(db), watch_id.strip().upper())
    except gateway.GatewayError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.get("/notifications")
def list_notifications(unread_only: bool = False, db=Depends(get_db)) -> list[dict]:
    sql = "SELECT * FROM notifications" + (" WHERE read = 0" if unread_only else "") + \
          " ORDER BY notification_id DESC LIMIT 100"
    return [{**dict(r), "evidence_ids": loads(r["evidence_ids"])} for r in db.execute(sql)]


class ReadIn(BaseModel):
    ids: list[int] | None = None
    read: bool = True  # false marks the alerts unread again


@router.post("/notifications/read")
def mark_read(body: ReadIn, db=Depends(get_db)) -> dict:
    flag = 1 if body.read else 0
    if body.ids:
        db.executemany("UPDATE notifications SET read = ? WHERE notification_id = ?", [(flag, i) for i in body.ids])
    else:
        db.execute("UPDATE notifications SET read = ?", (flag,))
    db.commit()
    return {"ok": True}


# ----------------------------------------------------------------- clock and scenarios
@router.get("/clock")
def clock_info(db=Depends(get_db)) -> dict:
    clock = DbClock(db)
    s = clock.state()
    now = clock.now()
    return {"now": now.isoformat(timespec="minutes"), "mode": s["mode"], "scenario": s["scenario"],
            "processed_through": get_setting(db, "processed_through"),
            "data_through": db.execute("SELECT MAX(date) FROM production_log").fetchone()[0],
            "next_boundary": scheduler.next_boundary(now).isoformat(timespec="minutes"),
            "min": scheduler.START.isoformat(timespec="minutes"),
            "max": (scheduler.START + scheduler.MAX_HORIZON).isoformat(timespec="minutes")}


class AdvanceIn(BaseModel):
    days: int = Field(0, ge=0, le=30)
    hours: int = Field(0, ge=0, le=23)


@router.post("/clock/advance")
def advance(body: AdvanceIn, db=Depends(get_db)) -> dict:
    if DbClock(db).state()["mode"] != "sim":
        raise HTTPException(status_code=409, detail="the clock is in real mode; switch to sim to advance it")
    return scheduler.advance(db, days=body.days, hours=body.hours)


class GotoIn(BaseModel):
    when: datetime = Field(description="Factory date and time to jump to, e.g. 2026-04-03T07:00")


@router.post("/clock/goto")
def goto(body: GotoIn, db=Depends(get_db)) -> dict:
    """Jump the simulated clock to any time from 1 Apr 07:00; going back replays the scenario from the start."""
    try:
        report = scheduler.goto(db, body.when.replace(tzinfo=None))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return {**clock_info(db), "rewound": report["rewound"], "boundaries": len(report["boundaries"])}


class ModeIn(BaseModel):
    mode: Literal["sim", "real"]


@router.post("/clock/mode")
def set_mode(body: ModeIn, db=Depends(get_db)) -> dict:
    DbClock(db).set_mode(body.mode)
    return clock_info(db)


class ResetIn(BaseModel):
    scenario: str = "baseline"


@router.post("/clock/reset")
def reset(body: ResetIn, db=Depends(get_db)) -> dict:
    if body.scenario not in {s.name for s in list_scenarios()}:
        raise HTTPException(status_code=404, detail=f"no scenario {body.scenario}")
    reset_in_place(db, body.scenario)
    scheduler.start_day(db)
    return clock_info(db)


@router.get("/scenarios")
def scenarios() -> list[dict]:
    return [{"name": s.name, "title": s.title, "description": s.description} for s in list_scenarios()]


# ----------------------------------------------------------------- observability
@router.get("/traces")
def traces(limit: int = 30, db=Depends(get_db)) -> list[dict]:
    return recent_turns(db, limit)


@router.get("/traces/{turn_id}")
def trace(turn_id: str, db=Depends(get_db)) -> list[dict]:
    return load_turn(db, turn_id)


@router.get("/usage")
def usage(db=Depends(get_db)) -> dict:
    return budget.summary(db)


@router.get("/tools")
def tools() -> list[dict]:
    return [{"name": s.name, "kind": s.kind, "description": s.description} for s in REGISTRY.values()]
