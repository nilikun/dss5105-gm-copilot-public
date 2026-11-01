"""Formal paired evaluation. Refuses release before human calibration and an immutable freeze.

This is a separate runner from legacy eval/run.py. Hidden files stay outside the
checkout. Results remain private until the custodian approves their publication.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from frozen_protocol import ROOT, load_released, require
from independent_scoring import combine, hard_score
from judge import evaluate


def schedule(items, repetitions, seed):
    plan = [
        (item, repetition, version)
        for item in items
        for repetition in range(1, repetitions + 1)
        for version in ("baseline", "improved")
    ]
    random.Random(seed).shuffle(plan)
    return plan


def cost(calls, rates):
    known = [c["usage"] for c in calls if c.get("usage") is not None]
    return sum(
        (
            (u["input_tokens"] - u["cached_input_tokens"]) * rates["input_per_million"]
            + u["cached_input_tokens"] * rates["cached_input_per_million"]
            + u["output_tokens"] * rates["output_per_million"]
        )
        / 1e6
        for u in known
    )


def metrics(rows, planned):
    result = {"planned": planned, "attempted": len(rows), "unattempted": planned - len(rows)}
    for version in ("baseline", "improved"):
        items = [r for r in rows if r["version"] == version]
        latencies = sorted(r["wall_seconds"] for r in items)
        calls = [c for r in items for c in r["api_calls"]] + [r["judge_call"] for r in items if r.get("judge_call")]
        known = [c["usage"] for c in calls if c.get("usage") is not None]
        scored = [r["score"] for r in items if r.get("score")]
        result[version] = {
            "planned": planned // 2,
            "attempted": len(items),
            "passed": sum(r.get("pass", False) for r in items),
            "errors": sum(r.get("error") is not None for r in items),
            "correctness_count": sum(s["correctness"] for s in scored),
            "mean_completeness_attempted": sum(s["completeness"] or 0 for s in scored) / len(items) if items else None,
            "behavior_correct_count": sum(s["behavior"] for s in scored),
            "unsupported_claim_answers": sum(s["unsupported_claims"] is True for s in scored),
            "unsupported_unscored": len(items) - sum(s["unsupported_claims"] is not None for s in scored),
            "p50_seconds": statistics.median(latencies) if latencies else None,
            "p90_seconds": latencies[round(0.9 * (len(latencies) - 1))] if latencies else None,
            "api_attempts": len(calls),
            "unknown_usage_calls": sum(c.get("usage") is None for c in calls),
            "reported_usage": {
                key: sum(u.get(key) or 0 for u in known)
                for key in ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_tokens")
            },
            "by_category": {
                category: {
                    "attempted": sum(r["category"] == category for r in items),
                    "passed": sum(r["category"] == category and r.get("pass", False) for r in items),
                }
                for category in sorted({r["category"] for r in items})
            },
            "clarification_refusal": {
                behavior: {
                    "attempted": sum(r["expected_behavior"] == behavior for r in items),
                    "appropriate": sum(
                        r["expected_behavior"] == behavior and bool(r.get("score", {}).get("behavior")) for r in items
                    ),
                }
                for behavior in ("clarify", "refuse")
            },
        }
    result["uncertainty"] = (
        f"{len({r['id'] for r in rows})} distinct attempted questions; "
        "repetitions are correlated, not independent samples."
    )
    # Paired cluster bootstrap resamples question IDs, keeping repetitions together.
    ids = sorted({r["id"] for r in rows})
    if len(ids) >= 2 and len(rows) == planned:
        averages = {
            v: {
                qid: statistics.mean(int(r.get("pass", False)) for r in rows if r["version"] == v and r["id"] == qid)
                for qid in ids
            }
            for v in ("baseline", "improved")
        }
        rng = random.Random(5105)
        deltas = sorted(
            statistics.mean(averages["improved"][i] - averages["baseline"][i] for i in rng.choices(ids, k=len(ids)))
            for _ in range(2000)
        )
        result["paired_pass_delta_95pct_cluster_bootstrap"] = [deltas[49], deltas[1949]]
    else:
        result["paired_pass_delta_95pct_cluster_bootstrap"] = None
    return result


def read_call_journal(path):
    latest = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            latest[event["call_index"]] = event
    return list(latest.values())


def execute(manifest, package, roots, out, api_key):
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    plan = schedule(
        package["items"],
        manifest["execution"]["repetitions_per_item_per_version"],
        manifest["execution"]["randomization_seed"],
    )
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (out / "schedule.json").write_text(
        json.dumps([{"id": i["id"], "repeat": r, "version": v} for i, r, v in plan], indent=2)
    )
    results, spent = [], 0.0
    execution = manifest["execution"]
    for index, (item, repeat, version) in enumerate(plan):
        if spent >= execution["budget_usd"]:
            break  # unattempted rows stay in the planned denominator and schedule
        prefix = out / f"{index:03d}-{version}-{item['id']}-{repeat}"
        request, answer = prefix.with_suffix(".request.json"), prefix.with_suffix(".answer.json")
        payload = {
            "item": item,
            "clock": package["as_of"],
            "settings": manifest["agent_settings"],
            "timeout_seconds": execution["timeout_seconds"],
            "max_api_calls": execution["max_api_calls_per_attempt"],
        }
        request.write_text(json.dumps(payload))
        start = time.perf_counter()
        try:
            process = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "eval/frozen_worker.py"),
                    "--backend",
                    str(roots[version] / "backend"),
                    "--request",
                    str(request),
                    "--output",
                    str(answer),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=execution["timeout_seconds"],
            )
            if process.returncode or not answer.exists():
                raise RuntimeError("Worker failed; " + process.stderr.replace(api_key, "[redacted]")[-1500:])
            row = json.loads(answer.read_text(encoding="utf-8"))
        except Exception as exc:
            callfile = answer.with_suffix(".calls.jsonl")
            row = {
                "reply": {},
                "api_calls": read_call_journal(callfile),
                "error": {"type": type(exc).__name__, "message": str(exc).replace(api_key, "[redacted]")[:1500]},
                "unconfirmed_actions": 0,
            }
        row.update(
            id=item["id"],
            repeat=repeat,
            version=version,
            category=item["category"],
            expected_behavior=item["expected_behavior"],
            wall_seconds=time.perf_counter() - start,
            score=None,
            judge_call=None,
            **{"pass": False},
        )
        if row["reply"] and not row["error"]:
            hard = hard_score(item, row["reply"], package["as_of"])
            if row["unconfirmed_actions"]:
                hard["pass"] = False
                hard["unconfirmed_actions"] = row["unconfirmed_actions"]
            settings = manifest["judge_settings"]
            judgment = evaluate(
                item,
                row["reply"],
                api_key=api_key,
                model=settings["model"],
                effort=settings["reasoning_effort"],
                max_output_tokens=settings["max_output_tokens"],
                timeout=settings["timeout_seconds"],
            )
            row["judge_call"] = judgment
            row["score"] = combine(hard, judgment)
            row["pass"] = row["score"]["pass"]
        spent += cost(row["api_calls"], manifest["pricing"]["agent"])
        if row["judge_call"]:
            spent += cost([row["judge_call"]], manifest["pricing"]["judge"])
        results.append(row)
        with (out / "results.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row) + "\n")
        print(index + 1, "/", len(plan), version, item["id"], "PASS" if row["pass"] else "FAIL", flush=True)
        # Unknown billing or API failures halt; never repeatedly charge for an invalid configuration.
        if (
            any(c.get("usage") is None for c in row["api_calls"])
            or (row["judge_call"] and row["judge_call"]["usage"] is None)
            or row["error"]
        ):
            break
    summary = metrics(results, len(plan))
    summary.update(
        scope=manifest.get("scope", "frozen held-out comparison"),
        cost_estimate_usd=spent,
        cost_note="Frozen-rate estimate, not a bill; unknown usage is not zero. Soft cap checked between items.",
        completed_utc=datetime.now(UTC).isoformat(),
    )
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    report = [
        "# " + manifest.get("scope", "Frozen held-out comparison"),
        "",
        f"Attempted {len(results)} of {len(plan)} planned attempts.",
        "",
        "| Version | Passes / planned | Errors | Unsupported / unscored | p50 / p90 seconds |",
        "|---|---:|---:|---:|---:|",
    ]
    for v in ("baseline", "improved"):
        m = summary[v]
        report.append(
            f"| {v} | {m['passed']} / {m['planned']} | {m['errors']} | "
            f"{m['unsupported_claim_answers']} / {m['unsupported_unscored']} | "
            f"{m['p50_seconds']} / {m['p90_seconds']} |"
        )
    report += [
        "",
        summary["uncertainty"],
        "",
        "All raw results, failures, traces, context turns and usage are retained.",
        "See summary.json for per-category metrics and the paired question-level bootstrap interval.",
        "",
        "## Failures",
        "",
    ]
    for r in results:
        if not r["pass"]:
            report.append(
                f"- {r['version']} {r['id']} repetition {r['repeat']}: "
                + (r["reply"].get("headline", "") or str(r["error"]))
            )
    (out / "REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("freeze", "baseline", "improved", "output-dir"):
        parser.add_argument("--" + key, type=Path, required=True)
    args = parser.parse_args()
    require(not args.output_dir.resolve().is_relative_to(ROOT), "Formal results must stay outside development checkout")
    manifest, package = load_released(args.freeze, args.baseline, args.improved)
    from dotenv import load_dotenv

    load_dotenv(ROOT / "backend/.env")
    load_dotenv(ROOT / "backend/.env.team")
    key = os.environ.get("OPENAI_API_KEY")
    require(bool(key), "API key missing")
    execute(manifest, package, {"baseline": args.baseline, "improved": args.improved}, args.output_dir, key)


if __name__ == "__main__":
    main()
