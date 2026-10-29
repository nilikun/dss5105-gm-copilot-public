"""The interactive agent: one ReAct loop per manager message (docs/PLAN.md §6).

    question → context → [LLM chooses tools → tools run → results back]* → respond (draft)
             → verifier (code) → pass: [critic, optional] → reply
                                → fail: one repair with the violations → else fallback to raw tool output

The LLM never computes and never executes: tools compute, the action gateway executes after the manager confirms.
Every step is traced (app/observability/trace.py).
"""

from __future__ import annotations

import json
import re
import sqlite3
import time
import uuid
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from app.agent import calendar_context, fallback, feasibility_view, order_status, prompts
from app.agent import critic as critic_mod
from app.agent.respond import Reply, RespondArgs, parse_respond, respond_tool_schema
from app.agent.verifier import verify
from app.clock import Clock
from app.config import HISTORY_TURNS, MAX_REPAIRS, MAX_TOOL_STEPS
from app.db.database import dumps, loads
from app.llm import budget
from app.llm.base import LLMClient
from app.observability.trace import Tracer, summarize_result
from app.tools import registry
from app.tools.base import ToolContext

MAX_OUTPUT_CHARS = 16000
ORDER_ID = re.compile(r"\bORD-\d{3}\b")


ACTION_KINDS = {"reject", "propose"}  # replies about a requested action, never overridden by the status contract


