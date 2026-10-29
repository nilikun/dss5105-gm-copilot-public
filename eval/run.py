"""Run an evaluation set through the agent and score it (docs/EVAL_PLAN.md §4).

    uv run --project backend python eval/run.py --set dev                 # critic off (default system)
    uv run --project backend python eval/run.py --set dev --critic        # ablation: + LLM critic
    uv run --project backend python eval/run.py --set dev --only D10,D29  # a few items while debugging

Each item gets a fresh in-memory database and the clock at the dataset's "today" (2026-04-01 07:00), so items
cannot affect each other. `context_turns` are sent first in the same conversation. Nothing is ever confirmed:
any executed action in the audit log counts as an unconfirmed side effect.

Writes eval/results/<run-id>/: results.jsonl (one line per item: reply, tool calls, scores), summary.json and
summary.md (decision accuracy, faithfulness, behaviour confusion, per category, latency, cost, failures).
The held-out file is read only when --set heldout is given (the one frozen run).
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "eval"))

from scoring import KIND_FOR, reply_text, score  # noqa: E402

from app.agent.prompts import load as load_prompt  # noqa: E402
from app.agent.runtime import Agent  # noqa: E402
from app.clock import SimClock  # noqa: E402
from app.config import DATASET_TODAY  # noqa: E402
from app.db.database import connect  # noqa: E402
from app.llm.openai_responses import OpenAIResponsesClient  # noqa: E402

SPEND = {"usd": 0.0}
SPEND_LOCK = threading.Lock()

SETS = {"dev": ROOT / "eval" / "questions_dev.yaml", "redteam": ROOT / "eval" / "redteam.yaml",
        "heldout": ROOT / "eval" / "questions_heldout.yaml"}


def run_item(item: dict, llm, critic: bool, max_cost: float) -> dict | None:
    with SPEND_LOCK:
        if SPEND["usd"] > max_cost:
            return None
    db, clock = connect(), SimClock.at(DATASET_TODAY)
    agent = Agent(db, clock, llm, critic_enabled=critic)
    cid, context_cost = None, 0.0
    for turn in item.get("context_turns", []):
        r = agent.run(turn["user"], cid)
        cid, context_cost = r.conversation_id, context_cost + r.cost_usd
    t0 = time.perf_counter()
    try:
        reply = agent.run(item["question"], cid).model_dump()
        error = None
    except Exception as e:  # a crash is a failed item, not a failed run
        reply, error = {"kind": "error", "headline": "", "grounded": False, "cost_usd": 0.0}, repr(e)
    wall = time.perf_counter() - t0
    executed = db.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
    with SPEND_LOCK:
        SPEND["usd"] += reply.get("cost_usd", 0.0) + context_cost
    return scored({
        "id": item["id"], "category": item["category"], "question": item["question"], "got": reply.get("kind"),
        "unconfirmed_executions": executed,
        "verifier_rejections": reply.get("verifier_rejections", 0), "critic": reply.get("critic"),
        "latency_s": round(wall, 2), "cost_usd": round(reply.get("cost_usd", 0.0) + context_cost, 6),
        "llm_calls": reply.get("llm_calls", 0), "tools": [t.get("tool") for t in reply.get("tool_calls", [])],
        "headline_lines": len([x for x in (reply.get("headline") or "").splitlines() if x.strip()]),
        "error": error, "reply": reply,
    }, item)


def scored(row: dict, item: dict) -> dict:
    """Attach the scores for `item` to a result row (also used to re-score stored replies)."""
    s = score(item, row["reply"])
    return {**row, "expected": KIND_FOR[item["expected_behavior"]], "decision_ok": s.decision_ok,
            "behavior_ok": s.behavior_ok, "facts_ok": s.facts_ok, "forbidden_ok": s.forbidden_ok,
            "faithful": s.faithful, "missing": s.missing, "forbidden_hits": s.forbidden_hits,
            "text": reply_text(row["reply"])}


def rescore(run_dir: Path) -> None:
    """Re-score a stored run with the current scorer and item file, without calling the model again, so that a
    scorer or label correction applies to every run alike. The first summary is kept as summary.original.json."""
    meta = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    items = {i["id"]: i for i in yaml.safe_load(SETS[meta["set"]].read_text(encoding="utf-8"))["items"]}
    rows = [json.loads(line) for line in (run_dir / "results.jsonl").read_text(encoding="utf-8").splitlines()]
    rows = [scored(r, items[r["id"]]) for r in rows]
    original = run_dir / "summary.original.json"
    if not original.exists():
        original.write_text((run_dir / "summary.json").read_text(encoding="utf-8"), encoding="utf-8")
    keep = ("run_id", "set", "model", "reasoning_effort", "critic", "prompt_version", "commit", "date", "workers")
    meta = {k: meta[k] for k in keep if k in meta} | {"rescored": datetime.now().isoformat(" ", "seconds")}
    with open(run_dir / "results.jsonl", "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
    summary, md = summarise(rows, meta)
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (run_dir / "summary.md").write_text(md, encoding="utf-8")
    print(f"{run_dir.name}: decision {summary['decision_accuracy']:.1%} · faithful {summary['faithfulness']:.1%}")


def pct(n: int, d: int) -> str:
    return f"{100 * n / d:.1f}%" if d else "—"


def summarise(rows: list[dict], meta: dict) -> tuple[dict, str]:
    n = len(rows)
    lat = sorted(r["latency_s"] for r in rows)
    p = lambda q: lat[min(n - 1, int(round(q * (n - 1))))] if n else 0.0  # noqa: E731
    cats = defaultdict(list)
    for r in rows:
        cats[r["category"]].append(r)
    confusion = Counter((r["expected"], r["got"]) for r in rows)
    summary = {
        **meta, "n": n,
        "decision_accuracy": sum(r["decision_ok"] for r in rows) / n,
        "behavior_accuracy": sum(r["behavior_ok"] for r in rows) / n,
        "faithfulness": sum(r["faithful"] for r in rows) / n,
        "unconfirmed_side_effects": sum(r["unconfirmed_executions"] for r in rows),
        "headline_le_3_lines": sum(r["headline_lines"] <= 3 for r in rows) / n,
        "verifier_rejections": sum(r["verifier_rejections"] for r in rows),
        "latency_p50_s": statistics.median(lat) if lat else 0.0, "latency_p90_s": p(0.9),
        "cost_total_usd": round(sum(r["cost_usd"] for r in rows), 5),
        "cost_per_item_usd": round(sum(r["cost_usd"] for r in rows) / n, 5) if n else 0.0,
        "per_category": {c: {"n": len(v), "decision_ok": sum(r["decision_ok"] for r in v)} for c, v in cats.items()},
        "confusion": {f"{e}->{g}": k for (e, g), k in sorted(confusion.items())},
        "failures": [r["id"] for r in rows if not (r["decision_ok"] and r["faithful"])],
    }
    ok = sum(r["decision_ok"] for r in rows)
    md = [f"# Evaluation run `{meta['run_id']}`", "",
          f"Set **{meta['set']}** · model `{meta['model']}` · reasoning {meta['reasoning_effort']} · critic "
          f"**{'on' if meta['critic'] else 'off'}** · prompt system v{meta['prompt_version']} · commit "
          f"`{meta['commit']}` · {meta['date']}"
          + (f" · re-scored {meta['rescored']} with the current scorer" if meta.get("rescored") else ""), "",
          "| Metric | Value |", "|---|---|",
          f"| Decision accuracy | **{pct(ok, n)}** ({ok}/{n}) |",
          f"| Behaviour accuracy | {pct(sum(r['behavior_ok'] for r in rows), n)} |",
          f"| Faithfulness (reply passed the verifier) | {pct(sum(r['faithful'] for r in rows), n)} |",
          f"| Unconfirmed side effects | {summary['unconfirmed_side_effects']} |",
          f"| Headline ≤ 3 lines | {pct(sum(r['headline_lines'] <= 3 for r in rows), n)} |",
          f"| Verifier rejections (repaired) | {summary['verifier_rejections']} |",
          f"| Latency p50 / p90 | {summary['latency_p50_s']:.1f} s / {summary['latency_p90_s']:.1f} s |",
          f"| Cost total / per item | ${summary['cost_total_usd']:.4f} / ${summary['cost_per_item_usd']:.4f} |", "",
          "## Per category", "", "| Category | n | Decision |", "|---|---|---|"]
    for c, v in summary["per_category"].items():
        md.append(f"| {c} | {v['n']} | {pct(v['decision_ok'], v['n'])} |")
    md += ["", "## Behaviour (expected → got)", "", "| Expected | Got | n |", "|---|---|---|"]
    md += [f"| {e} | {g} | {k} |" for (e, g), k in sorted(confusion.items())]
    md += ["", "## Items", "", "| ID | Category | Expected | Got | Decision | Faithful | Missing / forbidden | s |",
           "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        note = "; ".join([f"missing: {m}" for m in r["missing"]] + [f"said: {h}" for h in r["forbidden_hits"]]
                         + ([f"error: {r['error']}"] if r["error"] else []))
        tick = lambda b: "✓" if b else "✗"  # noqa: E731
        md.append(f"| {r['id']} | {r['category']} | {r['expected']} | {r['got']} | {tick(r['decision_ok'])} | "
                  f"{tick(r['faithful'])} | {note} | {r['latency_s']} |")
    return summary, "\n".join(md) + "\n"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows consoles default to a legacy code page
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=SETS, default="dev")
    ap.add_argument("--critic", action="store_true")
    ap.add_argument("--model", default=None)
    ap.add_argument("--only", default=None, help="comma-separated item ids")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--tag", default="", help="suffix for the run id (e.g. r1, r2 for repeated runs)")
    ap.add_argument("--max-cost", type=float, default=0.60, help="stop submitting items beyond this spend (USD)")
    ap.add_argument("--rescore", nargs="+", type=Path, help="re-score stored run directories instead of running")
    a = ap.parse_args()
    if a.rescore:
        for d in a.rescore:
            rescore(d)
        return

    items = yaml.safe_load(SETS[a.set].read_text(encoding="utf-8"))["items"]
    items = [i for i in items if not i.get("void")]
    if a.only:
        keep = set(a.only.split(","))
        items = [i for i in items if i["id"] in keep]
    llm = OpenAIResponsesClient(model=a.model)
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                            cwd=ROOT).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no", "backend", "eval"],
                           capture_output=True, text=True, cwd=ROOT).stdout.strip()
    commit += "-dirty" if dirty else ""  # uncommitted code or prompt changes are part of what was measured
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    run_id = (f"{stamp}-{a.set}-{llm.model}-{'critic' if a.critic else 'base'}" + ("-partial" if a.only else "")
              + (f"-{a.tag}" if a.tag else ""))
    meta = {"run_id": run_id, "set": a.set, "model": llm.model, "reasoning_effort": llm.effort, "critic": a.critic,
            "prompt_version": load_prompt("system").version, "commit": commit,
            "date": datetime.now().isoformat(" ", "seconds"), "workers": a.workers}
    out = ROOT / "eval" / "results" / run_id
    out.mkdir(parents=True, exist_ok=True)

    rows = []
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        futures = {i["id"]: pool.submit(run_item, i, llm, a.critic, a.max_cost) for i in items}
        for iid, f in futures.items():
            r = f.result()
            if r is None:
                print(f"- {iid:4} skipped: cost cap ${a.max_cost} reached")
                continue
            rows.append(r)
            mark = "✓" if r["decision_ok"] and r["faithful"] else "✗"
            print(f"{mark} {iid:4} {r['expected']:9} → {r['got']:9} {r['latency_s']:5.1f}s ${r['cost_usd']:.4f}  "
                  f"{'; '.join(r['missing'] + r['forbidden_hits'])}", flush=True)

    with open(out / "results.jsonl", "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
    summary, md = summarise(rows, meta)
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out / "summary.md").write_text(md, encoding="utf-8")
    print(f"\ndecision {summary['decision_accuracy']:.1%} · faithful {summary['faithfulness']:.1%} · "
          f"p50 {summary['latency_p50_s']:.1f}s · ${summary['cost_total_usd']:.4f} → {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
