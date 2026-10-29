# GM Co-Pilot

An AI co-pilot for the general manager of a quick-response knitwear factory. It gives a morning briefing,
answers questions over the production data all day, keeps standing watches and raises alerts, estimates whether
a new order is feasible, and drafts actions (chase-ups, notes, reminders) that run only after the manager
confirms them. **Tools compute, the model narrates**: every number in a reply is checked against the tool outputs
of that turn and links back to the source rows.

NUS DSS5105 Capstone, Track 1 — **Group 23**: CAI Ruixin · HE Wenxin · IAO Ngan Chun · LIU Boxuan · NI Likun ·
ZENG Zihao

![Architecture](docs/figures/fig1_architecture.png)

## Public Demo — Sprint 2

**[Open GM Co-Pilot](https://35.213.154.170)** ·
[Source code](https://github.com/nilikun/dss5105-gm-copilot-public)

1. Open the Demo and enter the access code in **Settings**. The team shares the code privately with graders
   and invited users; no credentials are published here.
2. Ask **"What is the status of order ORD-120? Cite your evidence."**
3. Expand **Show thinking** to see streamed steps, then open an evidence reference to inspect its source.

FastAPI, the built React app, SQLite and the Watch Engine run on a Google Cloud VM; no local installation is
needed. All visitors share one factory state and clock. The initial **As things stand** scenario starts at
**1 Apr 2026, 07:00** in simulation mode: watches run when the simulated clock advances. Coordinate changes
and resets with the team.

Public HTTPS, real Q&A, Watch execution and restart persistence were verified on **27 Oct 2026 (UTC+8)**.
The VM uses time-limited trial credit; this is not a permanently free hosting guarantee.
See [deployment and operations](docs/DEPLOY.md) for the reproducible Google Cloud setup and its limits.

## What it does

| Capability | How |
|---|---|
| Answer anything, any time | ReAct loop over 19 typed tools (retrieval, judgement, tracing, discovery, feasibility, actions); a code verifier rejects any number, date or id not in this turn's tool outputs; one repair, then a raw-data fallback |
| "Is that normal?" | Robust z-score against the trailing 20 working days; thresholds chosen by backtest ([analysis](analysis/results/threshold_backtest.md)) |
| Morning briefing | Built by code at 07:00 (yesterday, at risk, decisions today); the optional written summary is checked against the structured briefing |
| Watches and alerts | "Tell me if ORD-120 hasn't moved by Friday" becomes a typed watch evaluated on every clock tick; P1/P2 alerts with a daily interrupt cap |
| Feasibility | In-house P50/P80 from a log-linear size model ([backtest](analysis/results/projection_backtest.md)) plus every outside workshop's finish date, cost and defect rate |
| Actions | The model can only propose; the manager confirms in the UI; every execution is audited and can be undone; messages go to an outbox |
| Observability | Every step (plan, tool call, draft, verifier verdict, cost, latency) is traced to the console, a JSONL log and the "Thinking logs" page |

## Results (development set; held-out results follow in Sprint 3)

| Metric | Value |
|---|---|
| Decision accuracy, dev set (36 items; tuned on, held-out follows) | 97–100% |
| Replies that passed the grounding verifier | 100% |
| Red-team action-safety prompts (12) | 12/12, **0** actions executed without confirmation |
| Median latency / cost | 6.7 s / ≈ $0.75 per 1,000 questions (`gpt-5.6-luna`) |
| LLM critic ablation | +1.4 points for 63% more cost and doubled p90 latency → off by default |

Details, every reply and all corrections: [eval/results](eval/results/README.md). Method: [EVAL_PLAN](docs/EVAL_PLAN.md).

## Run it

Prerequisites: Python ≥ 3.11 with [uv](https://docs.astral.sh/uv/), Node ≥ 20, an OpenAI API key.

```bash
cp backend/.env.example backend/.env        # put your key in it; the file is git-ignored
cd frontend && npm install && npm run build && cd ..
cd backend && uv sync && uv run uvicorn app.main:app --port 8000
# open http://127.0.0.1:8000 — the clock starts at Wed 1 Apr 2026 07:00 (the dataset's "today")
```

For the hosted Demo, follow [Google Cloud deployment](docs/DEPLOY.md). For a separate local container:

```bash
cp deploy/deploy.env.example deploy/deploy.env   # set a private ACCESS_CODE; TRUST_PROXY=false without a proxy
docker compose up -d --build                     # http://localhost:8000
```

Tests and evaluation:

```bash
cd backend && uv sync && uv run pytest -q && uv run ruff check . ../eval
cd .. && uv run --project backend python -m pytest -q eval/tests    # evaluation contracts and fixtures
uv run --project backend python eval/run.py --set dev                # ≈ $0.03 of model calls
uv run --project backend python eval/run.py --set redteam
```

## Repository

| Path | Contents |
|---|---|
| `backend/app/tools/` | The 19 tools, one folder per family; each has Pydantic models and a test against an independent pandas computation |
| `backend/app/agent/` | ReAct runtime, `respond` contract, grounding verifier, optional critic, fallback |
| `backend/prompts/` | Every prompt, versioned |
| `backend/app/workflows/` | Briefing, watch engine, alert policy, scheduler; `app/clock/` simulated and real clock, scenario data advancer |
| `backend/app/actions/` | Confirm / cancel / undo gateway and audit log |
| `frontend/` | React web app: chat with live thinking, evidence drawer, briefing, alerts, actions, watches, logs, settings, voice |
| `data/` | The factory dataset and simulation scenarios |
| `eval/` | Dev and red-team sets, ground-truth script, runner, scorer, results |
| `analysis/` | Backtests behind the alert thresholds and the completion forecast |
| `docs/` | [Deployment and operations](docs/DEPLOY.md), [tool specification](docs/TOOL_SPEC.md), [evaluation plan](docs/EVAL_PLAN.md), figures |
