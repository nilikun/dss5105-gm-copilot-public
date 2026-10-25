"""Shared API dependencies: per-request database connection, LLM client, access code and rate limit."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from collections.abc import Iterator

from fastapi import Depends, HTTPException, Request

from app.config import SETTINGS
from app.db.database import open_db
from app.llm.base import LLMClient


def db_path(request: Request) -> str:
    return request.app.state.db_path


def get_db(request: Request) -> Iterator:
    conn = open_db(db_path(request))
    try:
        yield conn
    finally:
        conn.close()


def get_llm(request: Request) -> LLMClient:
    llm = getattr(request.app.state, "llm", None)
    if llm is None:
        from app.llm.openai_responses import OpenAIResponsesClient

        llm = request.app.state.llm = OpenAIResponsesClient()
    return llm


def require_access(request: Request) -> None:
    code = getattr(request.app.state, "access_code", SETTINGS.access_code)
    if code and request.headers.get("x-access-code") != code:
        raise HTTPException(status_code=401, detail="access code required")


_lock = threading.Lock()


def client_ip(request: Request) -> str:
    """The visitor's IP: Cloudflare's CF-Connecting-IP when the proxy is trusted, else the socket peer."""
    trusted = getattr(request.app.state, "trust_proxy", SETTINGS.trust_proxy)
    if trusted and request.headers.get("cf-connecting-ip"):
        return request.headers["cf-connecting-ip"]
    return request.client.host if request.client else "unknown"


def rate_limited(request: Request, _=Depends(require_access)) -> None:
    """Sliding one-minute window per client IP, kept on the app instance."""
    state = request.app.state
    limit = getattr(state, "rate_limit", SETTINGS.rate_limit_per_minute)
    ip = client_ip(request)
    now = time.time()
    with _lock:
        hits: dict[str, deque] = getattr(state, "rate_hits", None) or defaultdict(deque)
        state.rate_hits = hits
        q = hits[ip]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= limit:
            raise HTTPException(status_code=429, detail=f"rate limit: {limit} requests per minute")
        q.append(now)
