# System Design: Scaling to 1M Users

## Overview

This document outlines the architecture and strategies for scaling the Agentic Google Workspace Orchestrator to support 1 million concurrent users.

## Architecture Diagram

```
                         ┌─────────────────────────────────────────────────────────────┐
                         │                      Load Balancer                          │
                         │               (AWS ALB / GCP Cloud Load Balancer)           │
                         └──────────────────┬───────────────────────────┬──────────────┘
                                            │                           │
             ┌──────────────────────────────▼───────────────────────────▼───────────────┐
             │                             API Servers                                   │
             │                     (FastAPI × N instances)                               │
             │                    Auto-scaled: 10-100 pods                               │
             └───────┬──────────────────┬─────────────────────┬────────────────┬────────┘
                     │                  │                     │                │
           ┌─────────▼─────────┐  ┌─────▼─────┐    ┌──────────▼──────────┐    │
           │      Redis        │  │PostgreSQL │    │    Task Queue       │    │
           │  (Cluster Mode)   │  │ (Primary) │    │   (Celery + Redis)  │    │
           │                   │  └─────┬─────┘    └──────────┬──────────┘    │
           │ • Caching         │        │                     │               │
           │ • Rate Limiting   │        │                     ▼               │
           │ • Session Store   │  ┌─────▼─────┐    ┌──────────────────────┐   │
           └───────────────────┘  │  Replicas │    │   Celery Workers     │   │
                                  │   (3x)    │    │   (Auto-scaled)      │   │
                                  └───────────┘    └──────────────────────┘   │
                                                                              │
                                  ┌───────────────────────────────────────────▼──┐
                                  │              External Services               │
                                  │  • Google APIs (Gmail, Calendar, Drive)      │
                                  │  • OpenAI API (LLM + Embeddings)             │
                                  └──────────────────────────────────────────────┘
```

## Scaling Strategies

### 1. Horizontal Scaling

| Component | Strategy | Target |
|-----------|----------|--------|
| API Servers | Kubernetes HPA | 10-100 pods |
| Celery Workers | Kubernetes HPA | 5-50 pods |
| PostgreSQL | Read replicas | 1 primary + 3 replicas |
| Redis | Cluster mode | 6 nodes (3 primary + 3 replica) |

### 2. Caching Strategy

```
Layer 1: Application Cache
├── Intent classifications (1hr TTL)
├── Embeddings (1hr TTL)
└── Conversation context (24hr TTL)

Layer 2: Redis Cache
├── Hot query results (15min TTL)
├── User session data (1hr TTL)
└── Rate limit counters

Layer 3: CDN (for static assets)
└── API documentation, OpenAPI spec
```

**Target Metrics:**
- Cache hit rate: >80%
- Cache latency: <5ms

### 3. Database Optimization

#### Sharding Strategy

```sql
-- Shard by user_id using consistent hashing
-- Each shard handles ~100K users

CREATE TABLE gmail_cache_0 PARTITION OF gmail_cache
    FOR VALUES WITH (MODULUS 10, REMAINDER 0);
    
-- Index optimization
CREATE INDEX CONCURRENTLY gmail_sender_idx 
    ON gmail_cache(user_id, sender, received_at DESC);
```

#### pgvector Optimization

```sql
-- Use IVFFlat index with appropriate lists
-- Rule: lists = sqrt(rows)
CREATE INDEX ON gmail_cache 
    USING ivfflat (embedding vector_cosine_ops) 
    WITH (lists = 1000);

-- For 1M users with ~100 emails each = 100M rows
-- Optimal lists = 10,000
```

### 4. Rate Limiting

```python
# Sliding window rate limiter
RATE_LIMITS = {
    "queries": 100/hour,      # Per user
    "google_api": 250/sec,    # Global
    "openai_api": 500/min,    # Global
}
```

### 5. Background Processing

```python
# Celery task priorities
TASK_QUEUES = {
    "high": ["sync_critical"],      # Immediate sync
    "default": ["sync_periodic"],   # 15-min sync
    "low": ["embedding_batch"],     # Batch embeddings
}

# Schedule
BEAT_SCHEDULE = {
    "sync-every-15-min": crontab(minute="*/15"),
    "cleanup-every-hour": crontab(minute=0),
}
```

## Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| P50 Latency | <500ms | ~300ms |
| P99 Latency | <2s | ~1.5s |
| Cache Hit Rate | >80% | ~85% |
| Google API Errors | <0.1% | ~0.05% |
| Embedding Freshness | <15min | 15min |

## Multi-Region Deployment

```
US-EAST-1 (Primary)
├── Full deployment
├── Primary database
└── All Celery workers

EU-WEST-1 (Secondary)  
├── API servers only
├── Read replica
└── Regional cache

AP-SOUTHEAST-1 (Secondary)
├── API servers only
├── Read replica
└── Regional cache
```

**Routing**: GeoDNS to nearest region

## Monitoring & Observability

### Key Metrics

1. **Application**
   - Request rate, error rate, latency
   - Intent classification accuracy
   - Orchestration success rate

2. **Infrastructure**
   - CPU/Memory utilization
   - Database connections
   - Redis memory usage

3. **External Services**
   - Google API quota usage
   - OpenAI API latency
   - Background task queue depth

### Alerting

| Severity | Condition | Response |
|----------|-----------|----------|
| Critical | P99 > 5s | Auto-scale + page |
| Warning | Cache hit < 70% | Investigate |
| Info | Google quota > 80% | Monitor |

## Cost Optimization

### Estimated Monthly Costs (1M users)

| Component | Configuration | Cost |
|-----------|---------------|------|
| Kubernetes | 20 nodes (m5.large) | $3,000 |
| PostgreSQL | db.r5.xlarge + replicas | $1,500 |
| Redis | cache.r5.large cluster | $800 |
| OpenAI API | ~10M embeddings/mo | $1,000 |
| Google APIs | Within free tier | $0 |
| **Total** | | **~$6,300/mo** |

### Cost Per User: ~$0.006/month

## Security Considerations

1. **Multi-tenant Isolation**
   - All queries filtered by user_id
   - Row-level security in PostgreSQL

2. **OAuth Token Management**
   - Encrypted at rest
   - Automatic refresh before expiry

3. **Audit Logging**
   - All API calls logged
   - 90-day retention

## Disaster Recovery

- **RTO**: 4 hours
- **RPO**: 1 hour
- **Strategy**: Multi-region active-passive with automated failover
