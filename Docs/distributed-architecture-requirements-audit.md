# Distributed Architecture Requirements Audit

Date: 2026-04-12

## Scope

This audit compares:

- required behavior from `Docs/RequirementsDoc_Rewritten.md`
- documented deployment behavior from `/Users/gabrielnielsen/Desktop/digitalOceanPass.md` and `Docs/claude/DISTRIBUTED_TESTING.md`
- implemented behavior from code/config in `server/`, `.env.multi`, and `docker-compose.multi.yml`

## Requirement Matrix (Distributed Focus)

| Requirement | Status | Evidence | Notes |
|---|---|---|---|
| Multi-store support across US | Meets | `Docs/RequirementsDoc_Rewritten.md` (lines 366, 370), `server/apps/users/management/commands/bootstrap_demo_data.py` (lines 61-111, 598-603), `tests.test_seed` result: `7 regions, 38 stores, 7 hubs` | Seeder and data model cover nationwide multi-store dataset. |
| No single centralized server; stores operate independently | Meets | `Docs/RequirementsDoc_Rewritten.md` (line 367), `docker-compose.multi.yml` (lines 15-25, 86-97, 165-176), `Docs/claude/DISTRIBUTED_TESTING.md` (lines 121-127) | Each node has its own DB/app/worker path. |
| Direct inter-store communication | Meets | `Docs/RequirementsDoc_Rewritten.md` (line 367), `server/apps/sync/views.py` (lines 198-231), `server/apps/sync/services.py` (lines 858-970) | Peer push + ingest implemented with authenticated machine endpoints. |
| Sync includes inventory/supply/maintenance data | Partial | `Docs/RequirementsDoc_Rewritten.md` (lines 368-369), `server/apps/inventory/services.py` (transfer/supplier events lines 432-802), `server/apps/maintenance/services.py` (machine/repair events lines 249-257, 312-317, 513-518) | Supply and maintenance are explicitly synchronized. Inventory-level updates are indirect via transfer/replenishment flows; direct inventory adjustment sync is not explicit. |
| Seven predefined supply-hub regions | Meets | `Docs/RequirementsDoc_Rewritten.md` (line 370), `server/apps/users/management/commands/bootstrap_demo_data.py` (lines 61-111, 598-603) | Seven region and hub definitions are seeded. |
| Account users can access from any store | Meets | `Docs/RequirementsDoc_Rewritten.md` (line 411), `server/apps/users/backends.py` (lines 58-119), `server/apps/users/views.py` (lines 1064-1121), `server/tests/test_peer_store_auth.py` | Federated account login exists and tests pass. |
| Staff access is role/scoped | Meets | `Docs/RequirementsDoc_Rewritten.md` (lines 383-409), `server/apps/users/permissions.py` (lines 121-228), `server/apps/maintenance/services.py` (lines 643-675), `server/tests/test_rbac.py` | Store/region assignments enforce role scope. |
| Conflict detection and safe resolution | Meets | `Docs/RequirementsDoc_Rewritten.md` (line 526), `server/apps/sync/services.py` (lines 169-217, 279-350), `Docs/deployment-notes.md` (line 54), `server/tests/test_sync.py` | Sync conflict logs + resolve/ignore controls implemented and tested. |
| Eventual consistency of inventory/supply/maintenance data within region | Partial | `Docs/RequirementsDoc_Rewritten.md` (line 527), `server/apps/sync/services.py` (lines 895-907, 973-990), `server/tests/test_sync.py` (dedup/retry tests) | Retry/backoff and idempotent ingest exist, but no explicit region-level consistency SLO/verification criterion is documented. |
| Inter-store communication must be authenticated and encrypted | Partial | `Docs/RequirementsDoc_Rewritten.md` (line 506), `server/apps/sync/views.py` (lines 209-216), `server/apps/users/views.py` (lines 1083-1089), `/Users/gabrielnielsen/Desktop/digitalOceanPass.md` (lines 11-12, 123-124) | Authenticated (`X-Sync-Token`) is implemented; docs currently show `http://` endpoints, so encrypted transport is not guaranteed by current deployment rules. |
| Sensitive data encrypted in transit and at rest | Gap | `Docs/RequirementsDoc_Rewritten.md` (line 504), `/Users/gabrielnielsen/Desktop/digitalOceanPass.md` (lines 16-20, 24) | Deployment doc includes plaintext passwords and no at-rest encryption controls. |

## Documentation Consistency Corrections Applied

The deployment rules doc `Docs/claude/DISTRIBUTED_TESTING.md` was corrected to match implementation:

- endpoint path corrected to `POST /peer-validate/`
- staff auth wording updated to "not federated" with scope enforcement
- seeding model corrected from "per-store only" to actual full-registry/demo seeding behavior

## Live Droplet Verification (2026-04-12)

Live checks were run against:

- Store A: `http://134.199.222.195:8000`
- Store B: `http://64.227.100.242:8000`

Observed results:

- `GET /sync/health/` on both nodes returns `200`, with correct node IDs (`store-a`, `store-b`) and `sync_enabled=true`.
- Authenticated `GET /sync/health/` on both nodes reports peer reachability as `false`.
- `POST /peer-validate/` behaves correctly:
  - account user returns `{"valid": true, ...}`
  - manager user returns `{"valid": false}`
- `https://<ip>:8000/sync/health/` fails TLS handshake on both nodes (no working TLS listener on that endpoint).
- Store B had `codepop-worker-1` exited (`Exited (1) 11 hours ago`), leaving reverse-direction async sync pushes stuck.

### Live Sync Propagation Test

Bidirectional event flow was validated directly on droplets:

- Store A -> Store B:
  - baseline on B for `origin_node_id='store-a', event_type='test.ping'`: `0`
  - created/processed controlled `test.ping` event on A
  - count on B became `1`
- Store B -> Store A:
  - baseline on A for `origin_node_id='store-b', event_type='test.pong'`: `0`
  - created/processed controlled `test.pong` event on B
  - delivery on B stayed `pending` while worker was down
  - restarted Store B worker (`docker compose up -d worker`)
  - delivery transitioned to `delivered`, and count on A became `1`

### Peer Health False-Negative Note

The `peers.reachable=false` result on authenticated `/sync/health/` is currently a recursive-health behavior artifact:

- authenticated health check on node A calls node B with auth token
- node B then performs its own authenticated peer check back to node A
- repeated nested checks hit timeout and report `reachable=false`

So `peers.reachable=false` should not be treated as definitive outage without direct host/container connectivity checks.

### Droplet-Level Verdict

The droplets are partially aligned with distributed architecture:

- Node identity, role federation rules, and machine auth endpoints are in place.
- Bidirectional sync is now functioning after worker recovery on Store B.
- Health endpoint peer status is currently noisy/false-negative due to recursive authenticated peer checks.
- Transport encryption requirement is not met on the exposed droplet endpoints (HTTP only on tested interface).

## Priority Gaps To Close

1. Enforce TLS for node URLs and sync endpoints in production deployment rules.
2. Remove plaintext credentials from deployment docs and move to secret management.
3. Add process supervision/auto-restart alerting for Celery worker health on each node.
4. Fix `NodeHealthView` peer-check recursion so peer reachability reflects true connectivity.
5. Define and test explicit eventual-consistency acceptance criteria for inventory/supply/maintenance sync.
6. Decide whether direct inventory-level synchronization (beyond transfer/replenishment events) is required, and implement/document accordingly.
