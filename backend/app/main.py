"""FastAPI application.

    uv run uvicorn app.main:app --reload --port 8000

Serves /api/* and, if the frontend has been built (frontend/dist), the web app itself on the same origin.
"""

from __future__ import annotations

import logging
import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import chat, routes
from app.clock import DbClock
from app.config import REPO_DIR, SETTINGS
from app.db.database import open_db
from app.observability.logging_setup import configure
from app.workflows import scheduler

log = logging.getLogger("gm.app")
FRONTEND_DIST = REPO_DIR / "frontend" / "dist"


def _real_clock_ticker(app: FastAPI, stop: threading.Event) -> None:
    """In real mode, run the 07:00 boundaries as wall-clock time passes them."""
    while not stop.wait(30):
        try:
            db = open_db(app.state.db_path)
            clock = DbClock(db)
            if clock.state()["mode"] == "real":
                scheduler.catch_up(db, clock)
            db.close()
        except Exception:  # never kill the ticker
            log.exception("clock ticker failed")


def create_app(db_path: str | None = None, llm=None, access_code: str | None = None,
               start_ticker: bool = True) -> FastAPI:
    configure()
    stop = threading.Event()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        db = open_db(app.state.db_path)
        scheduler.start_day(db)
        db.close()
        if start_ticker:
            threading.Thread(target=_real_clock_ticker, args=(app, stop), daemon=True).start()
        log.info("GM Co-Pilot API ready · model %s · db %s", SETTINGS.llm_model, app.state.db_path)
        yield
        stop.set()

    app = FastAPI(title="GM Co-Pilot API", version="0.2.0", lifespan=lifespan)
    app.state.db_path = db_path or SETTINGS.db_path
    app.state.llm = llm
    app.state.access_code = SETTINGS.access_code if access_code is None else access_code
    app.state.rate_limit = SETTINGS.rate_limit_per_minute
    app.state.started = time.time()
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    app.include_router(routes.public)
    app.include_router(routes.router)
    app.include_router(chat.router)

    if FRONTEND_DIST.exists():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            target = FRONTEND_DIST / path
            return FileResponse(target if path and target.is_file() else FRONTEND_DIST / "index.html")

    return app


app = create_app()
