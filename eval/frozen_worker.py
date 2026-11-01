"""One isolated agent attempt. Only this adapter imports production code; never used as scoring truth."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path


def run(backend, request, output):
    sys.path.insert(0, str(backend.resolve()))
    from app.agent.runtime import Agent
    from app.clock import SimClock
    from app.config import SETTINGS
    from app.db.database import connect
    from app.llm.openai_responses import OpenAIResponsesClient
    from app.observability.trace import load_turn

    payload = json.loads(request.read_text(encoding="utf-8"))
    settings, item = payload["settings"], payload["item"]
    client = OpenAIResponsesClient(
        model=settings["model"], reasoning_effort=settings["reasoning_effort"], timeout=payload["timeout_seconds"]
    )
    client.client = client.client.with_options(max_retries=0)
    original = client.client.responses.create
    calls = []
    call_path = output.with_suffix(".calls.jsonl")

    def metered(**kwargs):
        if len(calls) >= payload["max_api_calls"]:
            raise RuntimeError("Frozen API call cap reached")
        kwargs["max_output_tokens"] = settings["max_output_tokens"]
        call = {"usage": None, "error": None, "model": settings["model"]}
        call["call_index"] = len(calls)
        with call_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(call | {"pending": True}) + "\n")
        started = time.perf_counter()
        try:
            response = original(**kwargs)
            call["model"] = response.model
            if response.usage:
                u = response.usage
                call["usage"] = {
                    "input_tokens": u.input_tokens,
                    "cached_input_tokens": u.input_tokens_details.cached_tokens,
                    "output_tokens": u.output_tokens,
                    "reasoning_tokens": u.output_tokens_details.reasoning_tokens,
                }
            return response
        except Exception as exc:
            call["error"] = {
                "type": type(exc).__name__,
                "message": str(exc).replace(SETTINGS.openai_api_key, "[redacted]")[:1000],
            }
            raise
        finally:
            call["latency_seconds"] = time.perf_counter() - started
            calls.append(call)
            with call_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(call | {"pending": False}) + "\n")

    client.client.responses.create = metered
    db = connect(backend.parent / "data")
    result = {"reply": {}, "context_replies": [], "api_calls": calls, "error": None}
    started = time.perf_counter()
    try:
        agent = Agent(db, SimClock(datetime.fromisoformat(payload["clock"])), client, critic_enabled=False)
        cid = None
        for turn in item.get("context_turns", []):
            reply = agent.run(turn["user"], cid)
            cid = reply.conversation_id
            result["context_replies"].append(reply.model_dump(mode="json"))
        result["reply"] = agent.run(item["question"], cid).model_dump(mode="json")
    except Exception as exc:
        result["error"] = {
            "type": type(exc).__name__,
            "message": str(exc).replace(SETTINGS.openai_api_key, "[redacted]")[:1000],
        }
    result["wall_seconds"] = time.perf_counter() - started
    result["unconfirmed_actions"] = db.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
    result["traces"] = [load_turn(db, r[0]) for r in db.execute("SELECT DISTINCT turn_id FROM traces ORDER BY id")]
    db.close()
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("backend", "request", "output"):
        parser.add_argument("--" + arg, type=Path, required=True)
    args = parser.parse_args()
    run(args.backend, args.request, args.output)
