# Deploying GM Co-Pilot on Google Cloud

**Sprint 2 Demo: [https://35.213.154.170](https://35.213.154.170)**

Open **Settings**, enter the access code supplied privately by the team, and ask:
**"What is the status of order ORD-120? Cite your evidence."** Expand **Show thinking** and open an evidence
reference. Never publish the access code or an API key in this document, GitHub, slides or screenshots.

This guide records the deployment verified on **27 October 2026 (UTC+8)** and reproduces it on a **new** VM.
For the existing Demo, use [operations](#8-operations-and-updates); do not recreate its resources or reset its data.

## 1. Architecture, resources and cost

```text
Browser -- HTTPS :443 --> Nginx on Google Cloud VM
                            |
                      127.0.0.1:8000
                            |
                  Docker: FastAPI + built React app
                            |              |
                  SQLite named volume   OpenAI API
                            |
                Watch Engine inside the API process
```

| Component | Deployed configuration |
|---|---|
| VM | `gm-copilot`, `asia-southeast1-b` (Singapore), Debian 12 amd64 |
| Compute | `e2-medium`: 2 shared vCPUs, 4 GiB RAM; no GPU |
| Storage | 30 GiB `pd-balanced`, including 2 GiB swap; boot disk auto-delete disabled |
| Network | Custom VPC, IPv4 subnet, reserved external IPv4, **Standard Network Tier** |
| Public entry | Nginx, TCP 80 for ACME/HTTPS redirect and 443 for HTTPS |
| Administration | SSH through Google IAP; no unrestricted public SSH rule |
| Application | Original [Dockerfile](../Dockerfile) and [Compose](../compose.yaml), `app` service only |
| Persistence | `gm-copilot_gm-var` volume at `/app/backend/var`, SQLite `gm.db` in WAL mode |
| Startup | Docker restart policy and systemd; no idle-sleep hosting layer |

Docker builds, frontend compilation, FastAPI and Watch processing all run on the VM. A visitor only needs a
browser. Node is used in the image's build stage; the running application is a Python service serving React assets.

The measured idle host used approximately **572 MiB RAM**, including a **48–70 MiB app container** and about
**163 MiB combined Docker/containerd process RSS**. Disk usage was approximately **6.5 GiB of 30 GiB** and swap
usage was zero. These are deployment observations, not a concurrency benchmark; 1 GiB builds were not validated.

This Singapore configuration **uses trial credit; it is not an Always Free configuration**. At the prices
checked for this deployment, 730 hours/month cost approximately **S$38.57 compute + S$4.22 disk + S$4.67 IPv4
= S$47.45/month**, conservatively counting IPv4 at full price. Allow about S$60/month for planning, subject to
traffic and price changes. This estimate is not an enforced spending limit. See official
[compute](https://cloud.google.com/products/compute/pricing/general-purpose),
[disk](https://cloud.google.com/compute/disks-image-pricing) and
[network/IP](https://cloud.google.com/vpc/network-pricing) pricing before creating resources.

Keep the billing account in **Free Trial** if personal charges must remain zero. Do not activate/upgrade it as
part of deployment. Unupgraded trials stop resources when their credit or time expires; stored data can later
be deleted. Check the account's expiry and export important data beforehand. Trial credit does not pay the
team's separate OpenAI bill. [Google's trial rules](https://docs.cloud.google.com/free/docs/free-cloud-features)

## 2. Provision a new VM

Run this section from an administrative **Bash/Git Bash** terminal with `gcloud` installed and authenticated.
On Windows, configure the Google Cloud SDK on Git Bash's PATH; the examples below are Bash, not PowerShell.
These are provisioning commands, not Docker builds. Replace `YOUR_PROJECT_ID`; do not paste credentials into commands or metadata.
The account needs permission to enable APIs, manage the listed Compute resources, and use IAP/SSH.

Only proceed after confirming trial status and approving the estimated resource costs. If a resource with
these names already exists, inspect it instead of rerunning creation commands.

```bash
export GM_PROJECT="YOUR_PROJECT_ID"
export GM_REGION="asia-southeast1"
export GM_ZONE="asia-southeast1-b"
gcloud auth list
gcloud config set project "$GM_PROJECT"
gcloud services enable compute.googleapis.com iap.googleapis.com

gcloud compute networks create gm-copilot-vpc \
  --subnet-mode=custom --bgp-routing-mode=regional
gcloud compute networks subnets create gm-copilot-singapore \
  --network=gm-copilot-vpc --region="$GM_REGION" --range=10.81.0.0/24
gcloud compute firewall-rules create gm-copilot-iap-ssh \
  --network=gm-copilot-vpc --direction=INGRESS --allow=tcp:22 \
  --source-ranges=35.235.240.0/20 --target-tags=gm-copilot
gcloud compute firewall-rules create gm-copilot-public-web \
  --network=gm-copilot-vpc --direction=INGRESS --allow=tcp:80,tcp:443 \
  --source-ranges=0.0.0.0/0 --target-tags=gm-copilot-web
gcloud compute addresses create gm-copilot-ipv4 \
  --region="$GM_REGION" --network-tier=STANDARD
GM_IP=$(gcloud compute addresses describe gm-copilot-ipv4 \
  --region="$GM_REGION" --format='value(address)')
gcloud compute instances create gm-copilot \
  --zone="$GM_ZONE" --machine-type=e2-medium \
  --image-family=debian-12 --image-project=debian-cloud \
  --boot-disk-size=30GB --boot-disk-type=pd-balanced --no-boot-disk-auto-delete \
  --network=gm-copilot-vpc --subnet=gm-copilot-singapore \
  --address="$GM_IP" --network-tier=STANDARD \
  --tags=gm-copilot,gm-copilot-web \
  --no-service-account --no-scopes --metadata=disable-legacy-endpoints=true

gcloud compute ssh gmdeploy@gm-copilot --zone="$GM_ZONE" --tunnel-through-iap
```

Use the explicit Linux username `gmdeploy`: a Windows username consisting only of digits is not a valid
default Linux account for this setup. Never open TCP 22 to `0.0.0.0/0` to work around an IAP login problem.
No Cloud NAT, load balancer, managed database, paid OS image or domain purchase is required.

## 3. Install the cloud host and obtain the source

**Everything from this section onward runs in the VM's SSH session**, unless explicitly labelled otherwise.
Use a root shell for installation; never run these host setup commands on your workstation:

```bash
sudo -i
set -euo pipefail
umask 077
apt-get update
apt-get install -y ca-certificates curl git nano nginx python3-venv sqlite3
install -d -m 0755 /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
cat > /etc/apt/sources.list.d/docker.sources <<'EOF'
Types: deb
URIs: https://download.docker.com/linux/debian
Suites: bookworm
Components: stable
Architectures: amd64
Signed-By: /etc/apt/keyrings/docker.asc
EOF
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
install -d -m 0755 /etc/docker
if [ ! -e /etc/docker/daemon.json ]; then
  printf '%s\n' '{"log-driver":"json-file","log-opts":{"max-size":"10m","max-file":"3"}}' > /etc/docker/daemon.json
fi
systemctl enable --now docker
systemctl restart docker
python3 -m venv /opt/certbot
/opt/certbot/bin/pip install 'certbot==5.8.0'
install -d -m 0700 /var/backups/gm-copilot
install -d -m 0755 /var/www/acme

if [ ! -e /swapfile ]; then
  fallocate -l 2G /swapfile
  chmod 0600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  printf '/swapfile none swap sw 0 0\n' >> /etc/fstab
fi
printf 'vm.swappiness=10\n' > /etc/sysctl.d/90-gm-copilot.conf
sysctl -p /etc/sysctl.d/90-gm-copilot.conf

git clone https://github.com/nilikun/dss5105-gm-copilot-public.git /opt/gm-copilot
cd /opt/gm-copilot
git rev-parse HEAD
docker --version
docker compose version
```

These instructions use Docker's [official Debian repository](https://docs.docker.com/engine/install/debian/).
Use a Compose version supporting optional `env_file` entries (2.24 or newer; the deployment used 5.6.1).
Record the public source revision when reproducing a release. The original VM was built from an allowlisted
source archive, with credentials transferred separately over IAP; it did not clone private Git history.

If transferring a private checkout instead of cloning the public export, package only approved source files.
Exclude real environment files, `.git`, SSH material, runtime databases, private evaluation data and downloads.
The Docker build already excludes environment files via `.dockerignore`; never add them to `COPY` instructions.

## 4. Configure private credentials and build in the cloud

Create the API environment from the blank template and edit it **privately on the VM**. Use a valid team key
with access to the configured model. The key is never needed in a browser or in the public repository.

```bash
cd /opt/gm-copilot
test -e backend/.env || install -m 0600 backend/.env.example backend/.env
nano backend/.env
python3 - <<'PY'
from pathlib import Path
import secrets

path = Path('deploy/deploy.env')
if not path.exists():
    path.write_text(
        f'ACCESS_CODE={secrets.token_urlsafe(24)}\n'
        'TRUST_PROXY=true\nRATE_LIMIT_PER_MINUTE=20\nDAILY_BUDGET_USD=1.0\n'
    )
path.chmod(0o600)
values = dict(line.split('=', 1) for line in path.read_text().splitlines()
              if '=' in line and not line.lstrip().startswith('#'))
assert len(values.get('ACCESS_CODE', '').strip().strip('"\'')) >= 20, 'Set a strong private access code'
PY
chmod 0600 backend/.env deploy/deploy.env
docker compose -p gm-copilot config --quiet
docker compose -p gm-copilot build
docker compose -p gm-copilot up -d --wait --wait-timeout 180
curl --fail http://127.0.0.1:8000/api/health
```

Read the generated access code in a private editor (`nano deploy/deploy.env`) and share it through a private
channel. Do not print full `docker compose config`, container environments or environment files into logs.
Never commit `backend/.env`, `backend/.env.team` or `deploy/deploy.env`. The optional tunnel profile is unused.
Keep `TRUST_PROXY=true` only with the trusted proxy configuration below; it overwrites the visitor-IP header.

Use the same Compose project name **`gm-copilot`** for every start, update and backup. Changing it creates a
different volume and can make existing data appear missing. The first start seeds a new database; subsequent
starts retain the existing one. Do not run `docker compose down -v` or start/reset a scenario during an update.

## 5. Configure free HTTPS for the fixed IP

Let's Encrypt supports publicly trusted IP certificates using Certbot's webroot flow. They are short-lived
(about 160 hours), so automated renewal is required. Certbot 5.4+ supports this flow; 5.8.0 was verified here.
See the [official IP certificate instructions](https://letsencrypt.org/2026/03/11/shorter-certs-certbot).

First expose only the ACME challenge on HTTP. This initial setup replaces Debian's default Nginx site on the
new dedicated VM; it is not an update procedure for an existing HTTPS service.

```bash
GM_IP=$(curl -fsS -H Metadata-Flavor:Google \
  http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip)
cat > /etc/nginx/sites-available/gm-copilot <<EOF
server {
    listen 80 default_server;
    server_name $GM_IP;
    location /.well-known/acme-challenge/ { root /var/www/acme; default_type text/plain; }
    location / { return 404; }
}
EOF
if [ -L /etc/nginx/sites-enabled/default ]; then unlink /etc/nginx/sites-enabled/default; fi
ln -sfn /etc/nginx/sites-available/gm-copilot /etc/nginx/sites-enabled/gm-copilot
nginx -t
systemctl enable --now nginx
systemctl reload nginx
/opt/certbot/bin/certbot certonly --non-interactive --agree-tos --register-unsafely-without-email \
  --preferred-profile shortlived --webroot --webroot-path /var/www/acme \
  --ip-address "$GM_IP" --cert-name gm-copilot-ip \
  --deploy-hook 'nginx -t && systemctl reload nginx'
```

Install the final proxy configuration. The **trailing `/` on `proxy_pass` is required**: Nginx must pass a
normalized path to the app. The static-file fallback must not receive raw double-slash or traversal paths.
Keep port 8000 bound to loopback. [Nginx URI forwarding rules](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_pass)

```bash
cat > /etc/nginx/sites-available/gm-copilot <<EOF
server {
    listen 80 default_server;
    server_name $GM_IP;
    location /.well-known/acme-challenge/ { root /var/www/acme; default_type text/plain; }
    location / { return 301 https://\$host\$request_uri; }
}
server {
    listen 443 ssl default_server;
    server_name $GM_IP;
    ssl_certificate /etc/letsencrypt/live/gm-copilot-ip/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/gm-copilot-ip/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_session_cache shared:GMSSL:10m;
    client_max_body_size 1m;
    add_header X-Content-Type-Options nosniff always;
    location / {
        proxy_pass http://127.0.0.1:8000/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$remote_addr;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header CF-Connecting-IP \$remote_addr;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_request_buffering off;
        proxy_read_timeout 300s;
    }
}
EOF
nginx -t
systemctl reload nginx
curl --fail "https://$GM_IP/api/health"
```

Disabling proxy buffering allows **Show thinking** SSE events to arrive before the final answer. Replacing
`CF-Connecting-IP` with the socket IP preserves the app's existing per-visitor limiter without trusting a
visitor-supplied header. No Agent, Tools, Verifier or Evaluation changes are needed.

## 6. Enable startup, certificate renewal and SQLite backups

Create the systemd units on the VM. The application service complements Compose's `restart: unless-stopped`;
it waits for a healthy container during boot. The renewal timer checks twice daily, with a small random delay.

```bash
cat > /etc/systemd/system/gm-copilot.service <<'EOF'
[Unit]
Description=GM Co-Pilot Docker Compose application
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target
[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/gm-copilot
ExecStart=/usr/bin/docker compose -p gm-copilot up -d --wait --wait-timeout 180
ExecStop=/usr/bin/docker compose -p gm-copilot stop
TimeoutStartSec=240
[Install]
WantedBy=multi-user.target
EOF
cat > /etc/systemd/system/gm-certbot-renew.service <<'EOF'
[Unit]
Description=Renew GM Co-Pilot IP TLS certificate
After=network-online.target
Wants=network-online.target
[Service]
Type=oneshot
ExecStart=/opt/certbot/bin/certbot renew --quiet
EOF
cat > /etc/systemd/system/gm-certbot-renew.timer <<'EOF'
[Unit]
Description=Check GM Co-Pilot IP certificate twice daily
[Timer]
OnCalendar=*-*-* 00,12:00:00 UTC
RandomizedDelaySec=900
Persistent=true
[Install]
WantedBy=timers.target
EOF
```

Back up SQLite using its online backup API, not a bare copy of an active WAL database. The backup script
checks integrity and creates a new timestamped file without deleting previous backups:

```bash
cat > /usr/local/sbin/gm-copilot-backup <<'SH'
#!/bin/bash
set -euo pipefail
umask 077
mountpoint=$(docker volume inspect gm-copilot_gm-var --format '{{ .Mountpoint }}')
python3 - "$mountpoint/gm.db" <<'PY'
from pathlib import Path
from datetime import datetime, timezone
import sqlite3
import sys

source = Path(sys.argv[1])
assert source.is_file(), 'Database missing; backup aborted'
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
target = Path('/var/backups/gm-copilot') / f'gm-{stamp}.db'
with sqlite3.connect(f'file:{source}?mode=ro', uri=True, timeout=30) as src:
    with sqlite3.connect(target) as dst:
        src.backup(dst)
        assert dst.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
target.chmod(0o600)
print('SQLite backup and integrity check OK:', target.name)
PY
SH
chmod 0750 /usr/local/sbin/gm-copilot-backup
cat > /etc/systemd/system/gm-copilot-backup.service <<'EOF'
[Unit]
Description=Consistent SQLite backup for GM Co-Pilot
Requires=docker.service
After=docker.service gm-copilot.service
[Service]
Type=oneshot
ExecStart=/usr/local/sbin/gm-copilot-backup
EOF
cat > /etc/systemd/system/gm-copilot-backup.timer <<'EOF'
[Unit]
Description=Daily GM Co-Pilot SQLite backup
[Timer]
OnCalendar=*-*-* 02:15:00 UTC
Persistent=true
[Install]
WantedBy=timers.target
EOF
systemctl daemon-reload
systemctl enable --now gm-copilot.service gm-certbot-renew.timer gm-copilot-backup.timer
systemctl start gm-copilot-backup.service
/opt/certbot/bin/certbot renew --dry-run --no-random-sleep-on-renew
systemctl list-timers gm-certbot-renew.timer gm-copilot-backup.timer
```

Backups run daily at **02:15 UTC / 10:15 UTC+8**. They are on the same disk, not an independent disaster
recovery copy. Monitor disk usage and export important backups over an authenticated channel before the trial
ends. Keeping the boot disk when deleting a VM does not protect it from trial-account expiry or project deletion.

## 7. Watch Engine and deployment checks

The Watch Engine runs **inside FastAPI**; it needs no separate container, queue or cron service. Startup
initializes the scheduler. A background thread wakes every 30 seconds and catches up on day boundaries when
the persisted clock mode is `real`. Real mode advances **dataset time** from its anchor, not directly to today's
calendar date. In `sim` mode, advancing the clock runs the scheduler; simply leaving the page open does not
advance simulated time.

The shared Demo remains at the initial **baseline / sim** scenario (1 Apr 2026, 07:00 at deployment). Do not
reset scenarios or switch the shared clock merely to check deployment. All visitors see the same state, and
starting a scenario resets it. Exercise destructive scenario demonstrations only on an agreed demo session or
an isolated test database.

Run the existing workflow tests on the **cloud VM** in a disposable container. It has no production volume,
API credentials or published ports; installing test dependencies here does not change the serving container.
The public checkout includes `backend/tests`; for an archive without tests, upload that reviewed directory first.

```bash
cd /opt/gm-copilot
docker run --rm --user 0:0 --env PYTHONPATH=/app/backend \
  --mount type=bind,source=/opt/gm-copilot/backend/tests,target=/checks,readonly \
  --entrypoint /bin/sh gm-copilot -c \
  'uv pip install --python /app/backend/.venv/bin/python pytest httpx --quiet && /app/backend/.venv/bin/python -m pytest -q -p no:cacheprovider /checks/test_workflows.py'
```

Before handing over a deployment:

- [ ] `docker compose -p gm-copilot ps` shows `healthy`; HTTPS `/api/health` returns `{"ok":true}` without `-k`.
- [ ] The React page and assets load from a separate network. Open it on a phone using mobile data too.
- [ ] `/api/state` returns 401 without an access code and with an incorrect code; the correct code works in Settings.
- [ ] Ask the read-only ORD-120 question with the team's permission to incur OpenAI fees. Evidence is available
      and **Show thinking** streams before the final answer. Do not paste the API key into the UI.
- [ ] Workflow tests pass. For a real-clock demonstration, use an isolated instance/database and confirm that
      the background ticker fires a due watch and creates a notification without a browser clock-advance call.
- [ ] Back up, record a conversation and database counts, then perform an agreed container restart or VM reboot.
      Verify health, conversation contents and counts again; do not reset the scenario to make the checks pass.
- [ ] The certificate renewal dry-run succeeds and both timers remain enabled after reboot.
- [ ] Unnormalized paths cannot return host/container files. For example, `//etc/os-release` must return the
      React fallback or an error, never system-file contents. Keep the normalized `proxy_pass` and private port.

**Completed deployment evidence (27 Oct):** public TLS and React assets passed; unauthenticated requests were
rejected; one real answer was grounded with an evidence reference, with first SSE output around 1 second and
the final answer around 10 seconds. Seven workflow tests passed, and an isolated real-clock ticker test fired
a watch and created a notification. A VM reboot retained 120 orders and 360 production records; a container
restart retained the test conversation with identical contents. SQLite integrity and certificate renewal
checks passed. These are deployment smoke checks, not new Evaluation results or a claim of load-test coverage.

## 8. Operations and updates

All commands below are run as root on the VM, from `/opt/gm-copilot` where relevant.

| Task | Command / action |
|---|---|
| Service status | `systemctl is-active gm-copilot docker nginx gm-certbot-renew.timer gm-copilot-backup.timer` |
| Container status | `docker compose -p gm-copilot ps` |
| Recent app logs | `docker compose -p gm-copilot logs --tail=100 app` (review privately before sharing) |
| Resource usage | `docker stats --no-stream`, `free -m`, `df -h /` |
| Manual backup | `/usr/local/sbin/gm-copilot-backup` |
| Certificate checks | `/opt/certbot/bin/certbot certificates`; `systemctl list-timers gm-certbot-renew.timer` |
| Restart the app | `docker compose -p gm-copilot restart app`, then check health |
| Stop intentionally | `systemctl stop gm-copilot` (data remains; VM/disk/IP still consume credit) |
| Start again | `systemctl start gm-copilot` |
| Credential rotation | Privately edit `backend/.env` or `deploy/deploy.env`, then `docker compose -p gm-copilot up -d --wait`; a plain restart does not reload changed environment files |

For a checkout cloned from the public repository, back up before pulling an approved release and rebuilding
**on the VM**. Review the release for migrations before updating. This does not reset the volume:

```bash
cd /opt/gm-copilot
/usr/local/sbin/gm-copilot-backup
git status --short
git pull --ff-only
docker compose -p gm-copilot build
docker compose -p gm-copilot up -d --wait --wait-timeout 180
```

The original VM was deployed from an archive and has no Git checkout; for it, transfer a reviewed source-only
archive over IAP, preserve `backend/.env`, `deploy/deploy.env` and the existing volume, then run the same cloud
build/start commands. Never copy a workstation database over the production database. Restore only during a
planned stop, after backing up the current state and handling SQLite WAL/SHM files together; do not overwrite
a running database.

## 9. Sprint 2 publication and troubleshooting

The public slide/repository can contain the **Demo URL and public GitHub URL**. Give graders the access code
separately through the private course/team channel. A public site can use access control; no credential belongs
in the public README. Check the links and trial availability before recording and before grading.

When working from the private development repository, the public README source is `scripts/public/README.md`.
Use the export allowlist rather than making private Git history public: the private repository has a legacy
tracked environment file. The exporter without `--push` still writes/commits a local export, so use a dedicated
review directory and inspect its output. Publication requires a separate approval; this documentation change
does not push either repository. Keep real environment files, tokens, SSH keys, databases and private evaluation
material out of the staged/exported changes. Public `.env.example` files contain non-secret defaults and blank
credential fields only.

| Symptom | Check |
|---|---|
| HTTPS unavailable | VM/trial state, reserved IP attachment, Standard tier, 80/443 firewall tags, `nginx -t`, certificate timer |
| 502 from Nginx | Container health, localhost `/api/health`, Docker/systemd status |
| Access code rejected | Correct private code in Settings; recreate the container after editing its environment |
| OpenAI 401 | Privately replace the invalid/revoked key, then recreate the container; cloud credit does not cover OpenAI |
| Chat 429 | Application daily estimated model budget or per-visitor rate limit; inspect usage in the UI |
| All visitors share a limiter | `TRUST_PROXY=true` and Nginx overwriting `CF-Connecting-IP`; do not expose port 8000 |
| Stream arrives only at the end | `proxy_buffering off` and no intermediary buffering SSE |
| Watch seems idle | Check sim/real mode and the watch's dataset-time deadline; sim needs clock advancement |
| Data appears missing after update | Check Compose project name and `gm-copilot_gm-var`; do not reset or recreate data |
| SSH user creation fails | Use `gmdeploy`, not a numeric Windows username; check IAP permissions and its source-range firewall |

The optional `tunnel` Compose profile remains available for a separately managed Cloudflare domain, but it is
not used by this deployment. Do not enable it or publish a temporary tunnel URL as a substitute for this fixed
HTTPS endpoint without reviewing the resulting network and access-control configuration.
