## FloatStack Distributed Demo Access (Sanitized)

This document is safe for the public repo and includes only testing/demo access details.

### Demo Nodes

| Node | Hostname | URL | Region | Home Store |
|------|----------|-----|--------|------------|
| Store A | store1-sf3 | http://134.199.222.195:8000 | A (Chicago, IL) | A001 — Chicago Loop |
| Store B | store2-sf3 | http://64.227.100.242:8000 | B (New Jersey/NY) | B001 — Jersey City Exchange |

### App Login Accounts

All app accounts below use password: `FloatStack123!`

**Global (available on both nodes)**

| Email | Role |
|-------|------|
| superadmin@floatstack.local | Super Admin (global, all stores) |

**Per-Store Staff (scoped to their store, seeded on both nodes)**

| Email | Role | Store |
|-------|------|-------|
| manager.a001@floatstack.local | Manager | A001 — Chicago Loop |
| admin.a001@floatstack.local | Admin | A001 — Chicago Loop |
| manager.b001@floatstack.local | Manager | B001 — Jersey City Exchange |
| admin.b001@floatstack.local | Admin | B001 — Jersey City Exchange |
| manager.c001@floatstack.local | Manager | C001 — Logan Main |
| admin.c001@floatstack.local | Admin | C001 — Logan Main |
| manager.d001@floatstack.local | Manager | D001 — Dallas North |
| admin.d001@floatstack.local | Admin | D001 — Dallas North |
| manager.e001@floatstack.local | Manager | E001 — Atlanta Midtown |
| admin.e001@floatstack.local | Admin | E001 — Atlanta Midtown |
| manager.f001@floatstack.local | Manager | F001 — Phoenix Central |
| admin.f001@floatstack.local | Admin | F001 — Phoenix Central |
| manager.g001@floatstack.local | Manager | G001 — Boise Capitol |
| admin.g001@floatstack.local | Admin | G001 — Boise Capitol |
| manager.c002@floatstack.local | Manager | C002 — North Logan Canyon |
| admin.c002@floatstack.local | Admin | C002 — North Logan Canyon |

**Logistics Managers (one per region, seeded on both nodes)**

| Email | Role | Region |
|-------|------|--------|
| logistics.a@floatstack.local | Logistics Manager | A — Chicago |
| logistics.b@floatstack.local | Logistics Manager | B — New Jersey/NY |
| logistics.c@floatstack.local | Logistics Manager | C — Logan, UT |
| logistics.d@floatstack.local | Logistics Manager | D — Dallas, TX |
| logistics.e@floatstack.local | Logistics Manager | E — Atlanta, GA |
| logistics.f@floatstack.local | Logistics Manager | F — Phoenix, AZ |
| logistics.g@floatstack.local | Logistics Manager | G — Boise, ID |

**Repair Staff (Region C, seeded on both nodes)**

| Email | Role | Assigned Stores |
|-------|------|-----------------|
| repair.north@floatstack.local | Repair Staff | C001–C007 |
| repair.metro@floatstack.local | Repair Staff | C008–C014 |
| repair.south@floatstack.local | Repair Staff | C015–C020 |

**Account Users / Customers (can roam between nodes)**

| Email | Role | Preferred Store |
|-------|------|-----------------|
| account.casey@floatstack.local | Account User | C001 — Logan Main |
| account.river@floatstack.local | Account User | C009 — Salt Lake Downtown |
| account.jules@floatstack.local | Account User | F001 — Phoenix Central |
| account.a001@floatstack.local | Account User | A001 — Chicago Loop |
| account.b001@floatstack.local | Account User | B001 — Jersey City Exchange |
| account.c001@floatstack.local | Account User | C001 — Logan Main |
| account.d001@floatstack.local | Account User | D001 — Dallas North |
| account.e001@floatstack.local | Account User | E001 — Atlanta Midtown |
| account.f001@floatstack.local | Account User | F001 — Phoenix Central |
| account.g001@floatstack.local | Account User | G001 — Boise Capitol |
| account.c002@floatstack.local | Account User | C002 — North Logan Canyon |

### Environment Model (Non-Secret Overview)

- Each node runs its own Django + Postgres + Redis + Celery stack.
- Nodes seed the full store/region registry.
- Each node is authoritative for its own home-store operational data.
- Customer identity can be validated across nodes.
- Staff roles are node-local.

### Regions & Stores (seeded on every node)

| Region | Hub City | Primary Store | Total Stores |
|--------|----------|---------------|--------------|
| A | Chicago, IL | A001 — Chicago Loop | 2 |
| B | Jersey City, NJ | B001 — Jersey City Exchange | 2 |
| C | Logan, UT | C001 — Logan Main | 20 |
| D | Dallas, TX | D001 — Dallas North | 2 |
| E | Atlanta, GA | E001 — Atlanta Midtown | 2 |
| F | Phoenix, AZ | F001 — Phoenix Central | 5 |
| G | Boise, ID | G001 — Boise Capitol | 5 |

### Valid `STORE_ID` Values

| STORE_ID | Region | Home Store |
|----------|--------|------------|
| store-a | A | A001 — Chicago Loop |
| store-b | B | B001 — Jersey City Exchange |
| store-c | C | C001 — Logan Main |
| store-d | D | D001 — Dallas North |
| store-e | E | E001 — Atlanta Midtown |
| store-f | F | F001 — Phoenix Central |
| store-g | G | G001 — Boise Capitol |

### Security Note

This file intentionally excludes infrastructure secrets, including:

- Droplet SSH usernames/passwords
- Any SSH private key material
- `SYNC_API_SECRET` and other deployment secrets

Store those in a private secret manager, not in public git.
