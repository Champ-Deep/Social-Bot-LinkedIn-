# LinkedIn Multi-Agent Automation System - Deployment Guide

**Version:** 1.0
**Last Updated:** December 26, 2025
**Maintainer:** Development Team

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Pre-Deployment Checklist](#pre-deployment-checklist)
4. [Deployment Methods](#deployment-methods)
   - [Quick Start (Docker)](#quick-start-docker)
   - [Local Development](#local-development)
   - [Production (Kubernetes)](#production-kubernetes)
5. [Configuration Guide](#configuration-guide)
6. [Post-Deployment Verification](#post-deployment-verification)
7. [Security Hardening](#security-hardening)
8. [Monitoring & Maintenance](#monitoring--maintenance)
9. [Troubleshooting](#troubleshooting)
10. [FAQ](#faq)
11. [Getting Help](#getting-help)

---

## Overview

This guide provides step-by-step instructions for deploying the LinkedIn Multi-Agent Automation System in various environments. Choose the deployment method that best suits your needs:

- **Docker**: Best for quick setup, development, and small-scale production
- **Local Development**: Best for development and testing
- **Kubernetes**: Best for large-scale production deployments with high availability

**Estimated Deployment Time:**
- Docker: 15-30 minutes
- Local Development: 20-40 minutes
- Kubernetes: 30-60 minutes

---

## Prerequisites

### System Requirements

#### Minimum Hardware Requirements

| Component | Docker | Local | Kubernetes (per node) |
|-----------|--------|-------|----------------------|
| CPU | 2 cores | 2 cores | 4 cores |
| RAM | 4 GB | 4 GB | 8 GB |
| Storage | 20 GB | 10 GB | 50 GB |
| Network | Stable internet connection | Stable internet connection | Stable internet connection |

#### Recommended Hardware Requirements

| Component | Docker | Local | Kubernetes (per node) |
|-----------|--------|-------|----------------------|
| CPU | 4+ cores | 4+ cores | 8+ cores |
| RAM | 8+ GB | 8+ GB | 16+ GB |
| Storage | 50+ GB SSD | 20+ GB SSD | 100+ GB SSD |
| Network | High-speed internet | High-speed internet | High-speed internet |

### Software Requirements

#### For Docker Deployment

- **Operating System**: Linux, macOS, or Windows 10/11
- **Docker**: Version 20.10+ ([Install Docker](https://docs.docker.com/get-docker/))
- **Docker Compose**: Version 1.29+ ([Install Docker Compose](https://docs.docker.com/compose/install/))
- **Git**: For cloning the repository

```bash
# Verify installations
docker --version          # Should show 20.10+
docker-compose --version  # Should show 1.29+
git --version
```

#### For Local Development

- **Operating System**: Linux, macOS, or Windows 10/11 with WSL2
- **Python**: Version 3.8 - 3.11 ([Download Python](https://www.python.org/downloads/))
- **Redis**: Version 6.0+ ([Install Redis](https://redis.io/download))
- **Git**: For cloning the repository
- **Build Tools**: gcc, make (for compiling Python packages)

```bash
# Verify installations
python3 --version  # Should show 3.8+
redis-server --version  # Should show 6.0+
git --version
```

#### For Kubernetes Deployment

- **Kubernetes Cluster**: Version 1.21+ (EKS, GKE, AKS, or self-managed)
- **kubectl**: Configured to access your cluster ([Install kubectl](https://kubernetes.io/docs/tasks/tools/))
- **Helm** (optional): Version 3.0+ for easier deployment
- **Storage Provisioner**: For persistent volumes (e.g., EBS, GCE PD)

```bash
# Verify installations
kubectl version --client
kubectl cluster-info
```

### External Services Required

#### 1. Supabase (Database)

**Purpose**: Primary database for storing accounts, interactions, and analytics

**Setup Steps:**
1. Create account at [supabase.com](https://supabase.com)
2. Create a new project
3. Navigate to **Settings** → **API**
4. Copy your **Project URL** and **Service Role Key**
5. Navigate to **Settings** → **Database** → **Connection Pooling**
6. Enable connection pooler and set mode to **Transaction**
7. Copy the **Pooler Connection String**

**Cost**: Free tier available (50,000 rows, 500 MB database, 2 GB file storage)

#### 2. LinkedIn Developer Account

**Purpose**: OAuth authentication for LinkedIn accounts

**Setup Steps:**
1. Go to [LinkedIn Developer Portal](https://www.linkedin.com/developers/)
2. Create a new app
3. Fill in app details:
   - **App name**: Your automation system name
   - **LinkedIn Page**: Your company page (create one if needed)
   - **Privacy policy URL**: Your privacy policy
   - **App logo**: Upload a logo
4. Navigate to **Auth** tab
5. Add redirect URLs:
   - For local: `http://localhost:3000/auth/linkedin/callback`
   - For production: `https://yourdomain.com/auth/linkedin/callback`
6. Copy **Client ID** and **Client Secret**
7. Navigate to **Products** tab
8. Request access to:
   - Sign In with LinkedIn
   - Share on LinkedIn (if available)

**Cost**: Free

#### 3. AI API Provider

**Purpose**: Generate AI-powered comments and content analysis

**Option A: Anthropic Claude (Recommended)**
1. Create account at [anthropic.com](https://www.anthropic.com)
2. Navigate to API Keys
3. Create new API key
4. Copy the key (starts with `sk-ant-`)

**Cost**: Pay-as-you-go (~$0.008 per 1K tokens for Claude 3.5 Sonnet)

**Option B: OpenAI GPT**
1. Create account at [platform.openai.com](https://platform.openai.com)
2. Navigate to API Keys
3. Create new API key
4. Copy the key (starts with `sk-`)

**Cost**: Pay-as-you-go (~$0.0015 per 1K tokens for GPT-3.5 Turbo)

#### 4. Redis (Included in Docker/Kubernetes)

For local development, install Redis locally:

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis
sudo systemctl enable redis
```

**macOS:**
```bash
brew install redis
brew services start redis
```

**Windows:**
Use Docker or WSL2

---

## Pre-Deployment Checklist

Before starting deployment, ensure you have:

- [ ] **Hardware**: Meets minimum requirements for chosen deployment method
- [ ] **Software**: All required software installed and verified
- [ ] **Supabase**: Project created, URLs and keys copied
- [ ] **LinkedIn App**: Created, credentials copied, redirect URIs configured
- [ ] **AI API**: Account created, API key obtained
- [ ] **Network**: Firewall rules configured (if applicable)
- [ ] **Domain**: DNS configured (for production deployments)
- [ ] **SSL Certificates**: Obtained (for production deployments)
- [ ] **Backup Strategy**: Planned and documented
- [ ] **Monitoring**: Strategy planned (optional but recommended)

---

## Deployment Methods

---

## Quick Start (Docker)

**Best for:** Quick setup, development, staging, small-scale production

**Pros:**
- Fast setup (15-30 minutes)
- Isolated environment
- Easy to scale agents
- Built-in monitoring with optional Prometheus/Grafana
- No complex dependencies

**Cons:**
- Not ideal for very large-scale production
- Requires Docker knowledge for troubleshooting

### Step 1: Clone Repository

```bash
# Clone the repository
git clone https://github.com/your-org/Social-Bot-LinkedIn-.git
cd Social-Bot-LinkedIn-

# Verify you're in the correct directory
ls -la  # Should see docker-compose.yml, Dockerfile, etc.
```

### Step 2: Generate Encryption Key

```bash
# Install cryptography if not already installed
pip install cryptography

# Generate encryption key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Copy the output - you'll need it in the next step
```

**Example output:**
```
vQ8kL9mN2pR5sT7uW0xY3zA6bC9dF2gH5jK8lM1nP4qS7tV0wX3yA6zB9cE2fG5h=
```

### Step 3: Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit the .env file
nano .env  # or use vim, code, etc.
```

**Required Variables** (fill these in):

```bash
# =============================================================================
# REQUIRED CONFIGURATION
# =============================================================================

# Supabase Configuration (from Supabase dashboard)
SUPABASE_URL=https://yourproject.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  # Service role key

# LinkedIn OAuth (from LinkedIn Developer Portal)
LINKEDIN_CLIENT_ID=78xxxxxxxxxxxxx
LINKEDIN_CLIENT_SECRET=AbCdEfGhIjKlMnOp
LINKEDIN_REDIRECT_URI=http://localhost:3000/auth/linkedin/callback

# Encryption Key (generated in Step 2)
ENCRYPTION_KEY=vQ8kL9mN2pR5sT7uW0xY3zA6bC9dF2gH5jK8lM1nP4qS7tV0wX3yA6zB9cE2fG5h=

# AI API Key (choose one or both)
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxxxxxx  # Recommended
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx  # Alternative or fallback

# =============================================================================
# DOCKER-SPECIFIC CONFIGURATION
# =============================================================================

# Redis Configuration (use these values for Docker)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# API Server
API_HOST=0.0.0.0
API_PORT=8000
ENVIRONMENT=production

# Frontend URL (update for production)
FRONTEND_URL=http://localhost:3000

# =============================================================================
# OPTIONAL CONFIGURATION
# =============================================================================

# Logging
LOG_LEVEL=INFO  # Use DEBUG for troubleshooting

# Token Monitor
ENABLE_TOKEN_MONITOR=true

# Sentry (for error tracking - optional)
# SENTRY_DSN=https://xxxx@xxxx.ingest.sentry.io/xxxx

# Rate Limiting (optional - defaults are safe)
# LINKEDIN_MAX_REQUESTS_PER_WINDOW=500
# LINKEDIN_RATE_LIMIT_WINDOW=900
```

**Save and close the file** (Ctrl+X, then Y, then Enter in nano)

### Step 4: Deploy with Docker Compose

#### Option A: Standard Deployment

```bash
# Deploy all services
./scripts/deploy.sh docker

# OR manually:
docker-compose up -d

# Wait for services to start (30-60 seconds)
sleep 60
```

#### Option B: Deployment with Monitoring

```bash
# Deploy with Prometheus and Grafana
docker-compose --profile monitoring up -d

# Wait for services to start
sleep 60
```

### Step 5: Verify Deployment

```bash
# Check service status
docker-compose ps

# Expected output - all services should be "Up"
#     Name                   State        Ports
# ------------------------------------------------------------
# redis                     Up           6379/tcp
# linkedin-app              Up           0.0.0.0:8080->8080/tcp
# account-manager           Up
# content-analyzer          Up
# interaction-agent         Up
# conversation-agent        Up
# safety-agent              Up

# Check logs
docker-compose logs -f linkedin-app

# Look for:
# - "System initialized successfully"
# - "Agents started: account_manager, content_analyzer, ..."
# - No error messages
```

### Step 6: Access Services

| Service | URL | Credentials |
|---------|-----|-------------|
| Web Dashboard | http://localhost:8080 | (To be configured) |
| Redis | localhost:6379 | (No password by default) |
| Prometheus* | http://localhost:9090 | None |
| Grafana* | http://localhost:3000 | admin / admin |

*Only if deployed with monitoring profile

### Step 7: Scale Agents (Optional)

```bash
# Scale content analyzer to 3 instances
docker-compose up -d --scale content-analyzer=3

# Scale multiple agents
docker-compose up -d --scale content-analyzer=3 --scale interaction-agent=5

# Verify scaling
docker-compose ps
```

### Step 8: Configure Agent Settings

Create or edit `config/config.json`:

```bash
# Create config directory if it doesn't exist
mkdir -p config

# Generate sample config
python3 -c "
import sys
sys.path.insert(0, 'src')
from config.config import SystemConfig
config = SystemConfig()
import json
with open('config/config.json', 'w') as f:
    json.dump(config.__dict__, f, indent=2, default=str)
print('Sample config created at config/config.json')
"
```

**Edit the configuration** based on your needs (see [Configuration Guide](#configuration-guide))

### Docker Management Commands

```bash
# View logs
docker-compose logs -f [service_name]  # Omit service_name for all logs

# Restart services
docker-compose restart

# Stop services
docker-compose stop

# Stop and remove containers
docker-compose down

# Stop and remove containers + volumes (WARNING: deletes data)
docker-compose down -v

# Update and redeploy
git pull
docker-compose build
docker-compose up -d

# Check resource usage
docker stats

# Execute command in container
docker-compose exec linkedin-app bash
```

### Docker Troubleshooting

**Services won't start:**
```bash
# Check logs for errors
docker-compose logs

# Verify .env file is correct
cat .env

# Rebuild containers
docker-compose build --no-cache
docker-compose up -d
```

**Port already in use:**
```bash
# Find what's using port 8080
sudo lsof -i :8080
# OR
sudo netstat -tuln | grep 8080

# Kill the process or change port in docker-compose.yml
```

**Out of disk space:**
```bash
# Clean up Docker
docker system prune -a --volumes

# Check disk usage
df -h
```

---

## Local Development

**Best for:** Development, testing, debugging, learning the system

**Pros:**
- Full control over environment
- Easy debugging
- Fast iteration
- No Docker overhead

**Cons:**
- More dependencies to manage
- Platform-specific issues
- No built-in isolation

### Step 1: Clone Repository

```bash
git clone https://github.com/your-org/Social-Bot-LinkedIn-.git
cd Social-Bot-LinkedIn-
```

### Step 2: Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate

# On Windows:
.\venv\Scripts\activate

# Verify Python version
python --version  # Should be 3.8+
```

### Step 3: Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# This will install:
# - Web framework (FastAPI, uvicorn)
# - Browser automation (playwright, selenium)
# - AI/ML libraries (openai, transformers, spacy, etc.)
# - Database (sqlalchemy, asyncpg)
# - Message queue (redis, celery)
# - Monitoring (prometheus-client, structlog)
# - Security (cryptography, passlib)
# And many more...

# Download NLP models
python -m spacy download en_core_web_sm

# Install Playwright browsers
playwright install chromium

# Install system dependencies for Playwright (Linux only)
# On Ubuntu/Debian:
sudo playwright install-deps chromium

# On other systems, follow Playwright's instructions
```

### Step 4: Set Up Redis

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis
sudo systemctl enable redis
redis-cli ping  # Should return PONG
```

**macOS:**
```bash
brew install redis
brew services start redis
redis-cli ping  # Should return PONG
```

**Windows:**
```bash
# Use WSL2 or Docker
docker run -d -p 6379:6379 redis:7-alpine
```

### Step 5: Configure Environment

```bash
# Copy example file
cp .env.example .env

# Generate encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Edit .env
nano .env
```

**Local Development .env:**

```bash
# Supabase
SUPABASE_URL=https://yourproject.supabase.co
SUPABASE_KEY=your-service-role-key

# LinkedIn OAuth
LINKEDIN_CLIENT_ID=your-client-id
LINKEDIN_CLIENT_SECRET=your-client-secret
LINKEDIN_REDIRECT_URI=http://localhost:3000/auth/linkedin/callback

# Encryption
ENCRYPTION_KEY=your-generated-key

# AI API
ANTHROPIC_API_KEY=sk-ant-your-key
# OPENAI_API_KEY=sk-your-key

# Redis (local)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# API Server
API_HOST=127.0.0.1
API_PORT=8000
ENVIRONMENT=development

# Logging
LOG_LEVEL=DEBUG  # More verbose for development

# Browser (for development)
LINKEDIN_HEADLESS=false  # See browser for debugging
LINKEDIN_BROWSER_TYPE=playwright
```

### Step 6: Create Configuration File

```bash
# Generate sample config
./scripts/deploy.sh config

# OR manually:
mkdir -p config
python -c "
import sys
sys.path.insert(0, 'src')
from config.config import SystemConfig
import json

config = SystemConfig()
# Customize for development
config.linkedin.likes_per_hour = 10  # Lower for testing
config.linkedin.headless = False  # See browser

with open('config/config.json', 'w') as f:
    json.dump(config.to_dict(), f, indent=2)
print('Config created at config/config.json')
"

# Edit config as needed
nano config/config.json
```

### Step 7: Validate Configuration

```bash
# Dry run to validate config
python main.py --dry-run

# Expected output:
# ✅ Configuration valid
# ✅ Redis connection successful
# ✅ Database connection successful
# ✅ All agents initialized
```

### Step 8: Run the System

```bash
# Standard run
python main.py --config config/config.json

# With debug logging
python main.py --config config/config.json --log-level DEBUG

# With web dashboard
python main.py --config config/config.json --web-dashboard

# Run specific agents only
python main.py --config config/config.json --agents account_manager,content_analysis

# Run with monitoring enabled
python main.py --config config/config.json --monitoring
```

### Step 9: Verify Deployment

```bash
# In another terminal, check Redis
redis-cli
127.0.0.1:6379> KEYS *
# Should see agent keys

# Check health
python -c "
import asyncio
import sys
sys.path.insert(0, 'src')
from infrastructure.health_check import health_check
asyncio.run(health_check())
"
```

### Local Development Commands

```bash
# Run tests
pytest tests/

# Run specific test file
pytest tests/unit/test_account_manager.py

# Run with coverage
pytest --cov=src tests/

# Format code
black src/ tests/
isort src/ tests/

# Lint code
flake8 src/ tests/
mypy src/

# Type checking
mypy src/

# Clean Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

### Local Development Troubleshooting

**Import errors:**
```bash
# Ensure virtual environment is activated
which python  # Should point to venv/bin/python

# Reinstall requirements
pip install -r requirements.txt --force-reinstall
```

**Redis connection failed:**
```bash
# Check Redis is running
redis-cli ping

# Check Redis logs (Linux)
sudo journalctl -u redis

# Restart Redis
sudo systemctl restart redis
```

**Playwright browser issues:**
```bash
# Reinstall browsers
playwright install chromium --force

# Install system dependencies (Linux)
sudo playwright install-deps
```

**Permission errors (Linux):**
```bash
# Add user to redis group
sudo usermod -aG redis $USER

# Logout and login again
```

---

## Production (Kubernetes)

**Best for:** Large-scale production, high availability, auto-scaling

**Pros:**
- Highly scalable
- Auto-healing
- Rolling updates
- Resource management
- Enterprise-ready

**Cons:**
- Complex setup
- Requires Kubernetes knowledge
- Higher resource overhead

### Prerequisites

- Kubernetes cluster (1.21+)
- kubectl configured
- Cluster admin access
- StorageClass for persistent volumes
- LoadBalancer or Ingress controller (for external access)

### Step 1: Prepare Cluster

```bash
# Verify cluster access
kubectl cluster-info

# Check available resources
kubectl top nodes

# Verify StorageClass
kubectl get storageclass

# Should see default StorageClass marked with (default)
```

### Step 2: Clone Repository

```bash
git clone https://github.com/your-org/Social-Bot-LinkedIn-.git
cd Social-Bot-LinkedIn-/deployment/kubernetes
```

### Step 3: Create Namespace

```bash
# Create namespace
kubectl apply -f namespace.yaml

# Verify
kubectl get namespaces | grep linkedin

# Expected output:
# linkedin-automation   Active   5s
```

### Step 4: Create Secrets

```bash
# Generate encryption key
ENCRYPTION_KEY=$(openssl rand -base64 32)

# Interactive secret creation
read -p "Enter your ANTHROPIC_API_KEY: " -s ANTHROPIC_API_KEY
echo
read -p "Enter your OPENAI_API_KEY (optional, press Enter to skip): " -s OPENAI_API_KEY
echo
read -p "Enter your SUPABASE_KEY: " -s SUPABASE_KEY
echo

# Create secrets
kubectl create secret generic linkedin-secrets \
  --from-literal=anthropic-api-key="$ANTHROPIC_API_KEY" \
  --from-literal=openai-api-key="${OPENAI_API_KEY:-none}" \
  --from-literal=encryption-key="$ENCRYPTION_KEY" \
  --from-literal=supabase-key="$SUPABASE_KEY" \
  -n linkedin-automation

# Verify (values should be hidden)
kubectl get secret linkedin-secrets -n linkedin-automation -o yaml
```

### Step 5: Configure ConfigMap

Edit `configmap.yaml` with your settings:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: linkedin-config
  namespace: linkedin-automation
data:
  # Supabase
  SUPABASE_URL: "https://yourproject.supabase.co"

  # LinkedIn OAuth
  LINKEDIN_CLIENT_ID: "your-client-id"
  LINKEDIN_CLIENT_SECRET: "your-client-secret"
  LINKEDIN_REDIRECT_URI: "https://yourdomain.com/auth/linkedin/callback"

  # Redis
  REDIS_HOST: "redis"
  REDIS_PORT: "6379"
  REDIS_DB: "0"

  # API Server
  API_HOST: "0.0.0.0"
  API_PORT: "8000"
  ENVIRONMENT: "production"

  # Logging
  LOG_LEVEL: "INFO"

  # Features
  ENABLE_TOKEN_MONITOR: "true"

  # LinkedIn Settings
  LINKEDIN_HEADLESS: "true"
  LINKEDIN_BROWSER_TYPE: "playwright"

  # Rate Limiting
  LINKEDIN_MAX_REQUESTS_PER_WINDOW: "500"
  LINKEDIN_RATE_LIMIT_WINDOW: "900"
```

Apply the ConfigMap:

```bash
kubectl apply -f configmap.yaml

# Verify
kubectl get configmap linkedin-config -n linkedin-automation
```

### Step 6: Deploy Redis

```bash
# Deploy Redis StatefulSet
kubectl apply -f redis.yaml

# Wait for Redis to be ready
kubectl wait --for=condition=ready pod -l app=redis -n linkedin-automation --timeout=300s

# Verify
kubectl get pods -n linkedin-automation | grep redis

# Test Redis connectivity
kubectl exec -it redis-0 -n linkedin-automation -- redis-cli ping
# Should return: PONG
```

### Step 7: Deploy Orchestrator

```bash
# Deploy orchestrator
kubectl apply -f orchestrator.yaml

# Wait for orchestrator
kubectl wait --for=condition=available deployment/linkedin-orchestrator -n linkedin-automation --timeout=300s

# Check logs
kubectl logs -f deployment/linkedin-orchestrator -n linkedin-automation

# Look for:
# - "Orchestrator initialized successfully"
# - "Connected to Redis"
# - No error messages
```

### Step 8: Deploy Agents

Before deploying, review and customize `agents.yaml` for your scale needs:

```yaml
# Example: Scale content-analyzer to 3 replicas
apiVersion: apps/v1
kind: Deployment
metadata:
  name: content-analyzer
  namespace: linkedin-automation
spec:
  replicas: 3  # Adjust based on load
  # ...
```

Deploy agents:

```bash
# Deploy all agents
kubectl apply -f agents.yaml

# Wait for agents to be ready
kubectl wait --for=condition=available deployment --all -n linkedin-automation --timeout=600s

# Verify all deployments
kubectl get deployments -n linkedin-automation

# Expected output:
# NAME                      READY   UP-TO-DATE   AVAILABLE
# linkedin-orchestrator     1/1     1            1
# account-manager           1/1     1            1
# content-analyzer          3/3     3            3
# interaction-agent         2/2     2            2
# conversation-agent        2/2     2            2
# safety-agent              1/1     1            1
```

### Step 9: Create Service & Ingress (Optional)

For external access, create a LoadBalancer service:

```yaml
# service-lb.yaml
apiVersion: v1
kind: Service
metadata:
  name: linkedin-orchestrator-lb
  namespace: linkedin-automation
spec:
  type: LoadBalancer
  selector:
    app: linkedin-orchestrator
  ports:
  - port: 80
    targetPort: 8080
    protocol: TCP
```

Apply:

```bash
kubectl apply -f service-lb.yaml

# Get external IP (may take a few minutes)
kubectl get svc linkedin-orchestrator-lb -n linkedin-automation -w

# Or use Ingress for more control (example with nginx-ingress)
```

### Step 10: Configure Horizontal Pod Autoscaler

```yaml
# hpa.yaml
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
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

Apply:

```bash
kubectl apply -f hpa.yaml

# Verify
kubectl get hpa -n linkedin-automation
```

### Kubernetes Management Commands

```bash
# View all resources
kubectl get all -n linkedin-automation

# View logs
kubectl logs -f deployment/linkedin-orchestrator -n linkedin-automation

# View logs for specific pod
kubectl logs -f <pod-name> -n linkedin-automation

# Execute command in pod
kubectl exec -it <pod-name> -n linkedin-automation -- bash

# Port forward for local access
kubectl port-forward service/linkedin-orchestrator 8080:80 -n linkedin-automation

# Scale deployment
kubectl scale deployment content-analyzer --replicas=5 -n linkedin-automation

# Update deployment (after image change)
kubectl rollout restart deployment/linkedin-orchestrator -n linkedin-automation

# Check rollout status
kubectl rollout status deployment/linkedin-orchestrator -n linkedin-automation

# View events
kubectl get events -n linkedin-automation --sort-by='.lastTimestamp'

# View resource usage
kubectl top pods -n linkedin-automation
kubectl top nodes

# Delete everything
kubectl delete namespace linkedin-automation
```

### Kubernetes Troubleshooting

**Pods not starting:**
```bash
# Describe pod for detailed info
kubectl describe pod <pod-name> -n linkedin-automation

# Check events
kubectl get events -n linkedin-automation

# Common issues:
# - ImagePullBackOff: Docker image not found
# - CrashLoopBackOff: Application crashing
# - Pending: Insufficient resources
```

**Configuration issues:**
```bash
# Verify secrets
kubectl get secret linkedin-secrets -n linkedin-automation -o yaml

# Verify configmap
kubectl get configmap linkedin-config -n linkedin-automation -o yaml

# Check environment variables in pod
kubectl exec -it <pod-name> -n linkedin-automation -- env | grep LINKEDIN
```

**Storage issues:**
```bash
# Check PVC status
kubectl get pvc -n linkedin-automation

# Describe PVC
kubectl describe pvc <pvc-name> -n linkedin-automation

# Check StorageClass
kubectl get storageclass
```

---

## Configuration Guide

The system uses multiple configuration sources:

1. **Environment Variables** (.env file or Kubernetes secrets)
2. **Configuration File** (config/config.json)
3. **Database** (runtime settings stored in Supabase)

### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SUPABASE_URL` | Yes | - | Supabase project URL |
| `SUPABASE_KEY` | Yes | - | Supabase service role key |
| `LINKEDIN_CLIENT_ID` | Yes | - | LinkedIn OAuth client ID |
| `LINKEDIN_CLIENT_SECRET` | Yes | - | LinkedIn OAuth client secret |
| `LINKEDIN_REDIRECT_URI` | Yes | - | OAuth redirect URI |
| `ENCRYPTION_KEY` | Yes | - | Fernet encryption key |
| `ANTHROPIC_API_KEY` | No* | - | Anthropic Claude API key |
| `OPENAI_API_KEY` | No* | - | OpenAI GPT API key |
| `REDIS_HOST` | Yes | localhost | Redis hostname |
| `REDIS_PORT` | No | 6379 | Redis port |
| `REDIS_PASSWORD` | No | - | Redis password |
| `REDIS_DB` | No | 0 | Redis database number |
| `API_HOST` | No | 0.0.0.0 | API server host |
| `API_PORT` | No | 8000 | API server port |
| `ENVIRONMENT` | No | development | Environment (development/production) |
| `LOG_LEVEL` | No | INFO | Logging level (DEBUG/INFO/WARNING/ERROR) |
| `FRONTEND_URL` | No | http://localhost:3000 | Frontend URL for CORS |
| `ENABLE_TOKEN_MONITOR` | No | true | Enable token usage monitoring |
| `SENTRY_DSN` | No | - | Sentry error tracking DSN |

*At least one AI API key (Anthropic or OpenAI) is required

### Configuration File Structure

Create `config/config.json`:

```json
{
  "redis": {
    "host": "localhost",
    "port": 6379,
    "password": null,
    "db": 0,
    "max_connections": 50,
    "socket_timeout": 5,
    "socket_connect_timeout": 5
  },

  "security": {
    "session_timeout_minutes": 120,
    "max_login_attempts": 5,
    "lockout_duration_minutes": 30,
    "require_2fa": false,
    "rate_limit_enabled": true,
    "max_requests_per_minute": 60
  },

  "linkedin": {
    "headless": true,
    "browser_type": "playwright",
    "user_agent_rotation": true,
    "proxy_enabled": false,

    "rate_limits": {
      "likes_per_hour": 30,
      "likes_per_day": 150,
      "like_cooldown_seconds": 10,

      "comments_per_hour": 10,
      "comments_per_day": 50,
      "comment_cooldown_seconds": 60,

      "shares_per_hour": 5,
      "shares_per_day": 20,
      "share_cooldown_seconds": 120,

      "follows_per_hour": 20,
      "follows_per_day": 100,
      "follow_cooldown_seconds": 30,

      "connections_per_hour": 10,
      "connections_per_day": 50,
      "connection_cooldown_seconds": 60,

      "messages_per_hour": 10,
      "messages_per_day": 50,
      "message_cooldown_seconds": 120
    },

    "timing": {
      "business_hours_start": 9,
      "business_hours_end": 18,
      "peak_hours": [10, 11, 14, 15],
      "weekend_activity_multiplier": 0.3,
      "random_delay_min_seconds": 2,
      "random_delay_max_seconds": 10
    },

    "interaction": {
      "priority_levels": 10,
      "max_retries": 3,
      "retry_delay_seconds": 300,
      "queue_check_interval_seconds": 5
    }
  },

  "content_analysis": {
    "model": "openai",
    "enable_embeddings": true,
    "embedding_model": "text-embedding-ada-002",

    "scoring": {
      "min_relevance_score": 0.5,
      "min_quality_score": 0.6,
      "min_engagement_probability": 0.4
    },

    "filters": {
      "target_industries": [
        "technology",
        "software",
        "artificial intelligence",
        "data science",
        "finance",
        "consulting"
      ],
      "target_keywords": [
        "AI",
        "machine learning",
        "innovation",
        "automation",
        "digital transformation",
        "leadership"
      ],
      "excluded_keywords": [
        "spam",
        "bitcoin",
        "crypto",
        "investment opportunity"
      ],
      "min_content_length": 50,
      "max_content_length": 3000
    },

    "nlp": {
      "spacy_model": "en_core_web_sm",
      "sentiment_threshold": -0.2,
      "enable_entity_extraction": true,
      "enable_topic_classification": true
    }
  },

  "conversation": {
    "model": "anthropic",
    "model_name": "claude-3-5-sonnet-20241022",
    "temperature": 0.7,
    "max_tokens": 150,

    "generation": {
      "min_confidence_score": 0.7,
      "generate_alternatives": true,
      "max_alternatives": 3,
      "diversity_threshold": 0.3
    },

    "styles": {
      "default": "professional",
      "available": [
        "professional",
        "casual",
        "friendly",
        "thought_leader",
        "technical",
        "inspirational",
        "analytical"
      ]
    },

    "tones": {
      "default": "positive",
      "available": [
        "positive",
        "neutral",
        "supportive",
        "inquisitive",
        "agreeable",
        "challenging"
      ]
    },

    "constraints": {
      "min_length": 20,
      "max_length": 300,
      "avoid_generic_phrases": true,
      "require_personalization": true
    }
  },

  "safety": {
    "bot_detection_threshold": 0.8,
    "rate_limit_buffer": 0.8,
    "action_threshold_per_hour": 100,
    "action_threshold_per_day": 500,
    "suspicious_activity_threshold": 0.8,
    "cooldown_duration_seconds": 300,
    "enable_captcha_detection": true,
    "enable_behavior_analysis": true
  },

  "monitoring": {
    "enable_prometheus": true,
    "prometheus_port": 9090,
    "enable_health_checks": true,
    "health_check_interval_seconds": 60,
    "enable_performance_tracking": true,
    "enable_error_tracking": true
  },

  "database": {
    "pool_size": 20,
    "max_overflow": 10,
    "pool_timeout": 30,
    "pool_recycle": 3600,
    "echo": false
  }
}
```

### Configuration Best Practices

1. **Start Conservative**: Use default rate limits and increase gradually
2. **Monitor First**: Run with monitoring enabled for first few days
3. **Test in Stages**: Test with 1-2 accounts before scaling
4. **Adjust Based on Results**: Tune based on LinkedIn's response
5. **Keep Backups**: Always backup working configurations

### Environment-Specific Configs

**Development:**
```json
{
  "linkedin": {
    "headless": false,
    "rate_limits": {
      "likes_per_hour": 5,
      "comments_per_hour": 2
    }
  },
  "safety": {
    "bot_detection_threshold": 0.5
  }
}
```

**Staging:**
```json
{
  "linkedin": {
    "headless": true,
    "rate_limits": {
      "likes_per_hour": 15,
      "comments_per_hour": 5
    }
  }
}
```

**Production:**
```json
{
  "linkedin": {
    "headless": true,
    "rate_limits": {
      "likes_per_hour": 30,
      "comments_per_hour": 10
    }
  },
  "safety": {
    "bot_detection_threshold": 0.9,
    "enable_behavior_analysis": true
  }
}
```

---

## Post-Deployment Verification

### Health Check Procedures

#### 1. System Health

```bash
# Docker
docker-compose ps
docker-compose exec linkedin-app python -c "
import asyncio
import sys
sys.path.insert(0, 'src')
from infrastructure.health_check import health_check
asyncio.run(health_check())
"

# Kubernetes
kubectl get pods -n linkedin-automation
kubectl exec -it deployment/linkedin-orchestrator -n linkedin-automation -- python -c "
import asyncio
from infrastructure.health_check import health_check
asyncio.run(health_check())
"

# Local
python -c "
import asyncio
import sys
sys.path.insert(0, 'src')
from infrastructure.health_check import health_check
asyncio.run(health_check())
"
```

#### 2. Redis Connectivity

```bash
# Docker
docker-compose exec redis redis-cli ping

# Kubernetes
kubectl exec -it redis-0 -n linkedin-automation -- redis-cli ping

# Local
redis-cli ping
```

#### 3. Database Connectivity

```bash
# Test Supabase connection
python -c "
import asyncio
from src.database.session import get_session

async def test():
    async with get_session() as session:
        result = await session.execute('SELECT 1')
        print('✅ Database connected')

asyncio.run(test())
"
```

#### 4. Agent Status

```bash
# Check agent health
redis-cli
> KEYS agent:*:health
> GET agent:account_manager:health
> GET agent:content_analyzer:health
```

#### 5. API Endpoints

```bash
# Health endpoint
curl http://localhost:8080/health

# Expected response:
# {"status": "healthy", "agents": [...], "timestamp": "..."}

# Readiness endpoint
curl http://localhost:8080/ready
```

### Functional Testing

#### Test 1: Add Test Account (Manual)

Use the web dashboard or API to add a test LinkedIn account and verify:
- [ ] Account successfully added
- [ ] Credentials encrypted in database
- [ ] Session created and stored
- [ ] Account appears in account list

#### Test 2: Content Analysis

```python
# Test content analyzer
import asyncio
from src.agents.core.content_analysis_agent import ContentAnalysisAgent

async def test():
    agent = ContentAnalysisAgent()
    await agent.initialize()

    result = await agent.analyze_content(
        content_text="Exciting developments in AI and machine learning...",
        content_type="post"
    )

    print(f"Relevance: {result.relevance_score}")
    print(f"Quality: {result.quality_score}")
    print(f"Sentiment: {result.sentiment_score}")

asyncio.run(test())
```

Expected:
- [ ] Content analyzed successfully
- [ ] Scores returned (0-1 range)
- [ ] Industries/topics identified

#### Test 3: Comment Generation

```python
# Test conversation agent
import asyncio
from src.agents.core.conversation_agent import ConversationAgent

async def test():
    agent = ConversationAgent()
    await agent.initialize()

    result = await agent.generate_comment(
        content_text="Just published an article on AI ethics...",
        content_author="John Doe",
        style="professional"
    )

    print(f"Generated: {result.comment_text}")
    print(f"Confidence: {result.confidence_score}")
## Quick Start (Development)

```bash
# 1. Start Backend
cd /path/to/linkedin-multi-agent-system
python src/api/main_simple_integrated.py

# 2. Start Frontend  
cd frontend-new
npm start

# 3. Access System
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

## Production Deployment

### Option 1: Docker Deployment (Recommended)

```dockerfile
# Dockerfile for backend
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN playwright install

COPY src/ ./src/
EXPOSE 8000
CMD ["python", "src/api/main_simple_integrated.py"]
```

```dockerfile  
# Dockerfile for frontend
FROM node:18-alpine

WORKDIR /app
COPY frontend-new/package*.json ./
RUN npm install

COPY frontend-new/ .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - REDIS_URL=${REDIS_URL}
    volumes:
      - ./data:/app/data

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
```

### Option 2: Manual Server Deployment

#### Backend Setup:
```bash
# Install Python dependencies
pip install fastapi uvicorn playwright openai beautifulsoup4 aioredis

# Install browser
playwright install

# Set environment variables
export OPENAI_API_KEY=your_openai_api_key
export REDIS_URL=redis://localhost:6379

# Run with production server
uvicorn src.api.main_simple_integrated:app --host 0.0.0.0 --port 8000 --workers 4
```

#### Frontend Setup:
```bash
cd frontend-new

# Install dependencies
npm install

# Build for production
npm run build

# Serve with production server
npm install -g serve
serve -s build -l 3000
```

### Option 3: Kubernetes Deployment (Production Scale)

For production-scale deployment, use the pre-configured Kubernetes manifests in `deployment/kubernetes/`:

```bash
# 1. Create namespace
kubectl apply -f deployment/kubernetes/namespace.yaml

# 2. Create ConfigMap and Secrets (edit with your values first)
kubectl apply -f deployment/kubernetes/configmap.yaml

# 3. Deploy Redis
kubectl apply -f deployment/kubernetes/redis.yaml

# 4. Deploy orchestrator
kubectl apply -f deployment/kubernetes/orchestrator.yaml

# 5. Deploy agents (Content Analyzer, Interaction Agent, etc.)
kubectl apply -f deployment/kubernetes/agents.yaml

# 6. Verify deployment
kubectl get pods -n linkedin-automation

# 7. Check logs
kubectl logs -f deployment/linkedin-orchestrator -n linkedin-automation
```

**Agent Scaling (agents.yaml):**
| Agent | Default Replicas | Memory |
|-------|------------------|--------|
| Account Manager | 1 | 512Mi-1Gi |
| Content Analyzer | 2 | 1Gi-2Gi |
| Interaction Agent | 2 | 512Mi-1Gi |
| Conversation Agent | 2 | 1Gi-2Gi |
| Safety Agent | 1 | 256Mi-512Mi |

**Using Production Scripts:**
```bash
# Automated deployment with validation
./scripts/deploy.sh kubernetes

# Or use the production deployment script
./scripts/deploy_production.sh
```

## Configuration

### Environment Variables:
```bash
# Required
OPENAI_API_KEY=sk-your-openai-api-key-here

# Optional
REDIS_URL=redis://localhost:6379
LOG_LEVEL=INFO
MAX_DAILY_POSTS=50
COMMENT_PROBABILITY=0.4
HEADLESS_BROWSER=true
```

### Backend Configuration:
Edit `src/api/main_simple_integrated.py`:
```python
# Modify these settings for production
automation_config = {
    "enabled": False,  # Start disabled for safety
    "max_posts_per_day": 50,  # Adjust based on your needs
    "comment_probability": 0.4,  # 40% chance to comment
    "reply_probability": 0.2,   # 20% chance to reply
    "min_delay_minutes": 5,     # Minimum delay between actions
    "max_delay_minutes": 30,    # Maximum delay between actions
    "risk_management_enabled": True,  # Keep enabled
    "ai_enabled": True,  # Enable once OpenAI key is set
}
```

### Supabase Database Configuration

This project uses Supabase as the primary database via the Supavisor connection pooler.

**Connection String Format (Transaction Mode - Port 6543):**
```
postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-1-[REGION].pooler.supabase.com:6543/postgres
```

**Finding Your Supabase Region:**
1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Select your project → Settings → Database
3. Find your region (e.g., `ap-southeast-2`, `us-east-1`, `eu-west-1`)
4. Copy the **Transaction mode** pooler URL (port 6543)

**Example Connection Strings by Region:**
```bash
# Australia (ap-southeast-2)
SUPABASE_DB_URL=postgresql://postgres.yourproject:password@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres

# US East (us-east-1)
SUPABASE_DB_URL=postgresql://postgres.yourproject:password@aws-1-us-east-1.pooler.supabase.com:6543/postgres

# Europe (eu-west-1)
SUPABASE_DB_URL=postgresql://postgres.yourproject:password@aws-1-eu-west-1.pooler.supabase.com:6543/postgres
```

**Required in `.env`:**
```bash
SUPABASE_DB_URL=postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-1-[REGION].pooler.supabase.com:6543/postgres
```

**SQLAlchemy Configuration (already configured in `src/database/session.py`):**
```python
# Required for Supabase pooler - disables prepared statement caching
connect_args = {
    "statement_cache_size": 0,
    "prepared_statement_cache_size": 0,
}
```

**Test Connection:**
```python
import asyncio
import asyncpg

async def test():
    conn = await asyncpg.connect(
        "YOUR_SUPABASE_DB_URL",
        statement_cache_size=0
    )
    result = await conn.fetchval('SELECT NOW()')
    print(f'✅ Connected: {result}')
    await conn.close()

asyncio.run(test())
```

Expected:
- [ ] Comment generated successfully
- [ ] Relevant to content
- [ ] Meets quality thresholds

### Performance Benchmarks

After deployment, verify performance meets expectations:

| Metric | Target | Acceptance Criteria |
|--------|--------|---------------------|
| System startup time | < 60 seconds | All agents initialized |
| Agent response time | < 2 seconds | For standard requests |
| Content analysis time | < 5 seconds | Per post |
| Comment generation time | < 10 seconds | Per comment |
| Database query time | < 100ms | For simple queries |
| Redis operations | < 10ms | For gets/sets |
| Memory usage | < 2GB | Per agent container |
| CPU usage | < 50% | At steady state |

### Monitoring Setup Verification

If monitoring is enabled, verify:

- [ ] Prometheus accessible at http://localhost:9090
- [ ] Grafana accessible at http://localhost:3000
- [ ] Metrics being collected (check Prometheus targets)
- [ ] Dashboards displaying data in Grafana
- [ ] Alerts configured (if applicable)

---

## Security Hardening

### Production Security Checklist

#### Infrastructure Security

- [ ] **Use HTTPS only**: Configure SSL/TLS certificates
- [ ] **Firewall rules**: Restrict access to necessary ports only
- [ ] **Network segmentation**: Isolate database, Redis, and application
- [ ] **VPN/Private network**: Run in private network where possible
- [ ] **DDoS protection**: Use CloudFlare or similar
- [ ] **Regular updates**: Keep all software updated

#### Application Security

- [ ] **Strong encryption keys**: Use 256-bit keys minimum
- [ ] **Rotate secrets**: Implement secret rotation policy
- [ ] **Secure storage**: Never commit secrets to git
- [ ] **Rate limiting**: Enable application-level rate limiting
- [ ] **Input validation**: Validate all user inputs
- [ ] **SQL injection protection**: Use parameterized queries
- [ ] **XSS protection**: Sanitize outputs
- [ ] **CSRF protection**: Implement CSRF tokens

#### LinkedIn Account Security

- [ ] **2FA enabled**: Enable on all LinkedIn accounts
- [ ] **Unique passwords**: Use different password per account
- [ ] **Password rotation**: Rotate passwords every 90 days
- [ ] **Monitor logins**: Watch for suspicious login attempts
- [ ] **IP whitelisting**: Use consistent IPs where possible
- [ ] **Proxy rotation**: Use residential proxies for anonymity

#### Database Security

- [ ] **Row-level security**: Enable RLS in Supabase
- [ ] **Encryption at rest**: Enabled by default in Supabase
- [ ] **Encryption in transit**: Use SSL connections
- [ ] **Backup encryption**: Encrypt backups
- [ ] **Access control**: Restrict database access
- [ ] **Audit logging**: Enable database audit logs

#### Redis Security

- [ ] **Password protection**: Set Redis password
- [ ] **Disable dangerous commands**: Disable FLUSHALL, KEYS, etc.
- [ ] **Bind to localhost**: Only expose to trusted networks
- [ ] **Use Redis ACLs**: Configure user permissions (Redis 6+)
- [ ] **Enable persistence**: Configure RDB/AOF for data durability

### Kubernetes-Specific Security

```yaml
# Security best practices for pods
apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 1000
    seccompProfile:
      type: RuntimeDefault

  containers:
  - name: app
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL

    resources:
      limits:
        memory: "2Gi"
        cpu: "1000m"
      requests:
        memory: "1Gi"
        cpu: "500m"
```

Apply network policies:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: linkedin-network-policy
  namespace: linkedin-automation
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress

  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: linkedin-automation

  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: linkedin-automation
  - to:  # Allow external API calls
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 443
```

### Secrets Management

**Never commit these to git:**
- API keys
- Passwords
- Encryption keys
- OAuth secrets
- Database credentials

**Use:**
- Environment variables
- Kubernetes secrets
- Secret management services (AWS Secrets Manager, HashiCorp Vault)
- Encrypted env files

**Example .gitignore:**
```
.env
.env.local
.env.production
config/secrets.json
*.pem
*.key
*.cert
```

---

## Monitoring & Maintenance

### Daily Checks

- [ ] Check agent health status
- [ ] Review error logs for anomalies
- [ ] Monitor rate limit consumption
- [ ] Check account status (not locked/suspended)
- [ ] Verify interactions completing successfully

### Weekly Maintenance

- [ ] Review performance metrics
- [ ] Analyze success/failure rates
- [ ] Check disk space usage
- [ ] Review and archive old logs
- [ ] Update configuration based on performance
- [ ] Review security alerts

### Monthly Maintenance

- [ ] Update dependencies
- [ ] Review and optimize database
- [ ] Backup configuration and data
- [ ] Security audit
- [ ] Performance tuning
- [ ] Review and update documentation

### Monitoring Dashboards

#### Prometheus Queries

```promql
# Agent health
up{job="linkedin-agents"}

# Request rate
rate(linkedin_interactions_total[5m])

# Error rate
rate(linkedin_errors_total[5m]) / rate(linkedin_interactions_total[5m])

# Queue depth
linkedin_queue_depth

# Response time
histogram_quantile(0.95, rate(linkedin_response_time_bucket[5m]))
```

#### Grafana Dashboard Panels

1. **System Overview**
   - Total agents running
   - System uptime
   - Error rate
   - Request rate

2. **Agent Performance**
   - Agent health status
   - Message processing rate
   - Queue depths
   - Response times

3. **LinkedIn Metrics**
   - Interactions by type
   - Success/failure rates
   - Rate limit usage
   - Account status

4. **Infrastructure**
   - CPU usage
   - Memory usage
   - Disk I/O
   - Network traffic

### Log Management

#### Log Locations

**Docker:**
```bash
docker-compose logs linkedin-app > logs/app.log
docker-compose logs content-analyzer > logs/content-analyzer.log
```

**Kubernetes:**
```bash
kubectl logs deployment/linkedin-orchestrator -n linkedin-automation > logs/orchestrator.log
```

**Local:**
```bash
# Logs are written to stdout and logs/ directory
tail -f logs/linkedin-automation.log
```

#### Log Rotation

Configure log rotation to prevent disk space issues:

```bash
# /etc/logrotate.d/linkedin-automation
/var/log/linkedin-automation/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 app app
    sharedscripts
    postrotate
        docker-compose restart linkedin-app
    endscript
}
```

#### Centralized Logging (Optional)

Consider using ELK Stack or similar:

```yaml
# docker-compose.yml addition
services:
  elasticsearch:
    image: elasticsearch:8.5.0
    environment:
      - discovery.type=single-node
    volumes:
      - es_data:/usr/share/elasticsearch/data

  kibana:
    image: kibana:8.5.0
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch

  filebeat:
    image: elastic/filebeat:8.5.0
    volumes:
      - ./filebeat.yml:/usr/share/filebeat/filebeat.yml
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
    depends_on:
      - elasticsearch
```

### Backup Strategy

#### What to Backup

1. **Database** (Supabase handles this automatically)
   - Supabase provides automatic daily backups
   - Can trigger manual backups via dashboard
   - Consider exporting critical tables weekly

2. **Configuration Files**
   ```bash
   # Backup script
   tar -czf backup-$(date +%Y%m%d).tar.gz \
     .env \
     config/ \
     deployment/
   ```

3. **Redis Data** (if persistence enabled)
   ```bash
   # Redis backup
   redis-cli SAVE
   cp /var/lib/redis/dump.rdb backup/dump-$(date +%Y%m%d).rdb
   ```

4. **Logs** (for audit purposes)
   ```bash
   # Archive old logs
   tar -czf logs-$(date +%Y%m).tar.gz logs/
   mv logs-$(date +%Y%m).tar.gz archive/
   ```

#### Backup Schedule

- **Configuration**: After every change
- **Database**: Daily (automated by Supabase)
- **Redis**: Daily (if using persistence)
- **Logs**: Weekly
- **Full system**: Weekly

#### Restore Procedures

**Configuration:**
```bash
tar -xzf backup-20250101.tar.gz
cp .env.backup .env
cp -r config.backup/ config/
```

**Database:**
Use Supabase dashboard to restore from snapshot

**Redis:**
```bash
cp backup/dump-20250101.rdb /var/lib/redis/dump.rdb
redis-cli SHUTDOWN SAVE
redis-server
```

---

## Troubleshooting

### Common Issues

#### Issue: Services won't start

**Symptoms:**
- Containers exit immediately
- Agents fail to initialize
- Connection errors

**Diagnosis:**
```bash
# Check logs
docker-compose logs
kubectl logs <pod-name> -n linkedin-automation

# Common errors:
# - "Connection refused" → Service not running
# - "Authentication failed" → Wrong credentials
# - "Module not found" → Missing dependencies
```

**Solutions:**
1. Verify environment variables
2. Check Redis/database connectivity
3. Verify all required secrets exist
4. Check firewall/network rules
5. Review resource limits

#### Issue: High memory usage

**Symptoms:**
- OOM (Out of Memory) kills
- Slow performance
- Container restarts

**Diagnosis:**
```bash
# Check memory usage
docker stats
kubectl top pods -n linkedin-automation

# Check memory limits
docker-compose config
kubectl describe pod <pod-name> -n linkedin-automation
```

**Solutions:**
1. Increase memory limits
2. Reduce agent instances
3. Enable garbage collection tuning
4. Review for memory leaks
5. Consider using local models instead of API calls (reduces memory for caching)

#### Issue: Rate limiting triggered

**Symptoms:**
- Many "rate limited" errors
- Interactions queued but not executing
- Cooldown messages in logs

**Diagnosis:**
```bash
# Check rate limit status
redis-cli
> KEYS rate_limit:*
> GET rate_limit:account:123:likes

# Check safety agent logs
docker-compose logs safety-agent
```

**Solutions:**
1. Reduce rate limits in config
2. Add more accounts for rotation
3. Increase cooldown periods
4. Review LinkedIn's current limits
5. Check if account is flagged/restricted

#### Issue: LinkedIn login failures

**Symptoms:**
- "Authentication failed" errors
- Accounts marked as inactive
- CAPTCHA errors

**Diagnosis:**
```bash
# Check account status
redis-cli
> GET account:123:status

# Check logs for specific error
docker-compose logs account-manager | grep -i "auth"
```

**Solutions:**
1. Verify credentials are correct
2. Check if 2FA is enabled (handle separately)
3. Check for CAPTCHA challenges
4. Try logging in manually to verify account status
5. Use proxies to avoid IP-based blocking
6. Enable non-headless mode to debug browser issues

#### Issue: AI comment generation failing

**Symptoms:**
- "API error" messages
- Empty comments generated
- High API costs

**Diagnosis:**
```bash
# Check API key validity
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json"

# Check conversation agent logs
docker-compose logs conversation-agent
```

**Solutions:**
1. Verify API key is valid and has credits
2. Check API rate limits
3. Switch to fallback provider (OpenAI ↔ Anthropic)
4. Reduce generation frequency
5. Check prompt templates for issues

#### Issue: Database connection errors

**Symptoms:**
- "Connection refused"
- "Too many connections"
- "SSL error"

**Diagnosis:**
```bash
# Test connection
psql "postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres"

# Check connection pool
docker-compose exec linkedin-app python -c "
from src.database.session import engine
print(engine.pool.status())
"
```

**Solutions:**
1. Verify SUPABASE_URL and SUPABASE_KEY
2. Check Supabase project status
3. Verify connection pooler is enabled
4. Increase pool size if needed
5. Check network connectivity
6. Use transaction mode for pooler (required for asyncpg)

### Debug Mode

Enable debug mode for detailed logging:

```bash
# Docker
docker-compose down
# Edit .env: LOG_LEVEL=DEBUG
docker-compose up

# Local
python main.py --log-level DEBUG

# Kubernetes
kubectl edit configmap linkedin-config -n linkedin-automation
# Change LOG_LEVEL to DEBUG
kubectl rollout restart deployment --all -n linkedin-automation
```

### Health Check Script

Create `scripts/health-check.sh`:

```bash
#!/bin/bash

echo "=== LinkedIn Automation Health Check ==="
echo

# Check Redis
echo -n "Redis: "
if redis-cli ping &> /dev/null; then
    echo "✅ Healthy"
else
    echo "❌ Not responding"
fi

# Check Database
echo -n "Database: "
if python -c "
import asyncio
from src.database.session import get_session
async def test():
    async with get_session() as session:
        await session.execute('SELECT 1')
asyncio.run(test())
" &> /dev/null; then
    echo "✅ Healthy"
else
    echo "❌ Connection failed"
fi

# Check Agents
echo
echo "Agent Status:"
redis-cli --raw KEYS 'agent:*:health' | while read key; do
    agent=$(echo $key | cut -d: -f2)
    status=$(redis-cli GET $key)
    echo "  $agent: $status"
done

echo
echo "=== End Health Check ==="
```

Run it:
```bash
chmod +x scripts/health-check.sh
./scripts/health-check.sh
```

---

## FAQ

### General Questions

**Q: What's the recommended deployment method?**
A: For production, use Kubernetes. For development or small-scale use, Docker is simpler.

**Q: How many LinkedIn accounts can the system handle?**
A: With proper scaling, 100+ accounts. Start with 5-10 and scale based on performance.

**Q: What are the ongoing costs?**
A: Main costs are:
- Supabase: $0-25/month (free tier available)
- AI API: $20-200/month depending on usage
- Infrastructure: Varies by provider (AWS/GKE/etc.)

**Q: Is this against LinkedIn's Terms of Service?**
A: Automation may violate LinkedIn's ToS. Use at your own risk. This is for educational purposes.

**Q: How much does it cost to run the AI APIs?**
A: Approximately:
- Anthropic Claude: ~$0.008 per 1K tokens
- OpenAI GPT-3.5: ~$0.0015 per 1K tokens
- Typical comment: 100-200 tokens
- 1000 comments/day ≈ $1-8/day

### Technical Questions

**Q: Can I use SQLite instead of Supabase?**
A: Yes for testing, but Supabase/PostgreSQL is required for production (better concurrent access).

**Q: Can I run without Redis?**
A: No, Redis is required for agent communication and state management.

**Q: What browsers are supported?**
A: Playwright (Chromium) is primary, Selenium (Chrome/Firefox) as fallback.

**Q: Can I use local AI models instead of API?**
A: Partially. The code supports local models but requires significant setup and resources.

**Q: How do I add custom agents?**
A: Inherit from BaseAgent, implement required methods, add to agent registry. See docs/agent-development.md

**Q: Can I run multiple instances for high availability?**
A: Yes, in Kubernetes with proper state management. Redis handles distributed coordination.

### Troubleshooting Questions

**Q: Why are interactions not executing?**
A: Check:
1. Agent health status
2. Rate limits not exceeded
3. Accounts not locked
4. Queue has items
5. Safety agent not blocking

**Q: Why is memory usage so high?**
A: Common causes:
1. Too many browser instances
2. Large ML models loaded
3. Memory leaks (restart agents)
4. Insufficient garbage collection

**Q: How do I reset the system?**
A:
```bash
# Docker
docker-compose down -v
docker-compose up -d

# Kubernetes
kubectl delete namespace linkedin-automation
# Redeploy

# This will delete all data!
```

---

## Getting Help

### Documentation

- **Main README**: [README.md](README.md)
- **API Documentation**: [docs/api.md](docs/api.md) (if available)
- **Agent Development**: [docs/agents.md](docs/agents.md) (if available)
- **Configuration Reference**: This guide, Configuration section

### Support Channels

- **GitHub Issues**: Report bugs and request features
- **GitHub Discussions**: Ask questions and share ideas
- **Email Support**: support@example.com (if available)

### Logs to Provide When Seeking Help

When reporting issues, include:

1. **System Information**
   ```bash
   # Docker version
   docker --version
   docker-compose --version

   # Kubernetes version
   kubectl version

   # OS information
   uname -a
   ```

2. **Configuration** (sanitized - remove secrets!)
   ```bash
   # Environment variables (remove sensitive values)
   env | grep -E "(REDIS|LOG|LINKEDIN)" | sed 's/=.*/=***/'

   # Config file (remove secrets)
   cat config/config.json
   ```

3. **Logs**
   ```bash
   # Docker
   docker-compose logs --tail=100

   # Kubernetes
   kubectl logs --tail=100 deployment/linkedin-orchestrator -n linkedin-automation
   ```

4. **Health Status**
   ```bash
   ./scripts/health-check.sh
   ```

### Before Reporting a Bug

- [ ] Check this troubleshooting guide
- [ ] Search existing GitHub issues
- [ ] Verify configuration is correct
- [ ] Check logs for error messages
- [ ] Try with debug logging enabled
- [ ] Test with minimal configuration
- [ ] Verify external services (Supabase, LinkedIn, AI APIs) are working

---

## Appendix

### Deployment Decision Matrix

| Factor | Docker | Local | Kubernetes |
|--------|--------|-------|------------|
| Setup time | 15-30 min | 20-40 min | 30-60 min |
| Complexity | Low | Medium | High |
| Scalability | Medium | Low | High |
| Resource usage | Medium | Low | High |
| Best for | Dev/Small prod | Development | Large prod |
| HA support | No | No | Yes |
| Auto-scaling | Limited | No | Yes |
| Monitoring | Built-in | Manual | Built-in |
| Cost | Low | Lowest | Highest |

### Resource Planning

**For 10 LinkedIn accounts:**
- CPU: 4 cores
- RAM: 8 GB
- Storage: 50 GB
- Estimated monthly cost: $50-100 (cloud) + API costs

**For 50 LinkedIn accounts:**
- CPU: 8-16 cores
- RAM: 16-32 GB
- Storage: 100 GB
- Estimated monthly cost: $200-400 (cloud) + API costs

**For 100+ LinkedIn accounts:**
- CPU: 16+ cores (distributed)
- RAM: 32+ GB (distributed)
- Storage: 200+ GB
- Estimated monthly cost: $500+ (cloud) + API costs

### Port Reference

| Service | Port | Purpose |
|---------|------|---------|
| Web Dashboard | 8080 | Main application UI |
| API Server | 8000 | REST API |
| Redis | 6379 | Message queue & cache |
| Prometheus | 9090 | Metrics collection |
| Grafana | 3000 | Monitoring dashboards |
| Database | 5432 | PostgreSQL (Supabase) |

### Glossary

- **Agent**: Autonomous component responsible for specific tasks
- **Orchestrator**: Coordinates agent lifecycle and communication
- **Message Queue**: Redis-backed queue for inter-agent communication
- **State Manager**: Distributed state storage with versioning
- **Rate Limiting**: Restricting action frequency to avoid detection
- **Headless Browser**: Browser automation without GUI
- **Embeddings**: Vector representations of text for similarity matching
- **NLP**: Natural Language Processing
- **HPA**: Horizontal Pod Autoscaler (Kubernetes)
- **PVC**: Persistent Volume Claim (Kubernetes)

---

## Conclusion

You should now have a comprehensive understanding of how to deploy the LinkedIn Multi-Agent Automation System in various environments. Remember:

1. **Start small**: Deploy locally or with Docker first
2. **Test thoroughly**: Verify each component before production
3. **Monitor actively**: Watch metrics and logs closely
4. **Scale gradually**: Increase load incrementally
5. **Stay compliant**: Respect LinkedIn's ToS and rate limits

For additional help, consult the troubleshooting section or reach out via GitHub issues.

**Happy Automating!** 🚀

---

*Last updated: December 26, 2025*
*Version: 1.0*
*Maintained by: Development Team*
## System Requirements

### Minimum Requirements:
- **CPU:** 2 cores
- **RAM:** 4GB
- **Storage:** 10GB free space
- **OS:** Linux/macOS/Windows
- **Python:** 3.9+
- **Node.js:** 16+

### Recommended for Production:
- **CPU:** 4+ cores
- **RAM:** 8GB+
- **Storage:** 50GB+ SSD
- **OS:** Ubuntu 20.04 LTS or CentOS 8
- **Network:** Stable internet connection

## Initial Setup Steps

### 1. Add LinkedIn Accounts
```bash
curl -X POST "http://localhost:8000/api/accounts" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-linkedin-email@example.com",
    "password": "your-password",
    "display_name": "Account 1",
    "max_daily_interactions": 50
  }'
```

### 2. Add WhatsApp Groups
```bash
curl -X POST "http://localhost:8000/api/whatsapp/groups" \
  -H "Content-Type: application/json" \
  -d '{
    "group_name": "Tech Professionals",
    "keywords": ["technology", "startup", "AI"]
  }'
```

### 3. Configure Automation
```bash
curl -X PUT "http://localhost:8000/api/automation/config" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "ai_enabled": true,
    "openai_api_key": "your-api-key",
    "max_posts_per_day": 30,
    "comment_probability": 0.4
  }'
```

### 4. Start Automation
```bash
curl -X POST "http://localhost:8000/api/automation/start"
```

## Campaign API Deployment

The Campaign API provides endpoints for managing LinkedIn engagement campaigns with idempotency support.

### 1. Run Database Schema in Supabase

Execute the following SQL in Supabase SQL Editor:

```sql
-- Campaign Status Enum
CREATE TYPE campaign_status AS ENUM (
    'draft', 'scheduled', 'running', 'paused', 'completed', 'failed', 'cancelled'
);

-- Campaigns Table
CREATE TABLE campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status campaign_status NOT NULL DEFAULT 'draft',
    target_urls JSONB NOT NULL DEFAULT '[]'::jsonb,
    account_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    actions JSONB NOT NULL DEFAULT '{"like": true, "comment": false}'::jsonb,
    priority INTEGER NOT NULL DEFAULT 1 CHECK (priority BETWEEN 1 AND 3),
    scheduled_start_at TIMESTAMPTZ,
    scheduled_end_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    total_tasks INTEGER NOT NULL DEFAULT 0,
    completed_tasks INTEGER NOT NULL DEFAULT 0,
    failed_tasks INTEGER NOT NULL DEFAULT 0,
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Campaign Tasks Table
CREATE TABLE campaign_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    orchestrator_task_id VARCHAR(255) NOT NULL,
    target_url TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    result JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    UNIQUE(campaign_id, orchestrator_task_id)
);

-- Idempotency Keys Table
CREATE TABLE idempotency_keys (
    key VARCHAR(255) PRIMARY KEY,
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID,
    response_code INTEGER,
    response_body JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '24 hours')
);

-- Indexes
CREATE INDEX idx_campaigns_status ON campaigns(status) WHERE deleted_at IS NULL;
CREATE INDEX idx_campaigns_created ON campaigns(created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX idx_campaign_tasks_campaign ON campaign_tasks(campaign_id);
CREATE INDEX idx_campaign_tasks_status ON campaign_tasks(status);
CREATE INDEX idx_idempotency_expires ON idempotency_keys(expires_at);
```

### 2. Start API Server
```bash
python -m uvicorn src.api.main:app --reload --port 8000
```

### 3. Campaign API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/campaigns` | Create campaign |
| GET | `/api/v1/campaigns` | List campaigns |
| GET | `/api/v1/campaigns/{id}` | Get campaign |
| POST | `/api/v1/campaigns/{id}/start` | Start campaign |
| POST | `/api/v1/campaigns/{id}/pause` | Pause campaign |
| GET | `/api/v1/campaigns/{id}/status` | Get progress |

### 4. Test Campaign Endpoints

```bash
# Create a campaign (requires X-Idempotency-Key header)
curl -X POST http://localhost:8000/api/v1/campaigns \
  -H "Content-Type: application/json" \
  -H "X-Idempotency-Key: $(uuidgen)" \
  -d '{
    "name": "Test Campaign",
    "target_urls": ["https://linkedin.com/posts/example-123"],
    "account_ids": ["your-account-uuid"],
    "actions": {"like": true, "comment": false}
  }'

# List all campaigns
curl http://localhost:8000/api/v1/campaigns

# Start a campaign
curl -X POST "http://localhost:8000/api/v1/campaigns/<campaign-id>/start" \
  -H "X-Idempotency-Key: $(uuidgen)"

# Get campaign status
curl http://localhost:8000/api/v1/campaigns/<campaign-id>/status
```

## Monitoring & Maintenance

### Health Checks:
```bash
# System health
curl http://localhost:8000/api/health

# Detailed status
curl http://localhost:8000/api/status

# Account metrics
curl http://localhost:8000/api/metrics/accounts
```

### Log Monitoring:
```bash
# View backend logs
tail -f /var/log/linkedin-automation/backend.log

# View access logs  
tail -f /var/log/linkedin-automation/access.log
```

### Backup Procedures:
```bash
# Backup account data
cp -r data/ backup/data-$(date +%Y%m%d)/

# Backup configuration
cp src/api/main_simple_integrated.py backup/config-$(date +%Y%m%d).py
```

## Troubleshooting

### Common Issues:

#### 1. Browser Not Found
```bash
# Solution: Install Playwright browsers
playwright install
```

#### 2. LinkedIn Login Fails
- Check account credentials
- Verify LinkedIn account is not locked
- Check for 2FA requirements
- Review LinkedIn rate limits

#### 3. WhatsApp Web Connection Issues
- Ensure WhatsApp Web is accessible
- Check browser permissions
- Verify QR code scanning

#### 4. API Errors
```bash
# Check service status
curl http://localhost:8000/api/health

# View logs for errors
tail -f logs/app.log
```

#### 5. Supabase Connection Issues

**Error: "Tenant or user not found"**
- **Cause:** Wrong region in connection string
- **Solution:** Check your Supabase project region in Dashboard → Settings → Database
- Use the correct region format: `aws-1-[REGION].pooler.supabase.com`

**Error: "prepared statement already exists"**
- **Cause:** Missing statement cache configuration for asyncpg
- **Solution:** Ensure `src/database/session.py` has:
```python
connect_args = {
    "statement_cache_size": 0,
    "prepared_statement_cache_size": 0,
}
```

**Error: "connection refused" on port 5432**
- **Cause:** Using direct connection instead of pooler
- **Solution:** Use port `6543` (transaction mode pooler), not `5432`

**Test your connection:**
```bash
python -c "
import asyncio
import asyncpg
async def test():
    conn = await asyncpg.connect('YOUR_SUPABASE_DB_URL', statement_cache_size=0)
    print(await conn.fetchval('SELECT NOW()'))
    await conn.close()
asyncio.run(test())
"
```

### Performance Optimization:

#### 1. Database Optimization:
- Use Redis for caching
- Index frequently queried fields
- Implement connection pooling

#### 2. Memory Management:
- Monitor browser memory usage
- Implement browser recycling
- Use headless mode in production

#### 3. Network Optimization:
- Use CDN for static assets
- Enable gzip compression
- Implement request caching

## Security Best Practices

### 1. Account Security:
- Use strong, unique passwords
- Enable 2FA where possible
- Rotate credentials regularly
- Monitor for suspicious activity

### 2. API Security:
- Implement rate limiting
- Use HTTPS in production
- Validate all input data
- Log security events

### 3. Browser Security:
- Run browsers in sandboxed mode
- Use clean browser profiles
- Monitor for detection

## Scaling Considerations

### Horizontal Scaling:
```yaml
# Load balancer configuration
version: '3.8'
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf

  backend1:
    build: .
    environment:
      - INSTANCE_ID=backend1

  backend2: 
    build: .
    environment:
      - INSTANCE_ID=backend2
```

### Database Scaling:
- Redis clustering for high availability
- Database read replicas for queries
- Separate analytics database

## Support & Maintenance

### Regular Maintenance Tasks:
- Weekly: Review account health scores
- Monthly: Update browser versions
- Quarterly: Security audit and password rotation
- As needed: LinkedIn selector updates

### Monitoring Alerts:
- Account suspension warnings
- High error rates
- Memory/CPU usage alerts
- Queue size monitoring

For additional support or questions, refer to the system documentation or contact the development team.
