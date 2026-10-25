"""Action gateway: proposal → manager confirms → deterministic executor → audit log → undo.

Only the API's confirm/cancel/undo endpoints call this module; no LLM tool does. Every execution writes an
append-only audit row with before/after state, so each action can be explained and reversed.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from app.clock import Clock
from app.db.database import dumps, loads, next_id


class GatewayError(Exception):
    pass


def _now(clock: Clock) -> str:
    return clock.now().isoformat(timespec="minutes")


def pending(db: sqlite3.Connection) -> list[dict[str, Any]]:
    return [{**dict(r), "payload": loads(r["payload"])}
            for r in db.execute("SELECT * FROM pending_actions WHERE status = 'pending' ORDER BY created_at")]


def get_action(db: sqlite3.Connection, action_id: str) -> dict[str, Any]:
    r = db.execute("SELECT * FROM pending_actions WHERE action_id = ?", (action_id,)).fetchone()
    if r is None:
        raise GatewayError(f"no proposal {action_id}")
    return {**dict(r), "payload": loads(r["payload"])}


def confirm(db: sqlite3.Connection, clock: Clock, action_id: str, actor: str = "manager") -> dict[str, Any]:
    a = get_action(db, action_id)
    if a["status"] != "pending":
        raise GatewayError(f"{action_id} is {a['status']}, not pending")
    p, now = a["payload"], _now(clock)
    before: Any = None
    if a["kind"] == "note":
        cur = db.execute("INSERT INTO notes (order_id, text, created_at) VALUES (?, ?, ?)",
                         (p["order_id"], p["text"], now))
        after = {"note_id": cur.lastrowid}
        summary = f"Note added to {p['order_id']}: \"{p['text']}\""
    elif a["kind"] == "message":
        cur = db.execute("INSERT INTO outbox (order_id, recipient_role, intent, body, created_at) "
                         "VALUES (?, ?, ?, ?, ?)", (p["order_id"], p["recipient_role"], p["intent"], p["body"], now))
        after = {"message_id": cur.lastrowid}
        summary = f"Message about {p['order_id']} placed in the outbox for the {p['recipient_role'].replace('_', ' ')}"
    elif a["kind"] == "watch":
        wid = next_id(db, "watch", "WT-")
        db.execute("INSERT INTO watches (watch_id, type, params, snapshot, description, priority, created_at, "
                   "expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                   (wid, p["type"], dumps(p["params"]), dumps(p["snapshot"]), p["description"], p["priority"], now,
                    p["expires_at"]))
        after = {"watch_id": wid}
        summary = f"Watch {wid} set: {p['description']}"
    elif a["kind"] == "cancel_watch":
        w = db.execute("SELECT status FROM watches WHERE watch_id = ?", (p["watch_id"],)).fetchone()
        if w is None or w["status"] != "active":
            raise GatewayError(f"watch {p['watch_id']} is no longer active")
        before = {"watch_id": p["watch_id"], "status": w["status"]}
        db.execute("UPDATE watches SET status = 'cancelled' WHERE watch_id = ?", (p["watch_id"],))
        after = {"watch_id": p["watch_id"], "status": "cancelled"}
        summary = f"Watch {p['watch_id']} cancelled"
    else:
        raise GatewayError(f"unknown action kind {a['kind']}")
    aid = next_id(db, "audit", "L-")
    db.execute("INSERT INTO audit_log (audit_id, action_id, kind, executed_at, actor, summary, before, after) "
               "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (aid, action_id, a["kind"], now, actor, summary, dumps(before),
                                                   dumps(after)))
    db.execute("UPDATE pending_actions SET status = 'executed', decided_at = ? WHERE action_id = ?", (now, action_id))
    db.commit()
    return {"audit_id": aid, "action_id": action_id, "kind": a["kind"], "summary": summary, "after": after}


def cancel(db: sqlite3.Connection, clock: Clock, action_id: str) -> dict[str, Any]:
    a = get_action(db, action_id)
    if a["status"] != "pending":
        raise GatewayError(f"{action_id} is {a['status']}, not pending")
    db.execute("UPDATE pending_actions SET status = 'cancelled', decided_at = ? WHERE action_id = ?",
               (_now(clock), action_id))
    db.commit()
    return {"action_id": action_id, "status": "cancelled"}


def undo(db: sqlite3.Connection, clock: Clock, audit_id: str) -> dict[str, Any]:
    r = db.execute("SELECT * FROM audit_log WHERE audit_id = ?", (audit_id,)).fetchone()
    if r is None:
        raise GatewayError(f"no audit entry {audit_id}")
    if r["undone_at"]:
        raise GatewayError(f"{audit_id} was already undone")
    after, before, now = loads(r["after"]), loads(r["before"]), _now(clock)
    if r["kind"] == "note":
        db.execute("UPDATE notes SET deleted_at = ? WHERE note_id = ?", (now, after["note_id"]))
    elif r["kind"] == "message":
        db.execute("UPDATE outbox SET status = 'retracted' WHERE message_id = ?", (after["message_id"],))
    elif r["kind"] == "watch":
        db.execute("UPDATE watches SET status = 'cancelled' WHERE watch_id = ?", (after["watch_id"],))
    elif r["kind"] == "cancel_watch":
        db.execute("UPDATE watches SET status = ? WHERE watch_id = ?", (before["status"], before["watch_id"]))
    db.execute("UPDATE audit_log SET undone_at = ? WHERE audit_id = ?", (now, audit_id))
    db.commit()
    return {"audit_id": audit_id, "undone_at": now, "summary": f"Undone: {r['summary']}"}


def audit_log(db: sqlite3.Connection, limit: int = 100) -> list[dict[str, Any]]:
    return [{**dict(r), "before": loads(r["before"]), "after": loads(r["after"])}
            for r in db.execute("SELECT * FROM audit_log ORDER BY rowid DESC LIMIT ?", (limit,))]
