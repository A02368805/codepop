# Multi-Store Distributed Testing Guide

This document describes how to test the distributed multi-store sync system locally.

## Quick Start

### Run 2 stores (Store A + B):
```bash
make multi-up
```

### Run 3 stores (Store A + B + C):
```bash
make multi-up STORES=3
```

### Stop all stores:
```bash
make multi-down
```

## Endpoints

Once stores are running:

- **Store A**: http://localhost:8001
- **Store B**: http://localhost:8002
- **Store C**: http://localhost:8003 (if STORES=3)

## Database Access

Each store has its own PostgreSQL database:

- Store A: `postgresql://codepop:codepop@localhost:5433/codepop_store_a`
- Store B: `postgresql://codepop:codepop@localhost:5434/codepop_store_b`
- Store C: `postgresql://codepop:codepop@localhost:5435/codepop_store_c`

## Useful Commands

### Seed demo data across all stores:
```bash
make multi-demo
```
Each store only seeds its own region and store (no fake cross-region data).

### View logs:
```bash
make multi-logs
```

### Run migrations on all stores:
```bash
make multi-migrate
```

## Demo Data Structure

In distributed mode, **each store instance seeds ONLY its own data**:

- **Store A** → Region A (Chicago, IL) with Store A001
- **Store B** → Region B (New Jersey / New York) with Store B001
- **Store C** → Region C (Logan, UT) with Store C001

Users are created per-store:
- 1 Logistics Manager (scoped to region)
- 1 Super Admin
- 1 Store Manager
- 1 Store Admin

No orders, transfers, machines, or inter-store dependencies are seeded in distributed mode — the focus is on testing sync infrastructure, not demo workflows.

## How Distributed Sync Works

### Architecture

Each store runs as:
- `web_a` / `web_b` / `web_c` — Django application
- `worker_a` / `worker_b` / `worker_c` — Celery worker for async tasks
- `beat_a` / `beat_b` / `beat_c` — Celery beat scheduler
- `db_a` / `db_b` / `db_c` — PostgreSQL database
- Shared `redis` — Celery message broker

### Sync Flow

1. **Local Event Creation**: Action on Store A creates `SyncOutboxEvent`
2. **Local Processing**: Celery worker applies projections/conflicts locally
3. **Peer Push**: After local success, event is POSTed to Store B and C
4. **Inbound Ingest**: Peer stores receive event via `POST /sync/ingest/`
5. **Deduplication**: Idempotent by `(origin_node_id, remote_event_id)`
6. **Retry Logic**: Failed deliveries retry with exponential backoff

### Configuration

Multi-store environment (`.env.multi`):
```
SYNC_API_SECRET=multi-dev-secret-change-me-in-production  # Shared between all stores
SYNC_PUSH_ENABLED=True  # Enable HTTP peer push
```

Per-store configuration set in `docker-compose.multi.yml`:
```
STORE_ID=store-a
PEER_STORES=store-b=http://web_b:8000,store-c=http://web_c:8000
```

## Testing Sync Manually

1. Open Store A at http://localhost:8001
2. Create an order or transfer
3. Check Store B sync dashboard at http://localhost:8002/sync/
4. Verify the event appears in the sync projection state

## Testing Programmatically

Unit tests verify:
- Ingest endpoint auth (X-Sync-Token validation)
- Event deduplication (same event idempotent)
- Peer delivery creation
- Loop prevention (events from peers don't re-push)

Run tests:
```bash
make test
```

Or just the sync tests:
```bash
docker compose exec -e DJANGO_SETTINGS_MODULE=config.settings.test web python manage.py test tests.test_sync
```

## Production Deployment

The docker-compose setup mirrors production deployment:

```
Production:
  Store A (store-a.example.com)
  ├─ Django app
  ├─ PostgreSQL (codepop_store_a)
  └─ Celery worker

  Store B (store-b.example.com)
  ├─ Django app
  ├─ PostgreSQL (codepop_store_b)
  └─ Celery worker

  Shared infrastructure (Redis at redis.example.com)
```

In production, each store is deployed independently but uses the same:
- `SYNC_API_SECRET` (shared HMAC token)
- `PEER_STORES` configuration (list of other store URLs)
- Database credentials (per-store)
- Environment variables from `.env.multi` pattern

## Troubleshooting

### Events not syncing?

1. Check sync dashboard: http://localhost:8001/sync/
2. Verify peer_deliveries status (pending/delivered/failed)
3. Check logs: `docker compose -f docker-compose.multi.yml logs worker_a`
4. Verify `SYNC_PUSH_ENABLED=True` in `.env.multi`

### Authentication errors (401)?

- Ensure `SYNC_API_SECRET` is set in `.env.multi`
- Both endpoints check: `X-Sync-Token` header must match secret

### Database connection errors?

- Check `DATABASE_URL` per store (set in docker-compose.multi.yml)
- Postgres containers: `db_a`, `db_b`, `db_c` are running
- Default credentials: `codepop:codepop`

## Implementation Details

### New Models

- `SyncPeerDelivery` — tracks per-peer event delivery (pending/delivered/failed)

### New Fields

- `SyncOutboxEvent.origin_node_id` — marks which node created the event
- `SyncOutboxEvent.remote_event_id` — original UUID from peer node (for dedup)

### New Endpoints

- `POST /sync/ingest/` — machine-to-machine endpoint for peer event ingestion

### New Celery Tasks

- `push_pending_peer_deliveries_async(event_id)` — sends event to all peer nodes
- `retry_failed_peer_deliveries_async()` — runs every 5 minutes to retry failed sends

## References

- **Implementation Plan**: `/home/curt/.claude/plans/enchanted-giggling-kernighan.md`
- **LLD Section 7.2**: `Docs/CodePop_Low_Level_Design_Rewritten.md` (Synchronization Architecture)
- **Tests**: `server/tests/test_sync.py` (SyncPeerTransportTests class)
