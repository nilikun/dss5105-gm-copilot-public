# Deploying the demo (Cloudflare Tunnel)

Goal: a working public link for the Sprint 2 first slide (due **Fri 30 Oct, 15:00**) that keeps working through
grading. The app is one container (web app + API, [`Dockerfile`](../Dockerfile)); [`compose.yaml`](../compose.yaml)
runs it next to a Cloudflare Tunnel connector, so the machine needs **no open ports and no public IP**.

```
visitor ──https──▶ Cloudflare edge ──tunnel──▶ cloudflared container ──▶ app container :8000 ──▶ OpenAI
                   (your hostname)              (outbound connection only)    (SQLite on a volume)
```

## 1. Pick the host (decide in the group)

The app runs wherever `docker compose` runs, and the link works only while that machine is on.

| Host | Cost | Notes |
|---|---|---|
| A cloud VM (e.g. an always-free tier VM, or a small VPS) | free – a few $/month | Best for grading: always on. Needs Docker; 1 vCPU / 1 GB RAM is enough |
| A teammate's always-on PC | free | Fine if it really stays on (no sleep, no reboots) until the final grade |

Avoid laptops that sleep. Whoever hosts it keeps the access code and tunnel token private.

## 2. Create the tunnel (Cloudflare dashboard, ~5 min)

Needs access to the Cloudflare account that holds the group's domain (ask the repo owner).

1. Cloudflare dashboard → **Zero Trust** → **Networks → Tunnels** → **Create a tunnel** → type **Cloudflared**,
   name it `gm-copilot`.
2. On the install screen, copy the **token** (the long string after `--token`). Don't run the command shown.
3. Add a public hostname (called *Public Hostname* or *Published application route* depending on the dashboard
   version): subdomain e.g. `gm`, your domain, **Service type `HTTP`, URL `app:8000`** (`app` is the service name
   in `compose.yaml`; the connector reaches it over the compose network).

## 3. Run it on the host

```bash
git clone https://github.com/nilikun/dss5105-gm-copilot.git && cd dss5105-gm-copilot   # private: team key included
# or the public repo (no key): git clone https://github.com/nilikun/dss5105-gm-copilot-public.git, then put OPENAI_API_KEY=… in backend/.env
cp deploy/deploy.env.example deploy/deploy.env
#   edit deploy/deploy.env: ACCESS_CODE=<pick one>, TUNNEL_TOKEN=<token from step 2>, TRUST_PROXY=true
docker compose --profile tunnel up -d --build
docker compose ps                      # app should become "healthy", tunnel "running"
```

The OpenAI key comes from `backend/.env.team` (already in the private repo; from a copy without it, put
`OPENAI_API_KEY=…` in `backend/.env`). Open `https://gm.<your-domain>`,
go to **Settings**, enter the access code, and ask a question.

## 4. Check before you put the link on a slide

- [ ] The link opens on a phone using mobile data (not the host's Wi-Fi).
- [ ] Without the access code the app says "Access code required"; with it, a question gets an answer.
- [ ] "Show thinking" streams step by step (if it only appears at the end, something buffers the stream).
- [ ] `docker compose logs -f app` shows each AI step (`[turn …] · action use tool …`).
- [ ] **Settings → Simulation scenarios → Start** on *As things stand* so graders begin at Wed 1 Apr 07:00.
- [ ] Slide 1 shows the link **and** the access code.

## 5. Operating it

| Task | Command / place |
|---|---|
| Live logs (every AI step) | `docker compose logs -f app` |
| Update to the latest code | `git pull && docker compose --profile tunnel up -d --build` (data is kept) |
| Reset the demo state | Settings page → start a scenario, or `docker compose down -v` (deletes the volume) |
| Spending | Top bar shows today's spend; hard cap **$1/day** (`DAILY_BUDGET_USD`), then chat returns 429 until the next UTC day |
| Abuse | Access code on every request; 20 chat requests per minute per visitor (`RATE_LIMIT_PER_MINUTE`) |
| Stop | `docker compose --profile tunnel down` |

All visitors share one factory state and one simulated clock — someone advancing the clock moves it for everyone.
Agree on who demos when, or reset before a demo.

## Trying it without a Cloudflare account

For a quick test from your own machine: `docker compose up -d --build` (app only, http://localhost:8000), then
install `cloudflared` and run `cloudflared tunnel --url http://localhost:8000`. It prints a temporary
`*.trycloudflare.com` link — fine for showing a teammate, **not** for the slide (it changes on every start and has
no uptime guarantee).

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Cloudflare error 502/1033 | Tunnel up but app not healthy yet, or the hostname's service URL isn't `http://app:8000` |
| "Access code required" on every request | `ACCESS_CODE` in `deploy/deploy.env` differs from what was typed in Settings |
| Chat returns 429 | Daily $1 budget reached, or more than 20 requests/minute from one visitor |
| Everyone shares one rate limit | `TRUST_PROXY` is not `true` |
| "OPENAI_API_KEY is not set" | `backend/.env.team` missing on the host (pull the private repo) |
