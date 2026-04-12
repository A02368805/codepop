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

## Endpoints & Login

Once stores are running:

- **Store A**: http://localhost:8001
- **Store B**: http://localhost:8002
- **Store C**: http://localhost:8003 (if STORES=3)

### Default Users

After running `make multi-demo`, each store has these accounts (default password: `FloatStack123!`):

**All Stores:**
- Super Admin: `superadmin@floatstack.local` (can see all stores)

**Store A (Region A - Chicago):**
- Logistics Manager: `logistics.a@floatstack.local` (region A - scoped)
- Store Manager: `manager.a001@floatstack.local` (store A001 only)
- Store Admin: `admin.a001@floatstack.local` (store A001 only)

**Store B (Region B - New Jersey/New York):**
- Logistics Manager: `logistics.b@floatstack.local` (region B - scoped)
- Store Manager: `manager.b001@floatstack.local` (store B001 only)
- Store Admin: `admin.b001@floatstack.local` (store B001 only)

**Store C (Region C - Logan, UT):**
- Logistics Manager: `logistics.c@floatstack.local` (region C - scoped)
- Store Manager: `manager.c001@floatstack.local` (store C001 only)
- Store Admin: `admin.c001@floatstack.local` (store C001 only)

### Login Flow

1. Visit http://localhost:8001 (or 8002, 8003)
2. Click "Login"
3. Enter email and password (`FloatStack123!`)
4. For cross-store sync testing, use the Logistics Manager or Super Admin (they see sync events)

### Cross-Store Account User Login (Federated)

Account users can log in to **any store** — even if their account was created on a different store. The system uses **federated authentication**: if a user isn't found locally, other stores are asked to validate the credentials.

**Example (federation path):**
1. Create a new account user on Store A only (not part of seeded demo users).
2. Do not create that user on Store B.
3. Visit http://localhost:8002 and log in with that Store A user.
4. Store B contacts Store A via `POST /peer-validate/` to validate.
5. Store A confirms credentials.
6. Store B provisions a local account record and logs the user in.

This enables order placement across stores while keeping each store's database independent (no shared DB needed).

**Staff roles are not federated**. The peer validation endpoint only accepts `account_user` role, and store/region scoping is enforced through assignment-based permissions.

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
Each node seeds a full registry (all regions, stores, hubs) plus demo users and operational data.

### View logs:
```bash
make multi-logs
```

### Run migrations on all stores:
```bash
make multi-migrate
```

## Demo Data Structure

In distributed mode, `bootstrap_demo_data --reset` seeds:

- All 7 regions and the full multi-store registry
- 7 supply hubs (one per region)
- Scoped users across roles (super admin, logistics managers, store managers/admins, repair staff, account users)
- Inventory balances, machine records, maintenance policies, and sample maintenance work
- Sample transfers, orders, notifications, and CSV-driven import data

This supports both sync transport testing and role/dashboard workflow testing in the same dataset.

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
