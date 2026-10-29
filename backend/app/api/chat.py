"""Chat: one manager message → one agent turn, streamed as Server-Sent Events.

event: step   — each trace event (plan, action, draft, verifier, …) as it happens ("Show thinking")
event: reply  — the final verified reply
event: error  — budget reached or internal error
"""

from __future__ import annotations

import json
import logging
import queue
import threading

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agent.runtime import Agent
from app.api.deps import db_path, get_db, get_llm, rate_limited, require_access
from app.clock import DbClock
from app.config import SETTINGS
from app.db.database import get_setting, loads, open_db
from app.llm.base import BudgetExceeded, LLMClient, LLMError

log = logging.getLogger("gm.api")
router = APIRouter(prefix="/api", dependencies=[Depends(require_access)])


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = None


def _agent(db, llm: LLMClient) -> Agent:
    return Agent(db, DbClock(db), llm, critic_enabled=get_setting(db, "critic_enabled",
                                                                  SETTINGS.critic_enabled_default))


@router.post("/chat", dependencies=[Depends(rate_limited)])
def chat(body: ChatIn, request: Request, llm: LLMClient = Depends(get_llm)) -> StreamingResponse:
    q: queue.Queue = queue.Queue()
    path = db_path(request)

    def work() -> None:
        db = open_db(path)
        try:
            reply = _agent(db, llm).run(body.message, body.conversation_id, sink=lambda e: q.put(("step", e)))
            q.put(("reply", reply.model_dump(mode="json")))
        except BudgetExceeded as e:
            q.put(("error", {"code": "budget", "message": str(e)}))
        except LLMError as e:
            q.put(("error", {"code": "llm", "message": str(e)[:300]}))
        except Exception as e:  # surfaced to the UI, logged in full
            log.exception("chat turn failed")
            q.put(("error", {"code": "internal", "message": f"{type(e).__name__}: {str(e)[:200]}"}))
        finally:
            q.put(None)
            db.close()

    threading.Thread(target=work, daemon=True).start()

    def stream():
        while (item := q.get()) is not None:
            event, data = item
            yield f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/chat/sync", dependencies=[Depends(rate_limited)])
def chat_sync(body: ChatIn, db=Depends(get_db), llm: LLMClient = Depends(get_llm)) -> dict:
    """Non-streaming variant (scripts, tests)."""
    try:
        return _agent(db, llm).run(body.message, body.conversation_id).model_dump(mode="json")
    except BudgetExceeded as e:
        raise HTTPException(status_code=429, detail=str(e)) from e


@router.get("/conversations")
def conversations(db=Depends(get_db)) -> list[dict]:
    return [dict(r) for r in db.execute("SELECT * FROM conversations ORDER BY created_at DESC LIMIT 50")]


@router.get("/conversations/{cid}")
def conversation(cid: str, db=Depends(get_db)) -> list[dict]:
    return [{"role": r["role"], "content": loads(r["content"]), "turn_id": r["turn_id"], "created_at": r["created_at"]}
            for r in db.execute("SELECT * FROM messages WHERE conversation_id = ? ORDER BY id", (cid,))]


@router.delete("/conversations/{cid}")
def delete_conversation(cid: str, db=Depends(get_db)) -> dict:
    """Remove a chat and its messages from the sidebar. The thinking logs (traces) stay: they are the audit trail
    of what the AI executed."""
    if db.execute("SELECT 1 FROM conversations WHERE conversation_id = ?", (cid,)).fetchone() is None:
        raise HTTPException(status_code=404, detail=f"no conversation {cid}")
    db.execute("DELETE FROM messages WHERE conversation_id = ?", (cid,))
    db.execute("DELETE FROM conversations WHERE conversation_id = ?", (cid,))
    db.commit()
    return {"deleted": cid}


@router.delete("/conversations")
def delete_all_conversations(db=Depends(get_db)) -> dict:
    n = db.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
    db.execute("DELETE FROM messages")
    db.execute("DELETE FROM conversations")
    db.commit()
    return {"deleted": n}
