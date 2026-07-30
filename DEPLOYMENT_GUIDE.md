# LinkedIn Multi-Agent Automation System — Deployment Guide

> **Senior Review Notes** — Every command in this guide was verified against the actual source code.
> If you find a discrepancy, the source code wins. Known limitations and partially-implemented
> features are called out explicitly rather than papered over.

---

## Table of Contents

1. [Architecture & Data Flow](#1-architecture--data-flow)
2. [Known Limitations (Read First)](#2-known-limitations-read-first)
3. [Prerequisites](#3-prerequisites)
4. [Credential Setup](#4-credential-setup)
5. [Deployment Option A — Docker Compose](#5-deployment-option-a--docker-compose)
6. [Deployment Option B — Local Development](#6-deployment-option-b--local-development)
7. [Deployment Option C — Kubernetes](#7-deployment-option-c--kubernetes)
8. [Configuration Reference](#8-configuration-reference)
9. [Post-Deployment Verification](#9-post-deployment-verification)
10. [Monitoring Setup](#10-monitoring-setup)
11. [Operational Runbook](#11-operational-runbook)
12. [Security Hardening](#12-security-hardening)
13. [Troubleshooting](#13-troubleshooting)
14. [Appendix](#14-appendix)

---

## 1. Architecture & Data Flow

```
┌─────────────────────────────────────────────────────────┐
│                      Client Layer                        │
│   REST API (/api/v1/campaigns)    WhatsApp Monitor       │
│          Web Dashboard (placeholder)                     │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│                  AgentOrchestrator                        │
│   - Starts / stops agent pools                           │
│   - Health monitoring (30s interval)                     │
│   - Auto-scales pools on load (>80% → scale up)          │
└──┬────────┬────────┬────────┬────────┬──────────────────┘
   │        │        │        │        │
   ▼        ▼        ▼        ▼        ▼
Account  Content  Interact  Convers  Safety   Scheduler  Analytics  WhatsApp
Manager  Analyzer  Agent    Agent    Agent    Agent      Agent      Monitor
   │        │        │        │
   └────────┴────────┴────────┘
                    │
          ┌─────────▼──────────┐
          │       Redis         │  ← pub/sub, heartbeats, rate limits,
          │  (State + MQ + KV)  │    agent state, message queue
          └─────────────────────┘
                    │
          ┌─────────▼──────────┐
          │  Supabase/Postgres  │  ← campaigns, accounts, analytics
          └─────────────────────┘
```

**Agent startup dependency order:**

```
Redis → account_manager → interaction
      → content_analysis → conversation
      → safety
      → scheduler
      → analytics
      → whatsapp_monitor
```

The orchestrator enforces this automatically. In Docker Compose, start Redis first, then
let the orchestrator handle agent initialization.

---

## 2. Known Limitations (Read First)

Before spending time on deployment, understand what is and is not finished.

| Feature | Status | Notes |
|---|---|---|
| Agent orchestration | ✅ Working | Full lifecycle, auto-scaling, health checks |
| Redis message bus | ✅ Working | pub/sub, priority queues, state management |
| Account management | ✅ Working | Encryption, session handling, rotation |
| Content analysis | ✅ Working | NLP pipeline, OpenAI scoring |
| Interaction agent | ✅ Working | Rate-limited likes, comments, follows |
| Conversation agent | ✅ Working | OpenAI-generated comments |
| Safety agent | ✅ Working | Rate limit monitoring, cooldowns |
| Campaign API | ✅ Working | CRUD + start/pause/resume |
| **Web dashboard** | ⚠️ Placeholder | `--web-dashboard` flag prints a message and exits |
| **Monitoring endpoints** | ⚠️ Placeholder | `--monitoring` flag prints a message and exits |
| WhatsApp monitor | ⚠️ Config only | Agent class not yet implemented |
| Database migrations | ⚠️ Manual | No Alembic migration files included |
| Anthropic API | ⚠️ Partial | Key is in `.env.example` but `config.py` only reads `OPENAI_API_KEY` |

**Consequence**: Do not plan around the web dashboard or Prometheus metrics endpoint
for your first deployment. Use `docker-compose logs` and the Redis CLI for visibility.

---

## 3. Prerequisites

### 3.1 Hardware Minimums

| | Docker | Local Dev | Kubernetes (per node) |
|---|---|---|---|
| CPU | 2 cores | 2 cores | 4 cores |
| RAM | 4 GB | 4 GB | 8 GB |
| Disk | 20 GB | 10 GB | 50 GB |

### 3.2 Software Requirements

**Docker deployment:**

```bash
docker --version          # 20.10+
docker-compose --version  # 1.29+ or docker compose v2
git --version
python3 --version         # only needed to generate encryption key
```

**Local development:**

```bash
python3 --version  # 3.8–3.11 (Dockerfile uses 3.11)
redis-server --version  # 6.0+
git --version
```

**Kubernetes:**

```bash
kubectl version --client  # 1.21+
kubectl cluster-info      # must return without error
kubectl get storageclass  # must have a default StorageClass
```

---

## 4. Credential Setup

You need four things before running anything. Get them all before touching deployment.

### 4.1 OpenAI API Key

1. Create account at [platform.openai.com](https://platform.openai.com)
2. **API Keys → Create new secret key**
3. Copy the key — it starts with `sk-`

> **Why OpenAI and not Anthropic?** The current `config.py` only reads `OPENAI_API_KEY`
> from environment variables. The `.env.example` lists `ANTHROPIC_API_KEY` but the
> config loader does not consume it yet. Use OpenAI for now.

### 4.2 Supabase Database URL

The code in `src/database/session.py` reads `SUPABASE_DB_URL` — a direct PostgreSQL
connection string, **not** the Supabase project URL from the dashboard.

1. Create project at [supabase.com](https://supabase.com)
2. Navigate to **Settings → Database → Connection Pooling**
3. Enable **Transaction mode** (required for asyncpg)
4. Copy the **Connection string** — it looks like:

```
postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
```

5. Set it as `SUPABASE_DB_URL` in your environment.

> **Note:** `SUPABASE_URL` and `SUPABASE_KEY` (the REST API credentials) from `.env.example`
> are not consumed by the Python backend in this version. Only `SUPABASE_DB_URL` is used.

**Fallback (no Supabase):** Set `USE_SQLITE=true` for local testing. Not suitable for production.

```bash
# Local PostgreSQL fallback env vars
POSTGRES_USER=postgres
POSTGRES_PASSWORD=yourpassword
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=linkedin_automation
```

### 4.3 LinkedIn OAuth Credentials

1. Go to [LinkedIn Developer Portal](https://www.linkedin.com/developers/)
2. **Create app → fill required fields**
3. Under the **Auth** tab, add redirect URIs:
   - Local: `http://localhost:8000/auth/linkedin/callback`
   - Production: `https://yourdomain.com/auth/linkedin/callback`
4. Copy **Client ID** and **Client Secret**
5. Under **Products**, request: *Sign In with LinkedIn using OpenID Connect*

### 4.4 Encryption Key

The encryption key protects LinkedIn account passwords at rest. Generate it once and
store it securely — if lost, all stored credentials become unreadable.

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

The output (a base64 string ~44 chars) goes into `ENCRYPTION_KEY` in your `.env`.

**Important:** The config system stores the key content in the `.env` as `ENCRYPTION_KEY`.
Internally, `SecurityConfig.encryption_key_file` refers to a file path where the key is
written at runtime. You do not need to manage that file directly — it is handled by the
account manager agent on startup.

---

## 5. Deployment Option A — Docker Compose

**Best for:** First deployment, development, single-server production

Estimated time: **20–30 minutes**

### 5.1 Clone and Configure

```bash
git clone https://github.com/your-org/Social-Bot-LinkedIn-.git
cd Social-Bot-LinkedIn-
```

Create your `.env` from the example:

```bash
cp .env.example .env
```

Edit `.env` — replace every placeholder with real values:

```bash
# ── REQUIRED ──────────────────────────────────────────────────────────────────

# Database: direct PostgreSQL connection string from Supabase pooler
SUPABASE_DB_URL=postgresql://postgres.yourref:yourpassword@aws-0-us-east-1.pooler.supabase.com:6543/postgres

# LinkedIn OAuth
LINKEDIN_CLIENT_ID=86xxxxxxxxxxxxxxxx
LINKEDIN_CLIENT_SECRET=xxxxxxxxxxxxxxxx
LINKEDIN_REDIRECT_URI=http://localhost:8000/auth/linkedin/callback

# Fernet encryption key (generated in section 4.4)
ENCRYPTION_KEY=your-generated-fernet-key=

# AI: OpenAI (required for content analysis and conversation agents)
OPENAI_API_KEY=sk-...

# ── DOCKER-SPECIFIC (keep these values exactly as shown) ─────────────────────
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# ── OPTIONAL ──────────────────────────────────────────────────────────────────
LOG_LEVEL=INFO
ENVIRONMENT=production
LINKEDIN_HEADLESS=true
LINKEDIN_BROWSER_TYPE=playwright
```

### 5.2 Create the Config File

The system looks for `config/config.json` first, then falls back to environment variables.
Generate a baseline config:

```bash
mkdir -p config
python3 main.py --create-sample-config
# Creates: config/sample_config.json

cp config/sample_config.json config/config.json
```

Edit `config/config.json` with your target industries and keywords
(see [Section 8](#8-configuration-reference) for the full schema).

### 5.3 Build and Start

```bash
# Build all images (first run takes 5–10 min due to ML dependencies)
docker-compose build

# Start Redis first, verify it's healthy before proceeding
docker-compose up -d redis
docker-compose exec redis redis-cli ping
# Expected: PONG

# Start the full stack
docker-compose up -d
```

### 5.4 Verify All Services Are Running

```bash
docker-compose ps
```

Expected output — every service should show `Up`:

```
Name                         State   Ports
----------------------------------------------------------
linkedin-redis               Up      6379/tcp
linkedin-automation          Up      0.0.0.0:8080->8080/tcp
linkedin-account-manager     Up
linkedin-content-analyzer    Up
linkedin-interaction-agent   Up
linkedin-conversation-agent  Up
linkedin-safety-agent        Up
linkedin-scheduler           Up
linkedin-analytics           Up
```

If a service shows `Exit` or `Restarting`, check its logs immediately:

```bash
docker-compose logs --tail=50 linkedin-app   # service name, not container name
```

### 5.5 Tail Startup Logs

```bash
# Watch the orchestrator start agents
docker-compose logs -f linkedin-app

# Look for these lines in order:
# "Initializing orchestrator"
# "Connected to Redis"
# "Agent started" (repeated for each agent type)
# "Orchestrator started"
```

### 5.6 Optional: Monitoring Stack

The monitoring profile requires configuration files that are not included in the repo.
Create them before starting the profile:

```bash
mkdir -p monitoring/grafana/dashboards monitoring/grafana/datasources

# Minimal Prometheus config — scrapes the app
cat > monitoring/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'linkedin-automation'
    static_configs:
      - targets: ['linkedin-app:8080']
    metrics_path: '/metrics'
EOF

# Grafana datasource pointing at Prometheus
cat > monitoring/grafana/datasources/prometheus.yml << 'EOF'
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    url: http://prometheus:9090
    isDefault: true
EOF
```

Then start the monitoring profile:

```bash
docker-compose --profile monitoring up -d
# Prometheus: http://localhost:9090
# Grafana:    http://localhost:3000  (admin / admin)
```

> **Caveat:** The `--monitoring` flag in `main.py` is currently a placeholder that
> prints a message but does not expose Prometheus metrics. The Prometheus scrape will
> return no data until that is implemented.

### 5.7 Docker Compose Management

```bash
# View logs for a specific service
docker-compose logs -f account-manager

# Restart a single service
docker-compose restart conversation-agent

# Scale content analyzers to 3 instances
docker-compose up -d --scale content-analyzer=3

# Execute a command inside the main container
docker-compose exec linkedin-app bash

# Stop everything (keeps data volumes)
docker-compose stop

# Stop and remove containers (keeps named volumes)
docker-compose down

# Nuclear option: remove containers AND volumes (deletes all data)
docker-compose down -v
```

---

## 6. Deployment Option B — Local Development

**Best for:** Debugging, adding features, understanding the codebase

Estimated time: **25–40 minutes**

### 6.1 Python Environment

```bash
python3 -m venv venv
source venv/bin/activate          # Linux / macOS
# .\venv\Scripts\activate         # Windows

pip install --upgrade pip
pip install -r requirements.txt   # takes 5–10 min (torch, transformers, etc.)
```

### 6.2 NLP Models and Browser

```bash
# SpaCy English model (required by content analysis agent)
python -m spacy download en_core_web_sm

# Playwright Chromium browser
playwright install chromium

# Linux only — install system browser dependencies
sudo playwright install-deps chromium
```

### 6.3 Redis

**Ubuntu/Debian:**
```bash
sudo apt update && sudo apt install -y redis-server
sudo systemctl start redis
redis-cli ping   # → PONG
```

**macOS:**
```bash
brew install redis
brew services start redis
redis-cli ping   # → PONG
```

**Windows (WSL2 recommended, or Docker):**
```bash
docker run -d -p 6379:6379 --name redis redis:7-alpine
```

### 6.4 Environment Variables

```bash
cp .env.example .env
# Edit .env with your credentials (same values as Docker section above,
# but change REDIS_HOST=localhost instead of redis)
```

Load them into your shell:

```bash
set -a && source .env && set +a
```

Verify the critical ones are set:

```bash
echo "OpenAI:    ${OPENAI_API_KEY:0:8}..."
echo "DB URL:    ${SUPABASE_DB_URL:0:30}..."
echo "Enc Key:   ${ENCRYPTION_KEY:0:10}..."
echo "Redis:     $REDIS_HOST:$REDIS_PORT"
```

### 6.5 Generate Config and Validate

```bash
mkdir -p config
python main.py --create-sample-config
# Creates: config/sample_config.json

cp config/sample_config.json config/config.json
# Edit config/config.json with your target industries/keywords

# Validate without starting
python main.py --dry-run
# Expected output: Configuration validation passed
```

### 6.6 Run the System

```bash
# Run all agents
python main.py --config config/config.json

# Run specific agents only (useful for testing one agent at a time)
python main.py --config config/config.json --agents account_manager,content_analysis

# Verbose output for debugging
python main.py --config config/config.json --log-level DEBUG
```

**Available agent names** (use these exactly with `--agents`):

| CLI Name | Description |
|---|---|
| `account_manager` | LinkedIn auth and session management |
| `content_analysis` | NLP analysis of LinkedIn posts |
| `interaction` | Executes likes, comments, follows |
| `conversation` | AI comment generation |
| `safety` | Rate limit enforcement |
| `scheduler` | Task timing and scheduling |
| `analytics` | Performance tracking |
| `whatsapp_monitor` | WhatsApp URL ingestion (not yet implemented) |

### 6.7 Graceful Shutdown

The system handles `SIGINT` (Ctrl+C) and `SIGTERM` gracefully — agents stop cleanly and
deregister from Redis. Do not kill with `kill -9` during production use.

---

## 7. Deployment Option C — Kubernetes

**Best for:** Multi-server production, horizontal scaling, high availability

Estimated time: **45–60 minutes** (assumes cluster already exists)

### 7.1 Pre-flight Checks

```bash
# Verify cluster access
kubectl cluster-info

# Verify a default StorageClass exists (needed for Redis PVC)
kubectl get storageclass
# Look for one marked "(default)"

# Verify you have cluster-admin rights
kubectl auth can-i create namespace --all-namespaces
# Expected: yes
```

### 7.2 Build and Push the Docker Image

The Kubernetes manifests reference `linkedin-automation:latest`. Build and push it to
your container registry before deploying.

```bash
# Build
docker build -t linkedin-automation:latest .

# Tag and push (replace with your registry)
docker tag linkedin-automation:latest your-registry.io/linkedin-automation:v1.0.0
docker push your-registry.io/linkedin-automation:v1.0.0
```

Update the `image:` field in all `deployment/kubernetes/*.yaml` files to your registry path.

### 7.3 Namespace

```bash
kubectl apply -f deployment/kubernetes/namespace.yaml

# Verify
kubectl get namespace linkedin-automation
```

### 7.4 Secrets

Secrets must be created before deployments. Never put secret values in YAML files
committed to git.

```bash
# Generate encryption key
ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Prompt for sensitive values (not echoed to terminal)
read -s -p "OpenAI API key:      " OPENAI_API_KEY; echo
read -s -p "Supabase DB URL:     " SUPABASE_DB_URL; echo
read -s -p "LinkedIn Client ID:  " LINKEDIN_CLIENT_ID; echo
read -s -p "LinkedIn Secret:     " LINKEDIN_CLIENT_SECRET; echo

# Create the secret
kubectl create secret generic linkedin-secrets \
  --from-literal=openai-api-key="$OPENAI_API_KEY" \
  --from-literal=encryption-key="$ENCRYPTION_KEY" \
  --from-literal=supabase-db-url="$SUPABASE_DB_URL" \
  --from-literal=linkedin-client-id="$LINKEDIN_CLIENT_ID" \
  --from-literal=linkedin-client-secret="$LINKEDIN_CLIENT_SECRET" \
  -n linkedin-automation \
  --dry-run=client -o yaml | kubectl apply -f -

# Verify (values should be hidden)
kubectl get secret linkedin-secrets -n linkedin-automation
```

### 7.5 ConfigMap

The `configmap.yaml` embeds `config.json` directly. Review and edit the values — specifically
`target_industries` and `target_keywords` — before applying:

```bash
# Review what's in the ConfigMap
cat deployment/kubernetes/configmap.yaml

# Apply
kubectl apply -f deployment/kubernetes/configmap.yaml

# Verify
kubectl get configmap linkedin-config -n linkedin-automation -o yaml
```

### 7.6 Deploy Redis

> **Note:** Redis is deployed as a `Deployment` (not a StatefulSet) in the current manifests.
> This means Redis pod names are not predictable. Use the label selector to access Redis pods.

```bash
kubectl apply -f deployment/kubernetes/redis.yaml

# Wait for Redis to be Ready (up to 2 minutes)
kubectl wait --for=condition=available deployment/redis \
  -n linkedin-automation --timeout=120s

# Find the Redis pod name (it has a random suffix)
REDIS_POD=$(kubectl get pods -n linkedin-automation -l app=redis -o jsonpath='{.items[0].metadata.name}')
echo "Redis pod: $REDIS_POD"

# Verify Redis is responding
kubectl exec -n linkedin-automation "$REDIS_POD" -- redis-cli ping
# Expected: PONG
```

### 7.7 Deploy the Orchestrator

```bash
kubectl apply -f deployment/kubernetes/orchestrator.yaml

# The orchestrator has HTTP health probes on /health and /ready
# Wait for it to be available (up to 5 minutes — needs to pull image and initialize)
kubectl wait --for=condition=available deployment/linkedin-orchestrator \
  -n linkedin-automation --timeout=300s

# Stream logs
kubectl logs -f deployment/linkedin-orchestrator -n linkedin-automation
```

### 7.8 Deploy Agents

```bash
kubectl apply -f deployment/kubernetes/agents.yaml

# Wait for all deployments to be available
kubectl wait --for=condition=available deployment --all \
  -n linkedin-automation --timeout=600s

# Check all deployments
kubectl get deployments -n linkedin-automation
```

Expected state:

```
NAME                    READY   UP-TO-DATE   AVAILABLE
redis                   1/1     1            1
linkedin-orchestrator   1/1     1            1
account-manager         1/1     1            1
content-analyzer        2/2     2            2
interaction-agent       2/2     2            2
conversation-agent      2/2     2            2
safety-agent            1/1     1            1
scheduler-agent         1/1     1            1
analytics-agent         1/1     1            1
```

### 7.9 Local Access (Port Forward)

```bash
# Access the orchestrator API locally
kubectl port-forward service/linkedin-orchestrator 8080:80 -n linkedin-automation &

# Test the health endpoint
curl http://localhost:8080/health
```

### 7.10 Horizontal Pod Autoscaling

Apply HPA for agents that benefit from scaling:

```yaml
# Save as deployment/kubernetes/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: content-analyzer-hpa
  namespace: linkedin-automation
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: content-analyzer
  minReplicas: 2
  maxReplicas: 8
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: interaction-agent-hpa
  namespace: linkedin-automation
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: interaction-agent
  minReplicas: 2
  maxReplicas: 8
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

```bash
kubectl apply -f deployment/kubernetes/hpa.yaml
kubectl get hpa -n linkedin-automation
```

### 7.11 Kubernetes Operations

```bash
# View all resources
kubectl get all -n linkedin-automation

# Tail logs for a deployment
kubectl logs -f deployment/content-analyzer -n linkedin-automation

# Execute a shell in a pod
kubectl exec -it deployment/linkedin-orchestrator -n linkedin-automation -- bash

# Scale a deployment manually
kubectl scale deployment content-analyzer --replicas=4 -n linkedin-automation

# Trigger rolling restart (e.g., after updating a ConfigMap)
kubectl rollout restart deployment --all -n linkedin-automation

# Check rollout status
kubectl rollout status deployment/linkedin-orchestrator -n linkedin-automation

# View recent events (sorted by time)
kubectl get events -n linkedin-automation --sort-by='.lastTimestamp' | tail -20

# Resource usage
kubectl top pods -n linkedin-automation

# Tear down everything
kubectl delete namespace linkedin-automation
```

---

## 8. Configuration Reference

### 8.1 How Configuration Is Loaded

The system uses this priority order (highest wins):

1. **`config/config.json`** — if the file exists, it is used exclusively
2. **Environment variables** — used only when `config/config.json` is absent

In Docker and Kubernetes, the recommended approach is to mount a `config.json`
(as a volume or ConfigMap). In local development, environment variables are simpler.

### 8.2 Generating a Baseline Config

```bash
python main.py --create-sample-config
# Writes: config/sample_config.json

cp config/sample_config.json config/config.json
```

### 8.3 Complete `config.json` Schema

This schema is derived directly from `src/config/config.py`. Every field name and
default value matches the source code.

```json
{
  "redis": {
    "host": "localhost",
    "port": 6379,
    "password": "",
    "db": 0
  },

  "security": {
    "encryption_key_file": ".encryption_key",
    "max_login_attempts": 3,
    "session_timeout": 3600,
    "rate_limit_window": 3600,
    "enable_2fa": false
  },

  "linkedin": {
    "likes_per_hour": 30,
    "likes_per_day": 150,
    "comments_per_hour": 10,
    "comments_per_day": 50,
    "shares_per_hour": 5,
    "shares_per_day": 20,
    "follows_per_hour": 20,
    "follows_per_day": 100,
    "connections_per_hour": 10,
    "connections_per_day": 50,
    "like_cooldown": 10,
    "comment_cooldown": 60,
    "share_cooldown": 120,
    "follow_cooldown": 30,
    "connection_cooldown": 60,
    "business_hours": [9, 18],
    "peak_hours": [10, 11, 14, 15],
    "weekend_activity": 0.3,
    "random_delay_range": [2, 10],
    "headless": true,
    "browser_type": "playwright"
  },

  "content_analysis": {
    "openai_api_key": "",
    "use_local_models": false,
    "model_name": "gpt-3.5-turbo",
    "cache_ttl": 3600,
    "min_relevance_score": 0.5,
    "min_quality_score": 0.4,
    "target_industries": ["technology", "finance", "healthcare"],
    "target_keywords": ["AI", "machine learning", "innovation"],
    "excluded_keywords": ["politics", "controversial"]
  },

  "conversation": {
    "openai_api_key": "",
    "use_local_models": false,
    "model_name": "gpt-3.5-turbo",
    "cache_ttl": 3600,
    "min_confidence_score": 0.7,
    "min_quality_score": 0.6,
    "min_relevance_score": 0.6,
    "max_alternatives": 3,
    "diversity_threshold": 0.8
  },

  "log_level": "INFO",
  "max_workers": 10,
  "health_check_interval": 30
}
```

> **Important:** The `openai_api_key` fields in `content_analysis` and `conversation`
> will be overwritten at runtime by the `OPENAI_API_KEY` environment variable when
> using `SystemConfig.from_env()`. If you use a `config.json`, populate those fields
> directly or they will remain empty.

### 8.4 Environment Variables Reference

Only these variables are read by `src/config/config.py`'s `from_env()` method:

| Variable | Used By | Default | Notes |
|---|---|---|---|
| `REDIS_HOST` | `config.py` | `localhost` | Use `redis` in Docker |
| `REDIS_PORT` | `config.py` | `6379` | |
| `REDIS_PASSWORD` | `config.py` | `""` | |
| `REDIS_DB` | `config.py` | `0` | |
| `OPENAI_API_KEY` | `config.py` | `""` | Required for AI agents |
| `LINKEDIN_HEADLESS` | `config.py` | `true` | Set `false` to debug browser |
| `LINKEDIN_BROWSER_TYPE` | `config.py` | `playwright` | Or `selenium` |
| `LOG_LEVEL` | `config.py` | `INFO` | `DEBUG` for verbose output |
| `MAX_WORKERS` | `config.py` | `10` | Concurrent worker limit |

Only these variables are read by `src/database/session.py`:

| Variable | Priority | Notes |
|---|---|---|
| `SUPABASE_DB_URL` | 1st | Full PostgreSQL connection string from Supabase pooler |
| `USE_SQLITE` | 2nd | Set `true` for local testing (not production) |
| `POSTGRES_USER` | 3rd | Used if neither of the above are set |
| `POSTGRES_PASSWORD` | 3rd | |
| `POSTGRES_HOST` | 3rd | |
| `POSTGRES_PORT` | 3rd | |
| `POSTGRES_DB` | 3rd | |

Variables in `.env.example` that are **not** currently consumed by Python code:

| Variable | Status |
|---|---|
| `SUPABASE_URL` | In `.env.example` but not read by any Python file |
| `SUPABASE_KEY` | In `.env.example` but not read by any Python file |
| `ANTHROPIC_API_KEY` | In `.env.example` but `config.py` only reads `OPENAI_API_KEY` |
| `ENABLE_TOKEN_MONITOR` | In `.env.example` but not wired to any config field |
| `FRONTEND_URL` | In `.env.example` but not wired to any config field |
| `SENTRY_DSN` | In `.env.example` but not wired to any config field |

### 8.5 Tuning for Your Scale

**Conservative (starting out — 1–5 accounts):**

```json
{
  "linkedin": {
    "likes_per_hour": 10,
    "likes_per_day": 50,
    "comments_per_hour": 3,
    "comments_per_day": 15,
    "follows_per_hour": 5,
    "follows_per_day": 20
  },
  "safety": {},
  "log_level": "DEBUG"
}
```

**Standard (stable — 10–20 accounts):**

```json
{
  "linkedin": {
    "likes_per_hour": 30,
    "likes_per_day": 150,
    "comments_per_hour": 10,
    "comments_per_day": 50
  }
}
```

**Aggressive (validated — 50+ accounts with established safety history):**

Only increase limits after several weeks of operation with zero suspensions.
LinkedIn's anti-automation systems learn account patterns over time.

---

## 9. Post-Deployment Verification

Run these checks in order. Fix each failure before proceeding to the next.

### 9.1 Redis Connectivity

```bash
# Docker
docker-compose exec redis redis-cli ping

# Kubernetes
REDIS_POD=$(kubectl get pods -n linkedin-automation -l app=redis -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n linkedin-automation "$REDIS_POD" -- redis-cli ping

# Local
redis-cli ping

# All should return: PONG
```

### 9.2 Database Connectivity

```bash
# Test the database connection string directly
python3 -c "
import asyncio, os
from sqlalchemy.ext.asyncio import create_async_engine

async def test():
    url = os.getenv('SUPABASE_DB_URL', '')
    if not url:
        print('SUPABASE_DB_URL not set — testing SQLite fallback')
        url = 'sqlite+aiosqlite:///./test.db'
    else:
        url = url.replace('postgresql://', 'postgresql+asyncpg://')
    engine = create_async_engine(url, connect_args={'statement_cache_size': 0})
    async with engine.connect() as conn:
        await conn.execute(__import__('sqlalchemy').text('SELECT 1'))
    print('Database connection: OK')
    await engine.dispose()

asyncio.run(test())
"
```

### 9.3 System Health Check

```bash
# Docker (exec into the main container by service name)
docker-compose exec linkedin-app python -c "
import asyncio
from src.infrastructure.health_check import health_check
asyncio.run(health_check())
"

# Kubernetes
kubectl exec -it deployment/linkedin-orchestrator -n linkedin-automation -- python -c "
import asyncio
from src.infrastructure.health_check import health_check
asyncio.run(health_check())
"

# Local (run from the repo root)
python -c "
import asyncio
from src.infrastructure.health_check import health_check
asyncio.run(health_check())
"
```

Expected output format:

```
System Status: HEALTHY
Timestamp: 2025-05-12T10:30:00.000000

Summary:
  Total Checks: 6
  Healthy: 6
  Degraded: 0
  Unhealthy: 0

Individual Checks:
  ✅ redis: healthy
  ✅ agent_account_manager: healthy
  ✅ agent_content_analysis: healthy
  ✅ agent_interaction: healthy
  ✅ agent_conversation: healthy
  ✅ agent_safety: healthy
```

### 9.4 Agent Heartbeat Verification via Redis

Agents publish heartbeats every 10 seconds. If an agent is running, its heartbeat key
will exist in Redis with a 30-second TTL.

```bash
# Docker
docker-compose exec redis redis-cli keys "heartbeat:*"

# Kubernetes
kubectl exec -n linkedin-automation "$REDIS_POD" -- redis-cli keys "heartbeat:*"
```

Each running agent should appear:
```
heartbeat:account_manager_1234567890.123
heartbeat:content_analysis_1234567890.456
...
```

Inspect a specific heartbeat:

```bash
docker-compose exec redis redis-cli get "heartbeat:account_manager_1234567890.123"
# Returns JSON: {"agent_id": "...", "state": "ready", "timestamp": "...", "health_metrics": {...}}
```

### 9.5 Validate Configuration Parsing

```bash
# Confirm config.json is loading correctly
python main.py --dry-run

# Expected output (exactly):
# Configuration validation passed

# If it prints "Configuration errors:", fix those before proceeding
```

### 9.6 API Endpoint Smoke Test

```bash
# Health check endpoint
curl -s http://localhost:8080/health | python3 -m json.tool

# Campaign API (if the FastAPI server is running)
curl -s http://localhost:8000/api/v1/campaigns | python3 -m json.tool
```

---

## 10. Monitoring Setup

### 10.1 What Is Available Today

| Method | Available | How |
|---|---|---|
| Structured JSON logs | ✅ Yes | `docker-compose logs -f` |
| Redis state inspection | ✅ Yes | `redis-cli` commands below |
| Agent heartbeats | ✅ Yes | `redis-cli keys "heartbeat:*"` |
| Orchestrator metrics | ✅ Yes | `redis-cli hgetall orchestrator:metrics` |
| HTTP `/health` endpoint | ✅ Yes | `curl localhost:8080/health` |
| Prometheus metrics | ⚠️ Placeholder | Not yet implemented |
| Grafana dashboards | ⚠️ Placeholder | Requires Prometheus to be working |

### 10.2 Key Redis Inspection Commands

```bash
# (run inside redis container or with redis-cli)

# All registered agents
redis-cli keys "agents:*"

# Orchestrator health metrics
redis-cli hgetall orchestrator:metrics

# Rate limit status for an account
redis-cli keys "rate_limit:*"

# Message queues depth
redis-cli llen "queue:interaction"
redis-cli llen "queue:content_analysis"

# Agent state
redis-cli keys "state:*"

# Watch all keys being written in real time (warning: noisy in production)
redis-cli monitor
```

### 10.3 Log-Based Monitoring

All components use `structlog` with JSON output. In production, pipe logs to a
collector (Datadog, CloudWatch, Loki):

```bash
# Docker — stream logs to a file
docker-compose logs -f --no-color >> /var/log/linkedin-automation.log &

# Search logs for errors
docker-compose logs | grep '"level":"error"' | python3 -m json.tool

# Watch error rate in real time
docker-compose logs -f | grep --line-buffered '"level":"error"'
```

### 10.4 Log Rotation

Prevent disk exhaustion in long-running deployments:

```bash
# /etc/logrotate.d/linkedin-automation
/var/log/linkedin-automation.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    missingok
    create 0644 root root
}
```

---

## 11. Operational Runbook

### 11.1 Deploying a Config Change

**Docker:**

```bash
# Edit config/config.json
# Then restart only the affected service
docker-compose restart linkedin-app

# Or restart all agents
docker-compose restart
```

**Kubernetes:**

```bash
# Update the ConfigMap
kubectl edit configmap linkedin-config -n linkedin-automation

# Trigger rolling restart to pick up the change
kubectl rollout restart deployment --all -n linkedin-automation

# Monitor rollout
kubectl rollout status deployment/linkedin-orchestrator -n linkedin-automation
```

### 11.2 An Agent Is Crashing / Restarting

```bash
# Identify the problem
docker-compose logs --tail=100 account-manager

# Common causes and fixes:
# 1. "Connection refused" on Redis → Redis not started, check REDIS_HOST
# 2. "Authentication failed" → Wrong OPENAI_API_KEY
# 3. "No module named X" → pip install -r requirements.txt in container
# 4. "Rate limited" in LinkedIn → reduce rate limits in config.json

# Isolate the agent for debugging
docker-compose stop account-manager
docker-compose run --rm account-manager bash
# Inside the container:
python main.py --agents account_manager --log-level DEBUG
```

### 11.3 LinkedIn Account Is Flagged / Suspended

1. **Stop interaction agent immediately**
   ```bash
   docker-compose stop interaction-agent
   ```

2. **Check account status in Redis**
   ```bash
   docker-compose exec redis redis-cli keys "agents:*"
   ```

3. **Review safety agent logs**
   ```bash
   docker-compose logs --tail=200 safety-agent | grep -i "suspicious\|warning\|flagged"
   ```

4. **Wait minimum 24–48 hours** before restarting with lower rate limits.

5. **Reduce limits** in `config.json` before restarting:
   ```json
   {
     "linkedin": {
       "likes_per_hour": 5,
       "comments_per_hour": 2,
       "follows_per_hour": 3
     }
   }
   ```

6. Restart with the reduced config and monitor closely for the first hour.

### 11.4 High Memory Usage

```bash
# Docker — check per-container usage
docker stats --no-stream

# The content-analyzer and conversation-agent are heaviest
# (ML models in memory). Reduce instances if OOM kills occur.
docker-compose up -d --scale content-analyzer=1

# Kubernetes
kubectl top pods -n linkedin-automation
kubectl edit deployment content-analyzer -n linkedin-automation
# Reduce 'replicas' and adjust 'resources.limits.memory'
```

### 11.5 Redis Queue Backlog

If interactions are queuing faster than agents process them:

```bash
# Check queue depth
docker-compose exec redis redis-cli llen "queue:interaction"

# Scale up interaction agents
docker-compose up -d --scale interaction-agent=4

# Or increase rate limits if within LinkedIn's safe range
# Or reduce content ingestion rate
```

### 11.6 Rolling Update (Zero Downtime — Kubernetes Only)

```bash
# Build and push new image
docker build -t your-registry.io/linkedin-automation:v1.1.0 .
docker push your-registry.io/linkedin-automation:v1.1.0

# Update the image tag
kubectl set image deployment/linkedin-orchestrator \
  orchestrator=your-registry.io/linkedin-automation:v1.1.0 \
  -n linkedin-automation

# Monitor the rollout
kubectl rollout status deployment/linkedin-orchestrator -n linkedin-automation

# Rollback if something goes wrong
kubectl rollout undo deployment/linkedin-orchestrator -n linkedin-automation
```

### 11.7 Backup and Restore

**What to back up:**

| Data | Location | Backup Frequency |
|---|---|---|
| `.env` file | Local filesystem | After every change |
| `config/config.json` | Local filesystem | After every change |
| Supabase database | Managed by Supabase | Daily automatic + manual before migrations |
| Redis data (if persistence is on) | Docker volume `redis_data` | Daily |
| LinkedIn session files | Docker volume `linkedin_sessions` | Weekly |

**Back up Redis data:**

```bash
# Force Redis to write its RDB snapshot
docker-compose exec redis redis-cli BGSAVE

# Wait for it to complete
docker-compose exec redis redis-cli LASTSAVE  # note the timestamp

# Copy the dump file from the volume
docker cp linkedin-redis:/data/dump.rdb ./backups/redis-$(date +%Y%m%d).rdb
```

**Restore Redis data:**

```bash
docker-compose stop redis
docker cp ./backups/redis-20250501.rdb linkedin-redis:/data/dump.rdb
docker-compose start redis
```

---

## 12. Security Hardening

### 12.1 Before Going to Production

- [ ] **Secrets not in git** — confirm `.env` is in `.gitignore`
- [ ] **Rotate default credentials** — change all example/default values
- [ ] **Redis password** — set `REDIS_PASSWORD` in production
- [ ] **LinkedIn account 2FA** — enable on every managed account
- [ ] **API key rotation schedule** — plan monthly rotation for OpenAI keys
- [ ] **Principle of least privilege** — the Supabase DB user should only have access to the `linkedin_automation` schema
- [ ] **TLS in production** — all traffic behind HTTPS; use a reverse proxy (nginx, Caddy)
- [ ] **Rate limit Redis port** — Redis (6379) must never be exposed to the internet

### 12.2 Docker Security

The Dockerfile already enforces:
- Non-root user (`app`, UID 1000)
- Multi-stage build (build deps not in production image)
- No `--privileged` flag

Additional hardening:

```yaml
# docker-compose.yml additions
services:
  linkedin-app:
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
    # Drop all capabilities
    cap_drop:
      - ALL
```

### 12.3 Redis Hardening

For production Redis, always set a password and disable dangerous commands:

```bash
# redis.conf additions
requirepass your-strong-redis-password
rename-command FLUSHALL ""
rename-command FLUSHDB ""
rename-command CONFIG ""
rename-command KEYS ""
bind 127.0.0.1  # or the Docker network IP only
```

Pass this to Docker:

```yaml
services:
  redis:
    command: redis-server /usr/local/etc/redis/redis.conf
    volumes:
      - ./redis.conf:/usr/local/etc/redis/redis.conf:ro
```

### 12.4 Secret Rotation Procedure

1. Generate new key/credential
2. Update the secret in your secret manager (Kubernetes secret, environment)
3. Rolling restart agents: `kubectl rollout restart deployment --all -n linkedin-automation`
4. Verify agents reconnect successfully
5. Revoke the old credential

### 12.5 `.gitignore` Essentials

Confirm these are in `.gitignore`:

```
.env
.env.*
config/config.json
config/sample_config.json
*.encryption_key
logs/
data/
sessions/
*.db
```

---

## 13. Troubleshooting

### Import / Module Errors

**Symptom:** `ModuleNotFoundError: No module named 'src'`

This happens when running Python commands from a directory other than the repo root,
or when `src` is not on the path.

```bash
# Always run from the repo root
cd /path/to/Social-Bot-LinkedIn-

# Confirm Python sees the correct working directory
python3 -c "import os; print(os.getcwd())"
# Should print the repo root

# Then run
python main.py --dry-run
```

---

**Symptom:** `ModuleNotFoundError: No module named 'playwright'`

```bash
# Ensure virtualenv is activated
which python  # should point to venv/bin/python

# Re-install
pip install -r requirements.txt
playwright install chromium
```

---

### Redis Connection Errors

**Symptom:** `Connection refused` or `ConnectionError`

```bash
# Is Redis actually running?
redis-cli ping               # local
docker-compose ps redis      # Docker

# Is REDIS_HOST set correctly?
# Local development → REDIS_HOST=localhost
# Docker → REDIS_HOST=redis (the service name in docker-compose.yml)
echo $REDIS_HOST

# Test connection directly
redis-cli -h $REDIS_HOST -p $REDIS_PORT ping
```

---

### Database Connection Errors

**Symptom:** `asyncpg.exceptions.TooManyConnectionsError`

```bash
# The Supabase pooler must be in Transaction mode for asyncpg
# Check your SUPABASE_DB_URL — the port for Transaction mode is 6543
# Session mode port is 5432

# If using direct connection (port 5432), switch to pooler (6543)
```

**Symptom:** `prepared statement "..." already exists`

```bash
# This happens when NOT using the Supabase pooler's Transaction mode
# The code already disables prepared statement caching for Supabase pooler URLs
# Ensure your SUPABASE_DB_URL contains "pooler.supabase.com" so the code
# applies the correct connection args
```

---

### Agents Not Appearing in Heartbeats

**Symptom:** `redis-cli keys "heartbeat:*"` returns empty

1. Check the orchestrator logs — did agent initialization fail?
   ```bash
   docker-compose logs linkedin-app | grep -i "error\|failed\|exception"
   ```

2. Confirm `OPENAI_API_KEY` is set (required for `content_analysis` and `conversation`)
   ```bash
   docker-compose exec linkedin-app env | grep OPENAI
   ```

3. Check agent dependency order — `interaction` requires `account_manager` to be registered first:
   ```bash
   docker-compose logs | grep "Agent started"
   ```

---

### Configuration Validation Fails

**Symptom:** `python main.py --dry-run` prints `Configuration errors:`

```
- "OpenAI API key required for content analysis and conversation agents"
```

Fix: Set `OPENAI_API_KEY` in your environment or in `config/config.json` under
`content_analysis.openai_api_key` and `conversation.openai_api_key`.

```
- "Daily like limit must be greater than hourly limit"
```

Fix: Ensure `likes_per_day > likes_per_hour` in your config.

---

### Docker Image Build Failures

**Symptom:** Build fails on `pip install torch` with OOM error

```bash
# Increase Docker memory limit to at least 4GB
# Docker Desktop: Settings → Resources → Memory

# Or build on a machine/VM with more RAM
```

**Symptom:** Playwright install fails in Docker

```bash
# Rebuild with no cache to get fresh apt packages
docker-compose build --no-cache

# If behind a corporate proxy, pass proxy args:
docker-compose build \
  --build-arg HTTP_PROXY=$HTTP_PROXY \
  --build-arg HTTPS_PROXY=$HTTPS_PROXY
```

---

### Kubernetes — Pods Stuck in `Pending`

```bash
kubectl describe pod <pod-name> -n linkedin-automation | grep -A 10 Events

# Common causes:
# "Insufficient memory" → node doesn't have enough RAM, scale cluster or reduce requests
# "no persistent volumes available" → StorageClass not configured
# "ImagePullBackOff" → wrong image name or registry not authenticated
```

**Fix ImagePullBackOff (private registry):**

```bash
kubectl create secret docker-registry regcred \
  --docker-server=your-registry.io \
  --docker-username=your-user \
  --docker-password=your-password \
  -n linkedin-automation

# Add to deployment spec:
# spec:
#   imagePullSecrets:
#   - name: regcred
```

---

## 14. Appendix

### 14.1 Deployment Decision Matrix

| Factor | Docker Compose | Local Dev | Kubernetes |
|---|---|---|---|
| Setup time | 20–30 min | 25–40 min | 45–60 min |
| Complexity | Low | Medium | High |
| Scalability | Medium (manual) | Low | High (HPA) |
| Debugging | Medium | Best | Hard |
| Production-ready | Yes (single server) | No | Yes (multi-server) |
| Auto-healing | Partial (`restart: unless-stopped`) | No | Yes |
| Recommended for | First deployment | Development | Scale production |

### 14.2 Resource Sizing Guide

| Account Count | CPU | RAM | Agent Config |
|---|---|---|---|
| 1–5 | 2 cores | 4 GB | 1 instance each |
| 6–20 | 4 cores | 8 GB | 1–2 instances each |
| 21–50 | 8 cores | 16 GB | 2–3 content-analyzer, 3–5 interaction |
| 50+ | 16+ cores | 32+ GB | K8s with HPA recommended |

### 14.3 Port Reference

| Port | Service | Exposed? |
|---|---|---|
| `8080` | Web dashboard / app | Yes (localhost in dev) |
| `8000` | FastAPI / REST API | Yes (localhost in dev) |
| `6379` | Redis | No (internal only in prod) |
| `9090` | Prometheus | Optional (monitoring profile) |
| `3000` | Grafana | Optional (monitoring profile) |
| `5432` | PostgreSQL | No (managed by Supabase) |

### 14.4 Valid Agent Names (CLI Reference)

These are the exact strings accepted by `--agents` and present in `config.agents`:

```
account_manager
content_analysis
interaction
conversation
safety
scheduler
analytics
whatsapp_monitor
```

### 14.5 Tested Dependency Versions

| Component | Version in `requirements.txt` |
|---|---|
| Python | 3.11 (Dockerfile), 3.8+ (local) |
| redis-py | 4.5.4 |
| playwright | 1.32.1 |
| openai | 0.27.4 |
| sqlalchemy | 2.0.10 |
| asyncpg | 0.27.0 |
| spacy | 3.5.2 |
| structlog | 23.1.0 |
| torch | 2.0.0 |
| pydantic | 1.10.7 |

Upgrading major versions (especially `openai`, `pydantic`, `torch`) without testing
is likely to break things. The `openai` 0.27.x SDK has a different API surface than
1.x and 2.x.

### 14.6 Health Check Script

Save this as `scripts/verify-deployment.sh` and run it after any deployment:

```bash
#!/usr/bin/env bash
set -euo pipefail

REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"

echo "=== LinkedIn Automation Deployment Verification ==="
echo

# Redis
printf "Redis connectivity... "
if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping &>/dev/null; then
    echo "OK"
else
    echo "FAIL — is Redis running? Is REDIS_HOST=$REDIS_HOST correct?"
    exit 1
fi

# Agent heartbeats
printf "Agent heartbeats...   "
HEARTBEATS=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" keys "heartbeat:*" 2>/dev/null | wc -l)
if [ "$HEARTBEATS" -gt 0 ]; then
    echo "OK ($HEARTBEATS agents registered)"
else
    echo "WARN — no heartbeats found. Agents may still be starting up."
fi

# Orchestrator metrics
printf "Orchestrator state... "
STATE=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" hget orchestrator:info state 2>/dev/null)
if [ "$STATE" = "running" ]; then
    echo "OK (state=running)"
else
    echo "WARN — state='$STATE' (expected 'running')"
fi

# Config validation
printf "Configuration...      "
if python main.py --dry-run &>/dev/null; then
    echo "OK"
else
    echo "FAIL — run 'python main.py --dry-run' to see errors"
    exit 1
fi

echo
echo "=== Verification complete ==="
```

```bash
chmod +x scripts/verify-deployment.sh
./scripts/verify-deployment.sh
```

---

*Verified against source code — May 2025*
*Report inaccuracies via GitHub issues*
