"""One logging configuration for the API, the CLI and the evaluation runner."""

from __future__ import annotations

import logging
import sys


def configure(level: int = logging.INFO) -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    root = logging.getLogger()
    if not any(getattr(h, "_gm", False) for h in root.handlers):
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(logging.Formatter("%(message)s"))
        h._gm = True  # type: ignore[attr-defined]
        root.addHandler(h)
    root.setLevel(level)
    for noisy in ("httpx", "httpx2", "httpcore", "openai", "openai._base_client", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
