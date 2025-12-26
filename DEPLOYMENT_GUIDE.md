# LinkedIn Multi-Agent Automation System - Deployment Guide

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