class Agent:
    def __init__(self, db: sqlite3.Connection, clock: Clock, llm: LLMClient, critic_enabled: bool = False,
                 daily_budget: float | None = None):
        self.db, self.clock, self.llm = db, clock, llm
        self.critic_enabled = critic_enabled
        self.daily_budget = daily_budget

    # ----------------------------------------------------------------- conversation memory
    def _ensure_conversation(self, conversation_id: str | None, first_text: str) -> str:
        if conversation_id and self.db.execute("SELECT 1 FROM conversations WHERE conversation_id = ?",
                                               (conversation_id,)).fetchone():
            return conversation_id
        cid = conversation_id or uuid.uuid4().hex[:12]
        self.db.execute("INSERT INTO conversations (conversation_id, created_at, title) VALUES (?, ?, ?)",
                        (cid, time.time(), first_text[:80]))
        self.db.commit()
        return cid

    def _history(self, cid: str) -> tuple[list[dict[str, Any]], list[str]]:
        rows = self.db.execute("SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
                               (cid, HISTORY_TURNS * 2)).fetchall()[::-1]
        items, focus = [], []
        for r in rows:
            c = loads(r["content"])
            if r["role"] == "user":
                text = c["text"]
            else:
                text = "\n".join(x for x in [c.get("headline"), c.get("details") or "",
                                             c.get("clarification_question") or ""] if x)
                if c.get("options"):
                    text += "\nOptions offered: " + "; ".join(o["value"] for o in c["options"])
            items.append({"role": r["role"], "content": text})
            focus += ORDER_ID.findall(text)
        return items, list(dict.fromkeys(reversed(focus)))[:5]

    def _save(self, cid: str, role: str, content: dict[str, Any], turn_id: str) -> None:
        self.db.execute("INSERT INTO messages (conversation_id, role, content, turn_id, created_at) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (cid, role, dumps(content), turn_id, time.time()))
        self.db.commit()

    # ----------------------------------------------------------------- one turn
    def run(self, user_text: str, conversation_id: str | None = None,
            sink: Callable[[dict[str, Any]], None] | None = None) -> Reply:
        t0 = time.perf_counter()
        turn_id = uuid.uuid4().hex[:12]
        cid = self._ensure_conversation(conversation_id, user_text)
        tracer = Tracer(self.db, self.clock, turn_id, sink)
        tracer.emit("question", text=user_text, conversation_id=cid)
        history, focus = self._history(cid)
        self._save(cid, "user", {"text": user_text}, turn_id)

        ctx = ToolContext(self.db, self.clock, turn_id)
        now = self.clock.now()
        sys_prompt = prompts.load("system")
        instructions = sys_prompt.render(now=now.strftime("%Y-%m-%d %H:%M"), weekday=now.strftime("%A"))
        cal = calendar_context.build(self.db, now)
        instructions += "\n\n" + calendar_context.render(cal)
        if focus:
            instructions += f"\nRecently discussed in this conversation: {', '.join(focus)}."
        tools = registry.function_schemas() + [respond_tool_schema()]

        tool_outputs: list[Any] = [cal]  # computed calendar facts count as grounded facts
        tool_log: list[dict[str, Any]] = []
        tool_results: list[tuple[str, dict[str, Any]]] = []
        next_input: list[dict[str, Any]] = history + [{"role": "user", "content": user_text}]
        prev_id: str | None = None
        tool_choice: Any = "required"
        state = {"llm_calls": 0, "cost": 0.0, "rejections": 0, "repairs": 0, "revisions": 0, "tool_steps": 0}
        final: RespondArgs | None = None
        critique: dict[str, Any] | None = None
        fail_reason = "the step limit was reached"

        def llm_call(purpose: str, **kwargs):
            budget.check(self.db, self.daily_budget)
            resp = self.llm.create(**kwargs)
            rec = budget.record(self.db, resp.model, purpose, turn_id, resp.usage, resp.latency_ms)
            state["llm_calls"] += 1
            state["cost"] += rec["cost_usd"]
            tracer.emit("llm", **rec, prompt=(sys_prompt if purpose == "agent" else prompts.load("critic")).tag)
            return resp

        for _ in range(MAX_TOOL_STEPS + MAX_REPAIRS + 2):
            resp = llm_call("agent", instructions=instructions, input=next_input, tools=tools,
                            tool_choice=tool_choice, previous_response_id=prev_id)
            prev_id = resp.id
            names = [c.name for c in resp.calls]
            if resp.reasoning_summary:
                summary = " ".join(" ".join(resp.reasoning_summary).replace("**", "").split())
                tracer.emit("plan", message=summary[:240] + ("…" if len(summary) > 240 else "") +
                            (f" → call {' + '.join(names)}" if names else ""), calls=names, reasoning=summary)
            else:
                tracer.emit("plan", message=("call " + " + ".join(names)) if names else "no tool call", calls=names)
            outputs: list[dict[str, Any]] = []

            if not resp.calls:  # the model answered in plain text despite tool_choice=required
                next_input = [{"role": "user", "content": "Use the respond function to give the final reply."}]
                tool_choice = {"type": "function", "name": "respond"}
                continue

            work = [c for c in resp.calls if c.name != "respond"]
            if work:
                state["tool_steps"] += 1
            for c in work:
                try:
                    args = json.loads(c.arguments or "{}")
                except json.JSONDecodeError:
                    args = {"_unparseable": c.arguments}
                res, ms = registry.call(ctx, c.name, args if isinstance(args, dict) else {})
                dump = res.model_dump(mode="json")
                tool_outputs.append(dump)
                tool_results.append((c.name, dump))
                entry = {"tool": c.name, "args": args, "ok": res.ok, "ms": round(ms, 1),
                         "error": res.error.code.value if res.error else None, "summary": summarize_result(res),
                         "evidence": [e.id for e in res.evidence]}
                tool_log.append(entry)
                tracer.emit("action", **{k: entry[k] for k in ("tool", "args", "ok", "summary", "evidence", "ms")},
                            error_code=entry["error"])
                text = json.dumps(dump, ensure_ascii=False)
                if len(text) > MAX_OUTPUT_CHARS:
                    text = text[:MAX_OUTPUT_CHARS] + ' …"[truncated: narrow the query for full detail]"'
                outputs.append({"type": "function_call_output", "call_id": c.call_id, "output": text})

            for c in (x for x in resp.calls if x.name == "respond"):
                if work:
                    outputs.append({"type": "function_call_output", "call_id": c.call_id,
                                    "output": "IGNORED: call respond alone, after reading the tool results."})
                    continue
                try:
                    draft = parse_respond(c.arguments)
                except (ValidationError, json.JSONDecodeError) as e:
                    state["rejections"] += 1
                    tracer.emit("verifier", ok=False, message="respond arguments invalid", violations=[str(e)[:400]])
                    outputs.append({"type": "function_call_output", "call_id": c.call_id,
                                    "output": f"INVALID respond arguments: {str(e)[:600]}"})
                    continue
                tracer.emit("draft", message=f'{draft.kind}: "{draft.headline[:200]}"', kind=draft.kind,
                            headline=draft.headline)
                # A status lookup made while handling an action request (reject / propose) must not replace that
                # answer with a status report (red-team R05/R06: "email the customer", "change the due date").
                status_reply = (order_status.render(tool_results, user_text, now.date())
                                if draft.kind not in ACTION_KINDS else None)
                if status_reply is not None:
                    draft = status_reply
                    tracer.emit("status_contract", message="Order status constructed from validated tool fields",
                                headline=draft.headline)
                else:
                    rendered = feasibility_view.apply(draft, tool_results)
                    if rendered is not draft:
                        draft = rendered
                        tracer.emit("render", message="Estimate details rendered from the feasibility result")
                v = verify(draft, tool_outputs, user_text, now, set(ctx.evidence.issued), self.db, turn_id)
                tracer.emit("verifier", ok=v.ok, checked=v.checked_tokens, violations=v.violations,
                            message=(f"{v.checked_tokens} factual tokens grounded" if v.ok else
                                     "; ".join(v.violations)[:400]))
                if not v.ok:
                    state["rejections"] += 1
                    if state["repairs"] < MAX_REPAIRS:
                        state["repairs"] += 1
                        tracer.emit("repair",
                                    message=f"verifier rejection sent back ({state['repairs']}/{MAX_REPAIRS})")
                        outputs.append({"type": "function_call_output", "call_id": c.call_id,
                                        "output": prompts.load("repair").render(
                                            violations="\n".join(f"- {x}" for x in v.violations))})
                    else:
                        fail_reason = "the reply still had unsupported figures after one repair: " + \
                                      "; ".join(v.violations)[:300]
                        final = None
                        outputs = []
                        break
                    continue
                if self.critic_enabled and state["revisions"] == 0:
                    cr = critic_mod.review(_CriticLLM(llm_call), user_text, draft, tool_outputs)
                    critique = {"verdict": cr.verdict, "issues": cr.issues}
                    tracer.emit("critic", message=f"{cr.verdict}: {'; '.join(cr.issues)}"[:400], **critique)
                    if cr.verdict == "revise" and cr.issues:
                        state["revisions"] += 1
                        tracer.emit("repair", message="critic asked for a revision (1/1)")
                        outputs.append({"type": "function_call_output", "call_id": c.call_id,
                                        "output": "REVISE requested by the reviewer before sending:\n" +
                                                  "\n".join(f"- {x}" for x in cr.issues) +
                                                  "\nFix these, keeping every figure from the tool results, then "
                                                  "call respond again."})
                        continue
                final = draft
                break

            if final is not None or (not outputs and state["rejections"] > MAX_REPAIRS):
                break
            next_input = outputs
            tool_choice = {"type": "function", "name": "respond"} if state["tool_steps"] >= MAX_TOOL_STEPS \
                else "required"

        if final is None:
            status_reply = order_status.render(tool_results, user_text, now.date())
            if status_reply is not None:
                verdict = verify(status_reply, tool_outputs, user_text, now, set(ctx.evidence.issued), self.db, turn_id)
                if verdict.ok:
                    final = status_reply
                    tracer.emit("status_contract", message="Verified status available despite draft failure",
                                headline=final.headline)
        reply = self._finish(cid, turn_id, final, critique, tool_log, state, fail_reason, t0, tracer)
        return reply

    # ----------------------------------------------------------------- assemble and persist the reply
    def _finish(self, cid, turn_id, final, critique, tool_log, state, fail_reason, t0, tracer) -> Reply:
        if final is not None:
            proposals = []
            for pid in final.proposal_ids:
                r = self.db.execute("SELECT action_id, kind, preview, status FROM pending_actions WHERE action_id = ?",
                                    (pid,)).fetchone()
                if r:
                    proposals.append(dict(r))
            reply = Reply(turn_id=turn_id, conversation_id=cid, kind=final.kind, headline=final.headline,
                          details=final.details, evidence_ids=final.evidence_ids,
                          clarification_question=final.clarification_question, options=final.options,
                          proposals=proposals, followups=final.followups, grounded=True)
        else:
            headline, details = fallback.render(tool_log, fail_reason)
            ev = sorted({e for t in tool_log for e in t["evidence"]}, key=lambda x: int(x[1:]))
            reply = Reply(turn_id=turn_id, conversation_id=cid, kind="fallback", headline=headline, details=details,
                          evidence_ids=ev, grounded=True)
            tracer.emit("fallback", message=fail_reason[:300])
        reply.verifier_rejections = state["rejections"]
        reply.critic = critique
        reply.llm_calls = state["llm_calls"]
        reply.cost_usd = round(state["cost"], 6)
        reply.latency_s = round(time.perf_counter() - t0, 2)
        reply.tool_calls = tool_log
        tracer.emit("reply", message=f"{reply.kind} · {reply.llm_calls} LLM calls · ${reply.cost_usd:.5f} · "
                                     f"{reply.latency_s} s · {len(tool_log)} tool calls · "
                                     f"{reply.verifier_rejections} rejected drafts",
                    kind=reply.kind, headline=reply.headline, cost_usd=reply.cost_usd, latency_s=reply.latency_s)
        self._save(cid, "assistant", reply.model_dump(mode="json", exclude={"tool_calls"}), turn_id)
        return reply


class _CriticLLM:
    """Routes the critic's call through the agent's budget check, usage record and trace."""

    def __init__(self, llm_call):
        self._call = llm_call
        self.model = "critic"

    def create(self, **kwargs):
        return self._call("critic", **kwargs)
