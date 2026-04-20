# ScouterFRC — Infrastructure & Deployment Strategy

> **Version:** 1.0  
> **Status:** Planning  
> **Scope:** End-to-end infrastructure, deployment, and operations for ScouterFRC

---

## Table of Contents

1. [Overview & Goals](#1-overview--goals)
2. [Architecture Overview](#2-architecture-overview)
3. [Cloud Provider Selection](#3-cloud-provider-selection)
4. [Environment Strategy](#4-environment-strategy)
5. [Backend Infrastructure](#5-backend-infrastructure)
6. [Database Infrastructure](#6-database-infrastructure)
7. [Caching Layer](#7-caching-layer)
8. [Message Queue](#8-message-queue)
9. [Object Storage](#9-object-storage)
10. [CDN & Static Assets](#10-cdn--static-assets)
11. [DNS & Domains](#11-dns--domains)
12. [Security Infrastructure](#12-security-infrastructure)
13. [Monitoring & Alerting](#13-monitoring--alerting)
14. [CI/CD Pipeline](#14-cicd-pipeline)
15. [Backup & Disaster Recovery](#15-backup--disaster-recovery)
16. [Secrets Management](#16-secrets-management)
17. [SSL/TLS Configuration](#17-ssltls-configuration)
18. [Scaling Strategy](#18-scaling-strategy)
19. [Deployment Procedures](#19-deployment-procedures)
20. [Cost Optimization](#20-cost-optimization)
21. [Disaster Recovery & Business Continuity](#21-disaster-recovery--business-continuity)
22. [On-Premises Option](#22-on-premises-option)
23. [Development Environment Setup](#23-development-environment-setup)
24. [Production Deployment Checklist](#24-production-deployment-checklist)
25. [Infrastructure as Code (IaC)](#25-infrastructure-as-code-iac)

---

## 1. Overview & Goals

### Infrastructure Objectives

ScouterFRC infrastructure must support:

- **Reliable video processing** — Celery workers processing FRC match videos with GPU acceleration without data loss
- **Low-latency API responses** — Sub-200 ms p95 for all cached endpoints
- **Real-time dashboard updates** — WebSocket connections with minimal latency
- **Scalable storage** — Growing video library and tracking data across multiple seasons
- **Team-friendly cost model** — Minimize operating costs while maintaining reliability for competition season peaks

### Deployment Philosophy

| Principle | Implementation |
|-----------|---------------|
| **Reliability** | Zero-downtime deployments; rolling updates; health checks on all services |
| **Scalability** | Horizontal scaling for API and worker tiers; vertical scaling for GPU workers |
| **Cost-effectiveness** | On-demand GPU instances during competition season only; reserved instances for always-on services |
| **Simplicity** | Docker Compose for development; Kubernetes or managed container services for production |
| **Security** | Least-privilege IAM; secrets in a vault; encrypted data at rest and in transit |

### High Availability Requirements

| Service | Target Uptime | Strategy |
|---------|--------------|----------|
| FastAPI backend | 99.9% | Multi-instance behind load balancer |
| PostgreSQL | 99.9% | Primary + replica with automated failover |
| Redis | 99.5% | Sentinel or managed Redis cluster |
| Celery workers | Best-effort | Auto-restart; task retry with backoff |
| Object storage | 99.99% | Managed S3/GCS (provider SLA) |

### Geographic Considerations

- **Primary region:** `us-east-1` (AWS) or `us-central1` (GCP) — closest to the largest concentration of FRC teams in the eastern US
- **FRC competitions** occur primarily in North America; sub-100 ms latency is achievable from a single US region
- **CDN edge nodes** distribute static assets globally for international teams
- Multi-region replication is a Phase 3+ concern; a single well-architected region is sufficient for Phase 1 and Phase 2

---

## 2. Architecture Overview

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           INTERNET / USERS                              │
│                  Scouts · Coaches · Alliance Captains                   │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │ HTTPS
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         CDN / Edge Layer                                │
│                  (CloudFront / Fastly / Cloudflare)                     │
│            Static assets · API caching · DDoS mitigation               │
└──────────┬──────────────────────────────────────────────┬──────────────┘
           │ Static files                                 │ API requests
           ▼                                              ▼
┌──────────────────────┐              ┌───────────────────────────────────┐
│   Frontend Hosting   │              │         Load Balancer             │
│  (Vercel / Netlify)  │              │    (ALB / Cloud Load Balancing)   │
│  React + TypeScript  │              └───────────────┬───────────────────┘
└──────────────────────┘                              │
                                                      ▼
                                     ┌────────────────────────────────────┐
                                     │       FastAPI App Servers          │
                                     │   (2–4 instances, auto-scaling)    │
                                     │  Gunicorn + Uvicorn workers        │
                                     └───┬────────────────────┬───────────┘
                                         │                    │
                          ┌──────────────▼──────┐   ┌────────▼──────────────┐
                          │   PostgreSQL Cluster │   │     Redis Cluster     │
                          │  Primary + Replica   │   │  Cache + Broker       │
                          │  (RDS / Cloud SQL)   │   │  (ElastiCache / MemS) │
                          └──────────────────────┘   └───────────────────────┘
                                                              │
                                               ┌─────────────▼──────────────┐
                                               │      Celery Workers         │
                                               │  CPU: 2 instances           │
                                               │  GPU: 1–4 (auto-scaled)     │
                                               │  (ECS / GKE / K8s pods)     │
                                               └─────────────┬───────────────┘
                                                             │
                                               ┌─────────────▼──────────────┐
                                               │       Object Storage        │
                                               │   S3 / GCS Buckets          │
                                               │  Videos · Heatmaps · PDFs   │
                                               └────────────────────────────┘
```

### Component Interactions

| Component | Communicates With | Protocol |
|-----------|------------------|----------|
| React frontend | FastAPI backend | HTTPS REST + WebSocket |
| FastAPI | PostgreSQL | TCP (SQLAlchemy connection pool) |
| FastAPI | Redis | TCP (aioredis) |
| FastAPI | Celery | Redis broker (task dispatch) |
| Celery workers | PostgreSQL | TCP (SQLAlchemy) |
| Celery workers | Redis | TCP (result backend + broker) |
| Celery workers | Object storage | HTTPS (boto3 / google-cloud-storage) |
| CDN | Frontend host / API | HTTPS (origin pull) |

### Data Flow

```
1. Scout uploads match video
       │
       ▼
2. FastAPI validates file → stores in S3 → enqueues Celery task
       │
       ▼
3. Celery GPU worker pulls task → downloads video from S3
       │
       ▼
4. YOLOv8 + DeepSORT pipeline processes video frame-by-frame
       │
       ▼
5. MovementTrack rows written to PostgreSQL in batches
       │
       ▼
6. Analytics task triggered → PhaseStat rows computed
       │
       ▼
7. Redis cache invalidated for affected team/match endpoints
       │
       ▼
8. WebSocket broadcast notifies connected dashboard clients
       │
       ▼
9. Coaches see updated heatmaps and performance metrics in real time
```

### Resilience Patterns

- **Circuit breaker** on TBA API calls (fail open with stale cache)
- **Exponential backoff + jitter** on all Celery task retries
- **Idempotent task design** — re-running a video processing task is safe (upsert semantics)
- **Health checks** on every service; orchestrator restarts unhealthy containers automatically
- **Graceful shutdown** — workers drain in-flight tasks before stopping (SIGTERM → drain → SIGKILL)

---

## 3. Cloud Provider Selection

### Comparison Matrix

| Criterion | AWS | GCP | Azure | DigitalOcean | Heroku |
|-----------|-----|-----|-------|-------------|--------|
| GPU instances | ✅ g4dn/g5 (NVIDIA T4/A10G) | ✅ n1+T4, a2+A100 | ✅ NCv3/NVv4 | ❌ No GPU VMs | ❌ No GPU |
| Managed PostgreSQL | ✅ RDS | ✅ Cloud SQL | ✅ Flexible Server | ✅ Managed DB | ✅ (limited) |
| Managed Redis | ✅ ElastiCache | ✅ Memorystore | ✅ Azure Cache | ✅ Managed Redis | ✅ (add-on) |
| Object storage | ✅ S3 | ✅ GCS | ✅ Blob Storage | ✅ Spaces | ❌ |
| Container orchestration | ✅ ECS/EKS | ✅ Cloud Run/GKE | ✅ AKS | ✅ App Platform | ✅ (managed) |
| Free tier / startup credits | ✅ | ✅ Large credits | ✅ | ✅ $200 credit | ❌ |
| Global CDN | ✅ CloudFront | ✅ Cloud CDN | ✅ Azure CDN | ❌ (3rd party) | ❌ |
| GitHub Actions integration | ✅ OIDC | ✅ OIDC | ✅ OIDC | Moderate | Moderate |
| Learning resources / community | ✅ Largest | ✅ Strong | ✅ Strong | ✅ Beginner-friendly | ✅ |

### Recommendation: AWS

**Recommended stack:** AWS (primary) with Vercel/Netlify for frontend hosting

**Rationale:**
1. `g4dn.xlarge` instances provide NVIDIA T4 GPUs at ~$0.526/hr on-demand — ideal for burst CV processing during competition season
2. The broadest ecosystem of managed services (RDS, ElastiCache, S3, CloudFront) reduces operational overhead
3. Spot instances for Celery GPU workers can cut compute costs by 60–90%
4. GitHub Actions has first-class OIDC integration with AWS IAM roles
5. AWS Educate and AWS Activate provide significant free credits for open-source / student projects

### Monthly Cost Estimates (Phase 2 Production)

#### AWS (Recommended)

| Service | Instance / Config | Est. Monthly Cost |
|---------|------------------|-------------------|
| FastAPI — 2× `t3.medium` | ECS Fargate | ~$60 |
| PostgreSQL — `db.t3.medium` Multi-AZ | RDS | ~$80 |
| Redis — `cache.t3.micro` | ElastiCache | ~$20 |
| GPU workers — `g4dn.xlarge` Spot (20 hrs/mo) | EC2 Spot | ~$11 |
| Object storage — 500 GB + 100 GB transfer | S3 | ~$15 |
| Load balancer | ALB | ~$20 |
| CloudFront CDN | 1 TB out | ~$85 |
| Misc (NAT, data transfer) | — | ~$20 |
| **Total** | | **~$311/mo** |

#### GCP (Alternative)

| Service | Instance / Config | Est. Monthly Cost |
|---------|------------------|-------------------|
| FastAPI — 2× `e2-medium` | Cloud Run | ~$50 |
| PostgreSQL — `db-g1-small` HA | Cloud SQL | ~$90 |
| Redis — 1 GB Basic | Memorystore | ~$25 |
| GPU workers — `n1-standard-4 + T4` Spot | Compute | ~$15 |
| Object storage — 500 GB | GCS | ~$12 |
| Load balancer | HTTPS LB | ~$18 |
| Cloud CDN | 1 TB out | ~$80 |
| **Total** | | **~$290/mo** |

#### DigitalOcean (Budget Option)

| Service | Instance / Config | Est. Monthly Cost |
|---------|------------------|-------------------|
| FastAPI — 2× `s-2vcpu-4gb` | App Platform | ~$48 |
| PostgreSQL — 2 vCPU 4 GB | Managed DB | ~$50 |
| Redis — 1 GB | Managed Redis | ~$15 |
| GPU workers | External (Lambda Labs) | ~$20 |
| Object storage — 500 GB | Spaces | ~$10 |
| Load balancer | DO LB | ~$12 |
| CDN | Spaces CDN | ~$5 |
| **Total** | | **~$160/mo** |

> **Note:** DigitalOcean lacks native GPU instances; an external provider like Lambda Labs or CoreWeave must be used for CV workloads, which adds operational complexity.

---

## 4. Environment Strategy

### Environment Overview

| Environment | Purpose | Data | Deployment Trigger |
|-------------|---------|------|--------------------|
| **Local** | Active development | Synthetic seed data | Developer machine |
| **Development** | Integration testing, PR preview | Anonymized subset | PR opened |
| **Staging** | Pre-production validation | Production-mirror snapshot | Merge to `main` |
| **Production** | Live users | Real data | Tagged release |

### Local Development Setup

```bash
# Prerequisites: Docker Desktop, Python 3.11, Node 20
git clone https://github.com/dburcat/ScouterFRC.git
cd ScouterFRC

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in LOCAL overrides
docker compose up -d          # starts PostgreSQL, Redis, MinIO (S3-compatible)
alembic upgrade head          # apply migrations
python scripts/seed.py        # load synthetic data
uvicorn app.main:app --reload # FastAPI dev server

# Frontend
cd ../frontend
npm install
npm run dev                   # Vite dev server on :5173
```

### Development Environment

- Deployed to AWS ECS/GCP Cloud Run on every PR (ephemeral environment)
- Shares a single small RDS/Cloud SQL instance (separate database per PR)
- No GPU: CV tasks run in a mocked/stubbed mode with pre-recorded results
- Automatically torn down when PR is merged or closed

### Staging Environment

- Identical configuration to production (same instance types, same IAM roles)
- Receives production data snapshot weekly (PII stripped via `pg_dump | anonymize`)
- GPU workers available for full CV pipeline testing
- Manual promotion gate before deploying to production

### Production Environment

- Multi-AZ deployment (RDS Multi-AZ; multiple Fargate tasks across AZs)
- Blue-green or rolling deployment strategy (see Section 19)
- CloudFront CDN in front of all static assets and API responses
- Monitoring, alerting, and on-call rotation active (see Section 13)

---

## 5. Backend Infrastructure

### FastAPI App Server Configuration

```
Service:         FastAPI + Gunicorn + Uvicorn workers
Container:       Docker image (Python 3.11 slim)
Orchestration:   AWS ECS Fargate (Phase 2) / Kubernetes (Phase 3)
Instance type:   t3.medium (2 vCPU, 4 GB RAM) per task
Worker count:    gunicorn --workers 2 --worker-class uvicorn.workers.UvicornWorker
Port:            8000 (internal); 443 (external via ALB)
```

### Gunicorn Configuration (`gunicorn.conf.py`)

```python
bind = "0.0.0.0:8000"
workers = 2                        # 2 × (2 vCPU) = 4 total async workers
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 120                      # long for video upload endpoints
keepalive = 5
max_requests = 1000                # recycle workers to prevent memory leaks
max_requests_jitter = 100
preload_app = True
accesslog = "-"
errorlog = "-"
loglevel = "info"
```

### Horizontal Scaling

| Metric | Scale-Out Trigger | Scale-In Trigger | Min | Max |
|--------|------------------|-----------------|-----|-----|
| CPU utilization | > 70% for 3 min | < 30% for 10 min | 2 | 8 |
| Memory utilization | > 80% | < 40% | 2 | 8 |
| Request count (p95 latency) | > 400 ms | < 100 ms | 2 | 8 |

### Load Balancing Strategy

```
Internet → Route 53 → CloudFront → ALB → ECS Fargate tasks
                                     ↓
                              Target Group (HTTP 8000)
                              Health check: GET /health (200 OK)
                              Stickiness: disabled (stateless API)
                              Algorithm: least outstanding requests
```

### Health Check Endpoint

```python
# backend/app/routers/health.py
@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"
    
    redis_ok = await redis_client.ping()
    
    return {
        "status": "ok" if db_status == "ok" and redis_ok else "degraded",
        "database": db_status,
        "cache": "ok" if redis_ok else "error",
        "version": settings.APP_VERSION,
    }
```

### Resource Requirements

| Resource | Minimum (dev) | Recommended (prod) |
|----------|--------------|-------------------|
| CPU | 1 vCPU | 2 vCPU |
| RAM | 1 GB | 4 GB |
| Disk (ephemeral) | 10 GB | 20 GB |
| Network | 1 Gbps | 10 Gbps |

---

## 6. Database Infrastructure

### Database Selection: PostgreSQL 16

**Rationale:**
- Native JSONB for raw tracking data (`actions_detected` column)
- Window functions for analytics (ranking, rolling averages)
- TimescaleDB extension available for `MovementTrack` hypertables
- Mature ecosystem with SQLAlchemy 2 + Alembic

### Primary-Replica Setup

```
┌─────────────────────────────────────┐
│         PostgreSQL Primary           │
│   Accepts reads + writes             │
│   Streams WAL to replica             │
└───────────────────┬─────────────────┘
                    │ Streaming replication (sync for HA)
                    ▼
┌─────────────────────────────────────┐
│         PostgreSQL Replica          │
│   Read-only queries (analytics)     │
│   Standby for automatic failover    │
└─────────────────────────────────────┘
```

**SQLAlchemy connection routing:**

```python
# backend/app/database.py
from sqlalchemy.ext.asyncio import create_async_engine

write_engine = create_async_engine(settings.DATABASE_URL_PRIMARY)
read_engine  = create_async_engine(settings.DATABASE_URL_REPLICA)

# Use read_engine for analytics queries; write_engine for mutations
```

### Backup Strategy

| Backup Type | Frequency | Retention | Tool |
|------------|-----------|-----------|------|
| Automated snapshot | Daily | 30 days | RDS automated backups |
| WAL archiving (PITR) | Continuous | 7 days | pg_basebackup + WAL-G |
| Manual pre-deployment | On each deploy | 7 days | pg_dump to S3 |
| Weekly full dump | Weekly | 90 days | pg_dump + S3 Glacier |

### Recovery Procedures

```bash
# Point-in-time recovery (PITR) to specific timestamp
walg wal-restore --until "2024-03-15 14:30:00" --target-db scouterfrc_restored

# Restore from pg_dump
aws s3 cp s3://scouterfrc-backups/dumps/latest.dump /tmp/latest.dump
pg_restore --dbname scouterfrc_prod --clean --if-exists /tmp/latest.dump

# Verify row counts post-restore
psql -c "SELECT relname, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC;"
```

### Connection Pooling

```
Application → PgBouncer (transaction mode) → PostgreSQL Primary

PgBouncer config:
  pool_mode = transaction
  max_client_conn = 200
  default_pool_size = 20
  server_lifetime = 3600
  server_idle_timeout = 600
```

### Scaling Strategy

| Stage | Strategy |
|-------|---------|
| Phase 1–2 (< 10 k teams) | Single primary + 1 replica; `db.t3.medium` |
| Phase 3 (10 k–100 k rows/day) | Upgrade to `db.r6g.large`; add read replica for analytics |
| Future (> 1 M tracking rows/day) | TimescaleDB hypertable for `movement_track`; partition by `match_id` |

---

## 7. Caching Layer

### Redis Infrastructure

| Config | Value |
|--------|-------|
| Version | Redis 7.x |
| Instance | `cache.t3.micro` (ElastiCache) — upgradeable |
| Memory limit | 1 GB (Phase 2); 4 GB (Phase 3) |
| Eviction policy | `allkeys-lru` |
| Persistence | RDB snapshot every 15 min (AOF disabled for performance) |

### Cluster Setup

- **Phase 2:** Single Redis node with Sentinel for HA (master + 2 sentinels)
- **Phase 3:** Redis Cluster with 3 shards × 1 replica = 6 nodes (if memory > 8 GB)

### TTL Strategy

| Cache Key Pattern | TTL | Rationale |
|------------------|-----|-----------|
| `event:{id}:teams` | 5 min | Teams change infrequently |
| `team:{id}:stats` | 10 min | Stats updated after each match |
| `match:{id}:detail` | 2 min | Match details (scores) can update live |
| `analytics:rankings:{event_id}` | 15 min | Heavy compute, invalidate after sync |
| `tba:event:{key}` | 1 hour | TBA API rate limit management |
| `session:{token}` | 24 hours | JWT session data |

### Cache Invalidation

```python
# Invalidate all team stats after a match is processed
async def invalidate_match_cache(match_id: int, team_ids: list[int]):
    keys = [f"match:{match_id}:detail"]
    keys += [f"team:{tid}:stats" for tid in team_ids]
    keys += [f"analytics:rankings:{event_id}"]
    await redis.delete(*keys)
```

---

## 8. Message Queue

### Celery + Redis Configuration

```python
# backend/app/celery_app.py
from celery import Celery

celery_app = Celery(
    "scouterfrc",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.video_tasks", "app.tasks.analytics_tasks",
             "app.tasks.sync_tasks", "app.tasks.report_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,          # Ensure tasks not lost on worker crash
    worker_prefetch_multiplier=1,  # Fair distribution for long video tasks
    task_routes={
        "app.tasks.video_tasks.*": {"queue": "video"},
        "app.tasks.analytics_tasks.*": {"queue": "analytics"},
        "app.tasks.sync_tasks.*": {"queue": "sync"},
        "app.tasks.report_tasks.*": {"queue": "reports"},
    },
)
```

### Worker Scaling Strategy

| Queue | Worker Type | Concurrency | Auto-Scale |
|-------|------------|-------------|------------|
| `video` | GPU (`g4dn.xlarge`) | 1 per GPU | 0–4 instances |
| `analytics` | CPU (`t3.medium`) | 4 | 1–4 instances |
| `sync` | CPU (`t3.micro`) | 2 | 1–2 instances |
| `reports` | CPU (`t3.medium`) | 2 | 1–2 instances |

### Job Retry Logic

```python
@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,           # Exponential: 60s, 120s, 240s
    retry_backoff_max=600,
    retry_jitter=True,
)
def process_video_file(self, match_id: int, s3_key: str):
    ...
```

### Dead Letter Queue Handling

```python
# Tasks that exhaust retries are routed to the dead-letter queue
celery_app.conf.task_routes["app.tasks.*"] = {
    "queue": "default",
    "dead_letter_queue": "failed_tasks",
}

# Periodic task to alert on dead-letter queue depth
@celery_app.task
def check_dead_letter_queue():
    count = redis.llen("failed_tasks")
    if count > 10:
        send_alert(f"Dead-letter queue has {count} failed tasks")
```

### Monitoring (Flower)

```bash
# Start Flower monitoring UI
celery -A app.celery_app flower --port=5555 --url_prefix=flower

# Access at: https://scouterfrc.example.com/flower (protected by basic auth)
```

---

## 9. Object Storage

### Storage Architecture

| Bucket / Container | Purpose | Access |
|-------------------|---------|--------|
| `scouterfrc-videos-raw` | Original uploaded match videos | Private; pre-signed URLs |
| `scouterfrc-videos-processed` | Trimmed/annotated clips for review | Private; pre-signed URLs |
| `scouterfrc-heatmaps` | Exported heatmap PNG/SVG files | Public read via CDN |
| `scouterfrc-reports` | Generated PDF/CSV reports | Private; pre-signed URLs |
| `scouterfrc-backups` | Database dumps and WAL archives | Private; versioning enabled |
| `scouterfrc-ml-models` | Trained YOLOv8 weights | Private |
| `scouterfrc-static` | Frontend static assets (fallback) | Public read |

### Organization Strategy

```
scouterfrc-videos-raw/
  {season_year}/          # e.g., 2024/
    {event_key}/          # e.g., 2024necmp/
      {match_key}/        # e.g., 2024necmp_qm12/
        original.mp4
        metadata.json

scouterfrc-heatmaps/
  {season_year}/
    {event_key}/
      {team_number}/
        match_{id}_heatmap.png
        season_aggregate_heatmap.png
```

### Lifecycle Policies

```json
{
  "Rules": [
    {
      "ID": "archive-old-raw-videos",
      "Filter": { "Prefix": "scouterfrc-videos-raw/" },
      "Status": "Enabled",
      "Transitions": [
        { "Days": 90,  "StorageClass": "STANDARD_IA" },
        { "Days": 365, "StorageClass": "GLACIER" }
      ]
    },
    {
      "ID": "delete-old-backups",
      "Filter": { "Prefix": "scouterfrc-backups/dumps/" },
      "Status": "Enabled",
      "Expiration": { "Days": 90 }
    }
  ]
}
```

### CDN Integration

- Raw videos served via pre-signed S3 URLs (15-min expiry) — not cached through CDN
- Heatmap images served via CloudFront (`scouterfrc-heatmaps` origin) — cached 24 hours
- Reports served via pre-signed URLs with 1-hour expiry

### Cost Optimization

| Strategy | Savings |
|---------|---------|
| S3 Intelligent-Tiering for videos | 40–68% on infrequently accessed videos |
| GLACIER for videos > 1 year old | 80%+ vs. STANDARD |
| Multipart upload for videos > 100 MB | Reduces failed upload costs |
| S3 Transfer Acceleration only when needed | Avoids unnecessary surcharges |

---

## 10. CDN & Static Assets

### CDN Provider Selection

**Recommended:** AWS CloudFront (co-located with backend; unified IAM)  
**Alternative:** Cloudflare (provider-agnostic; excellent free tier; WAF included)

### CloudFront Distribution Configuration

```
Origins:
  1. API origin:      ALB DNS name (HTTPS only)
  2. Static origin:   Vercel/Netlify or S3 static bucket
  3. Heatmaps origin: s3://scouterfrc-heatmaps

Cache Behaviors:
  - /api/*            → API origin; Cache-Control: no-store
  - /static/*         → Static origin; Cache 1 year (content-hash filenames)
  - /heatmaps/*       → Heatmaps origin; Cache 24 hours
  - /*                → Static origin (SPA fallback)

Price Class:  PriceClass_100 (US, Europe) — reduces CDN cost ~50%
```

### Cache Invalidation Strategy

```bash
# Triggered automatically on deploy by GitHub Actions
aws cloudfront create-invalidation \
  --distribution-id $CF_DISTRIBUTION_ID \
  --paths "/static/*" "/index.html"
```

### Static Asset Versioning

All frontend assets use **content-hash filenames** generated by Vite:

```
# Before:  /static/main.js
# After:   /static/main.a3f9c2b1.js
```

This allows `Cache-Control: max-age=31536000, immutable` for all versioned assets and targeted invalidation of only `index.html` on deploy.

---

## 11. DNS & Domains

### Domain Structure

| Domain | Purpose |
|--------|---------|
| `scouterfrc.app` (example) | Production frontend + API |
| `api.scouterfrc.app` | API subdomain (optional separation) |
| `staging.scouterfrc.app` | Staging environment |
| `flower.scouterfrc.app` | Celery Flower monitoring (restricted) |
| `grafana.scouterfrc.app` | Grafana dashboards (restricted) |

### DNS Provider Selection

**Recommended:** AWS Route 53  
- Latency-based routing available for future multi-region
- Integrates with ALB alias records (no IP management)
- Health-check-based DNS failover

### SSL/TLS Certificate Management

| Option | Use Case | Renewal |
|--------|---------|---------|
| **AWS ACM** | ALB/CloudFront termination | Automatic |
| **Let's Encrypt + Certbot** | Self-hosted / on-premises | 90-day auto-renewal via cron |

**Recommendation:** Use AWS ACM for production (zero-config renewal). Use Let's Encrypt for staging and on-premises deployments.

### Multi-Region DNS Strategy (Phase 3+)

```
Route 53 latency-based routing:
  us-east-1: primary production stack
  eu-west-1: European replica (Phase 3)
  ap-southeast-1: APAC replica (Phase 3)
```

---

## 12. Security Infrastructure

### VPC / Network Configuration

```
VPC: 10.0.0.0/16
  ├── Public subnets (10.0.1.0/24, 10.0.2.0/24)
  │     ALB, NAT Gateway
  │
  ├── Private subnets (10.0.10.0/24, 10.0.11.0/24)
  │     ECS Fargate tasks (FastAPI, Celery workers)
  │
  └── Database subnets (10.0.20.0/24, 10.0.21.0/24)
        RDS PostgreSQL, ElastiCache Redis
```

### Security Groups

| Resource | Inbound | Outbound |
|---------|---------|---------|
| ALB | 443 from 0.0.0.0/0 | 8000 to ECS SG |
| ECS (FastAPI) | 8000 from ALB SG | 5432 to RDS SG; 6379 to Redis SG; 443 to internet |
| ECS (Celery) | None (workers pull) | 5432 to RDS SG; 6379 to Redis SG; 443 to internet |
| RDS | 5432 from ECS SG only | None |
| ElastiCache | 6379 from ECS SG only | None |

### DDoS Protection

- **AWS Shield Standard** — included at no cost; protects ALB and CloudFront from volumetric attacks
- **CloudFront** — absorbs Layer 7 spikes at the edge before reaching origin
- **ALB connection limits** — configurable per-target connection limits
- **Rate limiting** — FastAPI middleware limits unauthenticated endpoints to 100 req/min per IP

```python
# backend/app/middleware/rate_limit.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/v1/events")
@limiter.limit("100/minute")
async def list_events(request: Request):
    ...
```

### WAF Configuration

AWS WAF rules applied to CloudFront distribution:

```
Managed Rule Groups:
  - AWSManagedRulesCommonRuleSet       (OWASP Top 10)
  - AWSManagedRulesSQLiRuleSet         (SQL injection)
  - AWSManagedRulesKnownBadInputsRuleSet

Custom Rules:
  - Block requests with suspicious user agents
  - Rate limit /api/v1/auth/login: 10 req/min per IP
  - Allow only MP4/MOV content-type on /api/v1/matches/*/video
```

---

## 13. Monitoring & Alerting

### Application Performance Monitoring (APM)

**Recommended:** Sentry (error tracking) + Prometheus (metrics) + Grafana (dashboards)

```python
# Sentry integration in FastAPI
import sentry_sdk
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    traces_sample_rate=0.1,       # 10% transaction sampling
    profiles_sample_rate=0.01,
    environment=settings.ENVIRONMENT,
)
app.add_middleware(SentryAsgiMiddleware)
```

### Infrastructure Monitoring (Prometheus)

```yaml
# monitoring/prometheus/prometheus.yml
scrape_configs:
  - job_name: fastapi
    static_configs:
      - targets: ['fastapi:8000']
    metrics_path: /metrics

  - job_name: celery
    static_configs:
      - targets: ['celery-exporter:9808']

  - job_name: postgres
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: redis
    static_configs:
      - targets: ['redis-exporter:9121']
```

### Key Metrics to Track

| Metric | Tool | Alert Threshold |
|--------|------|----------------|
| API p95 latency | Prometheus | > 500 ms for 5 min |
| API error rate (5xx) | Prometheus | > 1% for 2 min |
| Celery queue depth (video) | Prometheus | > 20 tasks |
| Celery task failure rate | Prometheus | > 5% in 10 min |
| PostgreSQL connections | Prometheus | > 80% pool used |
| Redis memory usage | Prometheus | > 85% |
| Disk usage | CloudWatch | > 80% |
| GPU utilization (CV workers) | CloudWatch | < 10% when queue > 5 (idle waste) |

### Log Aggregation

```
Application logs → CloudWatch Logs (JSON structured)
                 → (optional) Datadog / Grafana Loki for advanced queries

Log format:
{
  "timestamp": "2024-03-15T14:30:00Z",
  "level": "INFO",
  "service": "fastapi",
  "trace_id": "abc123",
  "message": "Video processing task dispatched",
  "match_id": 42,
  "task_id": "celery-uuid-xyz"
}
```

### Grafana Dashboard Panels

1. **API Overview** — request rate, error rate, p50/p95/p99 latency
2. **Celery Workers** — active workers, queue depths, task success/failure rate
3. **Database** — connections, query latency, replication lag
4. **Redis** — memory usage, hit rate, eviction rate
5. **CV Pipeline** — videos processed/hour, avg processing time, GPU utilization
6. **Business Metrics** — events tracked, teams scouted, reports generated

### On-Call Rotation Strategy

- Phase 1–2: Single on-call (project maintainer); alerts via PagerDuty free tier or email
- Phase 3: Two-person on-call rotation; 15-minute SLA for P1 alerts
- Runbooks for all P1/P2 scenarios stored in `docs/runbooks/`

---

## 14. CI/CD Pipeline

### Git Workflow

```
main          — Protected; production-ready code only
  ↑ PR
develop       — Integration branch; all feature branches merge here
  ↑ PR
feature/*     — Short-lived feature branches
fix/*         — Bug fix branches
release/*     — Release preparation branches
```

**Branch protection rules for `main`:**
- Require 1 approving review
- Require all status checks to pass (lint, test, build)
- No force pushes
- Linear history preferred (squash merges)

### GitHub Actions Pipeline

```yaml
# .github/workflows/ci.yml
name: CI

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install ruff mypy && ruff check . && mypy app/

  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env: { POSTGRES_PASSWORD: test, POSTGRES_DB: test_db }
      redis:
        image: redis:7
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements.txt
      - run: pytest --cov=app --cov-report=xml -x
      - uses: codecov/codecov-action@v4

  build:
    needs: [lint, test]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/build-push-action@v5
        with:
          push: ${{ github.ref == 'refs/heads/main' }}
          tags: ghcr.io/dburcat/scouterfrc:${{ github.sha }}

  deploy-staging:
    needs: [build]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_STAGING_ROLE_ARN }}
          aws-region: us-east-1
      - run: aws ecs update-service --cluster staging --service fastapi --force-new-deployment
```

### Deployment Stages

```
Code push → Lint + Test → Build Docker image → Push to GHCR
                                                    │
                                         ┌──────────▼──────────┐
                                         │  Auto-deploy Staging │
                                         │  (on merge to main)  │
                                         └──────────┬──────────┘
                                                    │ Manual approval
                                         ┌──────────▼──────────┐
                                         │  Deploy Production   │
                                         │  (tagged release)    │
                                         └─────────────────────┘
```

### Automated Testing Gates

| Gate | Failure Action |
|------|---------------|
| Unit tests (< 2 min) | Block PR merge |
| Integration tests (< 5 min) | Block PR merge |
| Code coverage < 80% | Warning (non-blocking) |
| Security scan (Bandit/Trivy) | Block if HIGH severity |
| Performance regression (> 20%) | Warning |

### Rollback Procedures

```bash
# Rollback ECS service to previous task definition
aws ecs update-service \
  --cluster production \
  --service fastapi \
  --task-definition fastapi:$PREVIOUS_REVISION \
  --force-new-deployment

# Verify rollback
aws ecs describe-services --cluster production --services fastapi \
  | jq '.services[0].taskDefinition'
```

### Deployment Frequency Target

| Phase | Target Frequency |
|-------|----------------|
| Phase 1 | 1–2 deploys/week |
| Phase 2 | 3–5 deploys/week |
| Phase 3 | Multiple deploys/day (feature flags for gradual rollout) |

---

## 15. Backup & Disaster Recovery

### Backup Overview

| Asset | Method | Frequency | Retention | Location |
|-------|--------|-----------|-----------|----------|
| PostgreSQL data | RDS automated snapshots | Daily | 30 days | Same region |
| PostgreSQL WAL | WAL-G continuous archiving | Continuous | 7 days | S3 |
| PostgreSQL schema | pg_dump on deploy | Per deploy | 7 days | S3 |
| Redis data | RDB snapshot | Every 15 min | 24 hours | Local (EBS) |
| S3 video files | S3 versioning | On upload | 365 days | Same bucket |
| S3 cross-region | S3 CRR rule | Continuous | 90 days | us-west-2 |
| ML model weights | S3 versioning | On retrain | All versions | Same bucket |

### Point-in-Time Recovery (PITR)

RDS automated backups + transaction logs enable PITR to any second within the retention window:

```bash
# AWS Console: RDS → Restore to Point in Time
# CLI:
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier scouterfrc-prod \
  --target-db-instance-identifier scouterfrc-restored \
  --restore-time 2024-03-15T14:30:00Z
```

### RTO / RPO Targets

| Scenario | RPO | RTO |
|---------|-----|-----|
| Database failure (primary) | < 5 min | < 10 min (replica failover) |
| Full AZ outage | < 1 hour | < 30 min |
| Region-level disaster | < 24 hours | < 4 hours |
| Accidental data deletion | < 15 min (PITR) | < 1 hour |

### Backup Testing Procedures

- **Monthly:** Restore last RDS snapshot to `scouterfrc-backup-test` instance; run row count checks
- **Quarterly:** Full DR drill — restore entire stack in a separate VPC from backups; verify API responds correctly
- **Annual:** Document drill results and update runbooks

---

## 16. Secrets Management

### Secret Categories

| Secret | Storage | Rotation |
|--------|---------|---------|
| Database credentials | AWS Secrets Manager | 90 days (automatic) |
| Redis auth token | AWS Secrets Manager | 180 days |
| JWT signing key | AWS Secrets Manager | 365 days |
| TBA API key | AWS Secrets Manager | On compromise |
| S3 access keys | IAM roles (no static keys) | N/A |
| Sentry DSN | GitHub Actions secret | On compromise |
| SSL certificates | AWS ACM | Automatic (ACM) |

### Environment Variables

```bash
# .env.example (committed — no real values)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/scouterfrc
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=change-me-in-production
TBA_API_KEY=your-tba-key-here
AWS_REGION=us-east-1
S3_BUCKET_VIDEOS=scouterfrc-videos-raw
SENTRY_DSN=
ENVIRONMENT=development
```

### AWS Secrets Manager Integration

```python
# backend/app/config.py
import boto3
import json

def get_secret(secret_name: str) -> dict:
    client = boto3.client("secretsmanager", region_name="us-east-1")
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response["SecretString"])

# In production, DATABASE_URL is assembled from the secret at startup
if settings.ENVIRONMENT == "production":
    db_secret = get_secret("scouterfrc/prod/database")
    settings.DATABASE_URL = (
        f"postgresql+asyncpg://{db_secret['username']}:{db_secret['password']}"
        f"@{db_secret['host']}:{db_secret['port']}/{db_secret['dbname']}"
    )
```

### Access Control

- Each service (FastAPI, Celery) uses a dedicated IAM role with minimal permissions
- Database credentials are never stored in environment variables in production
- GitHub Actions uses OIDC to assume IAM roles — no long-lived AWS credentials in CI

---

## 17. SSL/TLS Configuration

### Certificate Acquisition

| Environment | Method | Issuer |
|-------------|--------|--------|
| Production (AWS) | AWS ACM | Amazon Trust Services |
| Staging | AWS ACM | Amazon Trust Services |
| Local / On-premises | Let's Encrypt | ISRG |

### Let's Encrypt Auto-Renewal

```bash
# /etc/cron.d/certbot
0 0,12 * * * root certbot renew --quiet --deploy-hook "nginx -s reload"
```

### TLS Protocol Configuration (Nginx / ALB)

```nginx
# Nginx TLS hardening
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256;
ssl_prefer_server_ciphers off;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 1d;
ssl_session_tickets off;
```

### HSTS Headers

```nginx
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
add_header X-Frame-Options DENY always;
add_header X-Content-Type-Options nosniff always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;
```

---

## 18. Scaling Strategy

### Horizontal Scaling

| Service | Scale Unit | Trigger |
|---------|-----------|---------|
| FastAPI | +1 ECS task | CPU > 70% or p95 > 400 ms |
| Celery CPU workers | +1 ECS task | Queue depth > 10 tasks |
| Celery GPU workers | +1 EC2 Spot | Video queue depth > 3 tasks |

### Vertical Scaling

| Phase | FastAPI | PostgreSQL | Redis |
|-------|---------|-----------|-------|
| Phase 1 | t3.small | db.t3.micro | cache.t3.micro |
| Phase 2 | t3.medium | db.t3.medium | cache.t3.small |
| Phase 3 | c6g.large | db.r6g.large | cache.r6g.large |

### Auto-Scaling Configuration (ECS)

```json
{
  "ServiceName": "fastapi",
  "ScalableDimension": "ecs:service:DesiredCount",
  "MinCapacity": 2,
  "MaxCapacity": 8,
  "TargetTrackingScalingPolicies": [
    {
      "TargetValue": 70.0,
      "PredefinedMetricType": "ECSServiceAverageCPUUtilization",
      "ScaleInCooldown": 300,
      "ScaleOutCooldown": 60
    }
  ]
}
```

### Database Scaling

| Phase | Strategy |
|-------|---------|
| Phase 1–2 | Single primary + 1 read replica |
| Phase 3 | Add second read replica; promote to `db.r6g.large` |
| Future | TimescaleDB hypertables for `movement_track`; partition by event/season |

### Storage Scaling

- S3 scales automatically — no action required
- Monitor `scouterfrc-videos-raw` bucket size; enable lifecycle rules to manage cost
- EBS volumes for database: Set CloudWatch alarm at 80% usage; extend via console

---

## 19. Deployment Procedures

### Zero-Downtime Deployment Strategy

ScouterFRC uses **rolling deployments** with ECS and a minimum healthy percent of 100%:

```
Phase 1: Start new task(s) alongside existing tasks
Phase 2: ALB health check confirms new tasks are healthy
Phase 3: Drain connections from old tasks (deregistration delay: 30s)
Phase 4: Terminate old tasks
```

### Rolling vs. Blue-Green

| Strategy | Use Case | Rollback Time |
|---------|---------|--------------|
| **Rolling** (default) | All normal deploys | ~5 min (redeploy old image) |
| **Blue-Green** | Major breaking changes; database migrations | ~1 min (DNS switch) |

Blue-green is reserved for releases that include breaking API changes or complex database migrations where instant rollback must be available.

### Database Migration Strategy

```bash
# Always run migrations BEFORE deploying new application code
# New code must be backward-compatible with the old schema during rollout

# Step 1: Run migration against production database
alembic upgrade head

# Step 2: Verify migration succeeded
alembic current

# Step 3: Deploy new application code (rolling)
# Step 4: Verify health checks pass
# Step 5: If failure: rollback application code (NOT the migration)
```

**Backward-compatible migration rules:**
- Add columns as nullable (not NOT NULL without a default)
- Never rename columns directly (add new → backfill → remove old in separate deploy)
- Never drop columns in the same deploy that removes the code reading them

### Deployment Checklist

Before every production deploy:

- [ ] All CI checks pass on the commit being deployed
- [ ] Manual pre-deployment database backup triggered
- [ ] Staging deploy succeeded and smoke tests passed
- [ ] On-call engineer notified
- [ ] Rollback plan documented

### Post-Deployment Verification

```bash
# Run smoke test suite against production
pytest tests/smoke/ --base-url https://api.scouterfrc.app -x

# Check key metrics in Grafana for 15 minutes post-deploy
# Verify no spike in 5xx errors
# Verify p95 latency within normal range
```

### Rollback Triggers

Automatically roll back if within 15 minutes of deploy:
- 5xx error rate exceeds 2% (vs < 0.1% baseline)
- p95 API latency exceeds 1 second
- Health check failure rate > 0%

---

## 20. Cost Optimization

### Reserved Instances vs. On-Demand

| Service | Recommendation | Savings |
|---------|---------------|---------|
| FastAPI ECS (Fargate) | Fargate Savings Plans (1-year) | ~20% |
| RDS PostgreSQL | 1-year Reserved Instance | ~30% |
| ElastiCache Redis | Reserved Cache Node (1-year) | ~35% |
| GPU workers | EC2 Spot Instances | 60–90% |

### Spot Instances for Background Jobs

```python
# GPU Celery workers run on EC2 Spot; bid at on-demand price
# Use Spot interruption handler to gracefully drain tasks on 2-min warning
@celery_app.task
def process_video_file(self, ...):
    # Register spot interruption check
    if check_spot_interruption():
        # Re-queue task for another worker before instance terminates
        self.retry(countdown=5)
    ...
```

### Data Transfer Costs

- Use S3 Transfer Acceleration only for uploads > 1 GB from distant locations
- Keep Celery workers and S3 in the same AWS region (free intra-region transfer)
- Use CloudFront for all outbound reads (CDN egress is cheaper than origin egress)
- Compress API responses with gzip (reduces bandwidth ~70%)

### Storage Lifecycle Policies

- Move videos to S3-IA after 90 days (40% savings)
- Move videos to S3 Glacier after 365 days (80% savings)
- Delete processed intermediate frames after 7 days

### Caching ROI

- Caching `analytics:rankings` eliminates repeated heavy SQL queries (estimated 80% cache hit rate at steady state)
- Each cache hit avoids ~50 ms of DB query time + CPU
- Redis `cache.t3.micro` at ~$20/mo avoids ~$80/mo of additional RDS scaling

### Cost Monitoring

```bash
# Set AWS Budget alert at $400/mo
aws budgets create-budget \
  --account-id $AWS_ACCOUNT_ID \
  --budget '{
    "BudgetName": "ScouterFRC-Monthly",
    "BudgetLimit": {"Amount": "400", "Unit": "USD"},
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST"
  }' \
  --notifications-with-subscribers '[{
    "Notification": {"NotificationType": "ACTUAL", "ComparisonOperator": "GREATER_THAN", "Threshold": 80},
    "Subscribers": [{"SubscriptionType": "EMAIL", "Address": "ops@scouterfrc.app"}]
  }]'
```

---

## 21. Disaster Recovery & Business Continuity

### RTO / RPO Targets (Detailed)

| Incident | Data Loss (RPO) | Recovery Time (RTO) | Procedure |
|---------|----------------|---------------------|-----------|
| Single ECS task crash | 0 | < 30 sec (ECS restart) | Automatic |
| Database primary failure | < 5 min (replication lag) | < 10 min (replica promotion) | Semi-automatic (RDS Multi-AZ) |
| Full AZ outage | < 5 min | < 30 min (failover to other AZ) | Semi-automatic |
| Accidental table drop | < 15 min (PITR) | < 1 hour | Manual (PITR restore) |
| Region-level disaster | < 24 hours | < 4 hours | Manual (cross-region restore) |

### Failover Procedures

```bash
# Manual RDS failover (if automatic fails)
aws rds failover-db-cluster --db-cluster-identifier scouterfrc-prod

# Promote read replica manually
aws rds promote-read-replica --db-instance-identifier scouterfrc-replica

# Update application DATABASE_URL secret to point to promoted replica
aws secretsmanager update-secret \
  --secret-id scouterfrc/prod/database \
  --secret-string '{"host": "new-primary-endpoint", ...}'

# Restart ECS services to pick up new database endpoint
aws ecs update-service --cluster production --service fastapi --force-new-deployment
aws ecs update-service --cluster production --service celery-worker --force-new-deployment
```

### Data Replication Strategy

- RDS synchronous replication to standby replica in the same region (different AZ)
- S3 Cross-Region Replication to `us-west-2` for video files and backups
- Redis: persistence via RDB snapshot (data loss acceptable — cache is reconstructable)

### Incident Response Procedures

1. **Detection** — CloudWatch alarm fires → PagerDuty alert → on-call engineer notified
2. **Triage** — Engineer assesses impact (P1/P2/P3) and opens incident Slack channel
3. **Mitigation** — Follow runbook for the specific failure scenario
4. **Communication** — Post status update to `#status` channel every 30 minutes during P1
5. **Resolution** — Confirm all health checks pass; monitor for 30 minutes
6. **Post-mortem** — Within 48 hours: document timeline, root cause, and preventive actions

### Communication During Outages

- Status page: `status.scouterfrc.app` (e.g., Statuspage.io free tier)
- In-app banner: API returns `Retry-After` header and degraded mode when database is unavailable
- Email notifications to team admins for outages > 15 minutes

---

## 22. On-Premises Option

For FRC teams or programs that prefer a self-hosted solution (e.g., no cloud budget, school network restrictions).

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|------------|
| Application server | 4 vCPU, 8 GB RAM | 8 vCPU, 16 GB RAM |
| GPU (CV processing) | NVIDIA GTX 1060 6GB | NVIDIA RTX 3080 / A10 |
| Database server | 2 vCPU, 4 GB RAM | 4 vCPU, 16 GB RAM |
| Storage | 500 GB SSD | 2 TB NVMe SSD |
| Network | 1 Gbps LAN | 1 Gbps LAN + 100 Mbps WAN |

### Network Setup

```
Internet
   │ Port 443 (HTTPS)
   ▼
Router / Firewall
   │
   ├── DMZ (10.0.1.0/24)
   │     Nginx reverse proxy (HTTPS termination)
   │
   └── LAN (10.0.10.0/24)
         Application server (FastAPI + Celery)
         Database server (PostgreSQL)
         Cache server (Redis)
```

### Docker Compose for On-Premises

```yaml
# deploy/docker-compose.onprem.yml
version: "3.9"
services:
  nginx:
    image: nginx:1.25-alpine
    ports: ["443:443", "80:80"]
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro

  api:
    image: ghcr.io/dburcat/scouterfrc:latest
    env_file: .env
    depends_on: [postgres, redis]

  celery-worker:
    image: ghcr.io/dburcat/scouterfrc:latest
    command: celery -A app.celery_app worker -Q video,analytics -c 2
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  postgres:
    image: postgres:16
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: scouterfrc
      POSTGRES_USER: scouterfrc
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    command: redis-server --save 900 1 --loglevel warning

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data
    ports: ["9000:9000", "9001:9001"]

volumes:
  postgres_data:
  redis_data:
  minio_data:
```

### Backup Procedures (On-Premises)

```bash
#!/usr/bin/env bash
# /opt/scouterfrc/scripts/backup.sh — run via cron daily at 02:00

set -euo pipefail
BACKUP_DIR="/backup/scouterfrc/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# PostgreSQL dump
docker exec scouterfrc-postgres-1 pg_dump -U scouterfrc scouterfrc \
  | gzip > "$BACKUP_DIR/postgres.dump.gz"

# MinIO data (videos)
rclone sync minio:scouterfrc-videos-raw "$BACKUP_DIR/videos" \
  --config /etc/rclone.conf

# Retain 30 days
find /backup/scouterfrc -maxdepth 1 -type d -mtime +30 -exec rm -rf {} +

echo "Backup complete: $BACKUP_DIR"
```

### Maintenance Responsibilities

On-premises operators are responsible for:
- OS security patches (recommend automatic unattended-upgrades on Ubuntu)
- Docker and container image updates
- SSL certificate renewal (Let's Encrypt cron; see Section 17)
- Database vacuum and index maintenance (`pg_cron` extension recommended)
- Hardware monitoring and disk space management

---

## 23. Development Environment Setup

### Prerequisites

```bash
# Required
- Docker Desktop 4.x or Docker Engine 24.x + Docker Compose 2.x
- Python 3.11
- Node.js 20 LTS
- Git 2.x

# Recommended
- VS Code with Python, ESLint, Prettier extensions
- pgAdmin or TablePlus (PostgreSQL GUI)
- RedisInsight (Redis GUI)
```

### Full Local Setup

```bash
# 1. Clone repository
git clone https://github.com/dburcat/ScouterFRC.git
cd ScouterFRC

# 2. Start infrastructure services
docker compose -f deploy/docker-compose.dev.yml up -d
# Starts: PostgreSQL 16, Redis 7, MinIO (S3-compatible), Flower (Celery UI)

# 3. Backend setup
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env        # Edit .env with local values

# 4. Run database migrations
alembic upgrade head

# 5. Seed development data
python scripts/seed.py --events 5 --teams 40 --matches 60

# 6. Start backend server
uvicorn app.main:app --reload --port 8000
# API docs: http://localhost:8000/docs

# 7. Frontend setup (separate terminal)
cd ../frontend
npm install
cp .env.local.example .env.local
npm run dev
# App: http://localhost:5173

# 8. Start Celery worker (separate terminal)
cd backend
celery -A app.celery_app worker --loglevel=info -Q video,analytics,sync,reports

# 9. Start Celery Beat scheduler (separate terminal)
celery -A app.celery_app beat --loglevel=info
```

### Docker Compose Dev Configuration

```yaml
# deploy/docker-compose.dev.yml
services:
  postgres:
    image: postgres:16
    ports: ["5432:5432"]
    environment:
      POSTGRES_DB: scouterfrc_dev
      POSTGRES_USER: dev
      POSTGRES_PASSWORD: dev_password
    volumes:
      - postgres_dev_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  minio:
    image: minio/minio
    ports: ["9000:9000", "9001:9001"]
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    volumes:
      - minio_dev_data:/data

  flower:
    image: mher/flower
    ports: ["5555:5555"]
    environment:
      CELERY_BROKER_URL: redis://redis:6379/0
    depends_on: [redis]

volumes:
  postgres_dev_data:
  minio_dev_data:
```

### Pre-Commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.9.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-merge-conflict
      - id: detect-private-key
```

```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install
```

---

## 24. Production Deployment Checklist

### Pre-Deployment Checks

- [ ] All CI tests pass on the tagged commit
- [ ] Docker image successfully built and pushed to GHCR
- [ ] Staging environment deployed and smoke tests pass
- [ ] Database migrations reviewed and tested on staging
- [ ] Rollback procedure documented and tested
- [ ] On-call engineer available and notified
- [ ] Status page incident created (if customer-visible change)
- [ ] Manual database backup triggered and confirmed

### Deployment Steps

```bash
# 1. Tag the release
git tag v2.1.0 -m "Phase 2 Tier 3: Robot Performance Analytics"
git push origin v2.1.0

# 2. GitHub Actions auto-builds and pushes image to GHCR
# 3. Staging auto-deploys from main branch (already done)
# 4. Manual approval gate in GitHub Actions environment "production"

# 5. Run database migrations (migration-only task)
aws ecs run-task \
  --cluster production \
  --task-definition scouterfrc-migrate \
  --launch-type FARGATE

# 6. Verify migration succeeded
aws ecs describe-tasks --cluster production --tasks $TASK_ARN \
  | jq '.tasks[0].containers[0].exitCode'  # should be 0

# 7. Deploy new application code
aws ecs update-service --cluster production --service fastapi \
  --force-new-deployment

# 8. Monitor rolling deployment
watch -n 5 "aws ecs describe-services --cluster production --services fastapi \
  | jq '.services[0] | {running: .runningCount, pending: .pendingCount, desired: .desiredCount}'"
```

### Post-Deployment Verification

```bash
# Run smoke tests
pytest tests/smoke/ --base-url https://api.scouterfrc.app

# Check API health
curl -s https://api.scouterfrc.app/health | jq .

# Verify key endpoints
curl -s https://api.scouterfrc.app/api/v1/events?limit=1 | jq '.total'
curl -s https://api.scouterfrc.app/api/v1/teams?limit=1 | jq '.total'

# Monitor Grafana for 15 minutes:
#   - 5xx error rate < 0.1%
#   - p95 latency < 300 ms
#   - No Celery worker crashes
```

### Health Check Procedures

```bash
# Full system health check script
#!/usr/bin/env bash
set -euo pipefail

BASE_URL="https://api.scouterfrc.app"

echo "=== API Health ==="
STATUS=$(curl -sf "$BASE_URL/health" | jq -r '.status')
[[ "$STATUS" == "ok" ]] && echo "✅ API: ok" || echo "❌ API: $STATUS"

echo "=== Database ==="
DB=$(curl -sf "$BASE_URL/health" | jq -r '.database')
[[ "$DB" == "ok" ]] && echo "✅ Database: ok" || echo "❌ Database: $DB"

echo "=== Cache ==="
CACHE=$(curl -sf "$BASE_URL/health" | jq -r '.cache')
[[ "$CACHE" == "ok" ]] && echo "✅ Cache: ok" || echo "❌ Cache: $CACHE"

echo "=== Celery ==="
WORKER_COUNT=$(curl -sf "$BASE_URL/admin/workers" | jq '.active_workers')
echo "Active workers: $WORKER_COUNT"
```

### Rollback Triggers

Immediately roll back if:
- Health check fails after 3 consecutive checks (within 10 min of deploy)
- 5xx rate exceeds 2% for more than 2 minutes
- Critical functionality broken (login, event loading, video upload)
- Database migration caused data corruption

---

## 25. Infrastructure as Code (IaC)

### Tool Selection: Terraform

**Rationale:**
- Provider-agnostic (supports AWS, GCP, DigitalOcean with the same workflow)
- Mature state management with remote backends (S3 + DynamoDB lock)
- Rich module ecosystem for common patterns
- First-class GitHub Actions integration
- Strong community and documentation

**Alternatives considered:**
- **AWS CloudFormation** — AWS-only; verbose YAML; harder to test
- **AWS CDK** — Code-first but AWS-only; good for teams already in the AWS ecosystem
- **Pulumi** — Code-first, provider-agnostic, but smaller community

### Repository Structure

```
infrastructure/
  ├── modules/
  │     ├── vpc/          — VPC, subnets, route tables, security groups
  │     ├── ecs/          — ECS cluster, task definitions, services
  │     ├── rds/          — PostgreSQL instance, parameter groups, snapshots
  │     ├── elasticache/  — Redis cluster / replication group
  │     ├── s3/           — S3 buckets with lifecycle policies
  │     ├── cloudfront/   — CDN distribution
  │     └── iam/          — Roles, policies, OIDC providers
  ├── environments/
  │     ├── staging/
  │     │     ├── main.tf
  │     │     ├── variables.tf
  │     │     └── terraform.tfvars
  │     └── production/
  │           ├── main.tf
  │           ├── variables.tf
  │           └── terraform.tfvars
  ├── .terraform-version   — Terraform version pin (e.g., 1.7.0)
  └── README.md
```

### Configuration Templates

```hcl
# infrastructure/environments/production/main.tf
module "vpc" {
  source      = "../../modules/vpc"
  environment = "production"
  cidr_block  = "10.0.0.0/16"
}

module "rds" {
  source            = "../../modules/rds"
  environment       = "production"
  instance_class    = "db.t3.medium"
  multi_az          = true
  subnet_ids        = module.vpc.database_subnet_ids
  security_group_id = module.vpc.rds_security_group_id
}

module "ecs" {
  source            = "../../modules/ecs"
  environment       = "production"
  image_tag         = var.image_tag
  min_capacity      = 2
  max_capacity      = 8
  subnet_ids        = module.vpc.private_subnet_ids
  security_group_id = module.vpc.ecs_security_group_id
  target_group_arn  = module.alb.target_group_arn
}
```

### Remote State Configuration

```hcl
# infrastructure/environments/production/backend.tf
terraform {
  backend "s3" {
    bucket         = "scouterfrc-terraform-state"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "scouterfrc-terraform-locks"
  }
}
```

### IaC CI/CD Integration

```yaml
# .github/workflows/terraform.yml
name: Terraform

on:
  pull_request:
    paths: ["infrastructure/**"]
  push:
    branches: [main]
    paths: ["infrastructure/**"]

jobs:
  plan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
        with: { terraform_version: "1.7.0" }
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_TERRAFORM_ROLE_ARN }}
          aws-region: us-east-1
      - run: terraform init
        working-directory: infrastructure/environments/production
      - run: terraform plan -out=tfplan
        working-directory: infrastructure/environments/production
      - uses: actions/upload-artifact@v4
        with:
          name: tfplan
          path: infrastructure/environments/production/tfplan

  apply:
    needs: plan
    if: github.ref == 'refs/heads/main'
    environment: production-infrastructure
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with: { name: tfplan }
      - uses: hashicorp/setup-terraform@v3
      - run: terraform apply tfplan
        working-directory: infrastructure/environments/production
```

### Automation Benefits

- Infrastructure changes are code-reviewed via pull requests (same workflow as application code)
- `terraform plan` output in PRs shows exactly what will change before approval
- `terraform apply` is idempotent — re-running is always safe
- Drift detection: `terraform plan` in CI nightly alerts on manual console changes
- Destroy protection: `lifecycle { prevent_destroy = true }` on production database and S3 buckets
