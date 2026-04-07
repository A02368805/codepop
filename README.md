# FloatStack

FloatStack is a Django-first, web-first implementation of the rewritten beverage-operations architecture. The active product uses server-rendered templates, HTMX partials, strict server-side RBAC, PostgreSQL-ready configuration, and background jobs for imports, notifications, sync processing, and recommendation refreshes.

The rewritten design documents remain the source of truth:

- `Docs/CodePop_High_Level_Design_Rewritten.md`
- `Docs/CodePop_Low_Level_Design_Rewritten.md`
- `Docs/RequirementsDoc_Rewritten.md`

The old Expo/mobile starter is archived under `legacy/` and is no longer the primary architecture.

## Architecture Summary

- Django 5 modular monolith under `server/apps/`
- HTMX-driven server-rendered UI, not a SPA
- Session authentication with a custom user model
- Server-enforced role and scope boundaries for `account_user`, `manager`, `admin`, `logistics_manager`, `repair_staff`, and `super_admin`
- PostgreSQL as the primary runtime target with SQLite fallback for quick local development
- Celery + Redis for queued imports, outbox sync processing, notification dispatch hooks, and recommendation refreshes
- Stripe-ready payment boundary with a robust `mock` demo mode
- In-app notifications, analytics summaries, audit logs, and outbox sync visibility

## Repo Layout

```text
server/
├── apps/
│   ├── analytics/
│   ├── imports/
│   ├── inventory/
│   ├── maintenance/
│   ├── notifications/
│   ├── orders/
│   ├── payments/
│   ├── stores/
│   ├── supply_hubs/
│   ├── sync/
│   └── users/
├── config/
│   ├── settings/
│   ├── urls.py
│   └── celery.py
├── seed/
├── static/
├── templates/
└── tests/
Docs/
```

## Quick Start With Docker

1. Copy the environment template.

```bash
cp .env.example .env
```

2. Start the web app, PostgreSQL, Redis, Celery worker, and Celery beat.

```bash
docker compose up --build
```

3. Seed the demo dataset.

```bash
docker compose exec web python manage.py bootstrap_demo_data --reset
```

4. Open the product.

```text
http://127.0.0.1:8000/
```

## Local Setup Without Docker

The local fallback uses SQLite unless `DATABASE_URL` is set. That is fine for demo work and template iteration. PostgreSQL remains the intended target for shared environments and Docker runs.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
pre-commit install
cd server
../.venv/bin/python manage.py migrate
../.venv/bin/python manage.py bootstrap_demo_data --reset
../.venv/bin/python manage.py runserver 127.0.0.1:8000
```

Or run the setup script which handles everything except starting the server:

```bash
./setup.sh
```

Local dev defaults to `CELERY_TASK_ALWAYS_EAGER=True`, so imports, notifications, and recommendation refreshes run inline unless you explicitly switch to worker-backed execution.

## Background Jobs

When you want real async behavior locally, set `CELERY_TASK_ALWAYS_EAGER=False` and run Redis, a worker, and beat:

```bash
redis-server
cd server
../.venv/bin/celery -A config worker -l info
../.venv/bin/celery -A config beat -l info
```

Background tasks currently cover:

- CSV import processing
- outbox sync processing and retries
- notification dispatch hooks
- account recommendation refreshes after preference updates and orders

## Environment Variables

Core variables:

- `DJANGO_SETTINGS_MODULE`
- `SECRET_KEY`
- `DEBUG`
- `TIME_ZONE`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `DATABASE_URL`

Background job variables:

- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `CELERY_TASK_ALWAYS_EAGER`
- `CELERY_TASK_TIME_LIMIT`

Seed/demo variables:

- `SEED_USER_PASSWORD`

Payment variables:

- `PAYMENT_MODE` with `mock` or `stripe`
- `PAYMENT_CHECKOUT_FLOW` with `hosted` or `elements`
- `STRIPE_SECRET_KEY`
- `STRIPE_PUBLISHABLE_KEY`
- `STRIPE_WEBHOOK_SECRET`

AI provider variables:

- `AI_RECOMMENDATION_PROVIDER` with `deterministic`, `mock-external`, or `anthropic`
- `ANTHROPIC_API_KEY`
- `ANTHROPIC_MODEL`
- `ANTHROPIC_API_BASE_URL`
- `AI_PROVIDER_TIMEOUT_SECONDS`
- `AI_PROVIDER_MAX_RETRIES`

Location and notification hook variables:

- `MAPBOX_PUBLIC_TOKEN`
- `FCM_SERVER_KEY`
- `WEB_PUSH_PUBLIC_KEY`
- `WEB_PUSH_PRIVATE_KEY`

## Payment Modes

- `PAYMENT_MODE=mock` is the safest default for demos and local setup. Server-side pricing still runs, but checkout completes immediately without an external processor.
- `PAYMENT_MODE=stripe` enables the Stripe checkout boundary and webhook route. Add real Stripe credentials before using it.
- `PAYMENT_CHECKOUT_FLOW=hosted` uses Stripe-hosted checkout redirect.
- `PAYMENT_CHECKOUT_FLOW=elements` keeps card entry inside the app with Stripe Elements + PaymentIntents.
- Client-submitted totals are never trusted. Order pricing is recalculated on the server before payment records are written.

### Keys-Last Activation Checklist

1. Keep defaults during development: `PAYMENT_MODE=mock`, `AI_RECOMMENDATION_PROVIDER=deterministic`.
2. Set Stripe test credentials and webhook secret.
3. Switch `PAYMENT_MODE=stripe` and choose `PAYMENT_CHECKOUT_FLOW=elements` (or `hosted`).
4. Set Anthropic settings and switch `AI_RECOMMENDATION_PROVIDER=anthropic`.
5. Run focused tests, then perform one checkout smoke test and one recommendation smoke test.
6. Run `python manage.py prelive_integrations_check` to validate launch configuration.

## Seed Data And Demo Credentials

`python manage.py bootstrap_demo_data --reset` creates the full demo dataset, including 7 documented regions, 7 hubs, 38 stores, account users, store staff, regional logistics users, repair staff, seeded imports, transfers, maintenance events, notifications, sync events, and demo orders.

All seeded users use `SEED_USER_PASSWORD`, which defaults to:

```text
FloatStack123!
```

Useful demo logins:

- Customer: `account.casey@floatstack.local`
- Customer: `account.river@floatstack.local`
- Manager: `manager.c001@floatstack.local`
- Admin: `admin.c001@floatstack.local`
- Logistics manager: `logistics.c@floatstack.local`
- Repair staff: `repair.north@floatstack.local`
- Super admin: `superadmin@floatstack.local`

Seeded guest lookup example:

- Order code: `FS-M5K9TD`
- Pickup combo: `624`
- Guest lookup code: `GST-DEMO-001`

## Sample Demo Walkthroughs

### 1. Guest Order

1. Open `/stores/`.
2. Pick a store or use the geolocation-assisted recommendation form.
3. Add a drink to the cart.
4. Check out as a guest.
5. Re-open the order through `/orders/guest-lookup/`.

### 2. Account User Order

1. Sign in as `account.casey@floatstack.local`.
2. Visit recommendations, favorites, or preferences.
3. Place an order from any store.
4. View status and order history from the customer workspace.

### 3. Manager Workflow

1. Sign in as `manager.c001@floatstack.local`.
2. Open the manager dashboard.
3. Move queued orders forward.
4. Review revenue and inventory.
5. Adjust a scoped inventory row with HTMX.

### 4. Logistics Workflow

1. Sign in as `logistics.c@floatstack.local`.
2. Open Supply Hubs, Imports, Sync, and Analytics.
3. Upload a supply usage CSV.
4. Approve AI-generated supply schedule drafts.
5. Review pending transfers and outbox visibility.

### 5. Repair Workflow

1. Sign in as `repair.north@floatstack.local`.
2. Open Maintenance and Imports.
3. Review urgent machine assignments.
4. Upload a maintenance CSV and inspect the resulting queue.

### 6. Super Admin Oversight

1. Sign in as `superadmin@floatstack.local`.
2. Open the system-wide dashboard.
3. Review analytics, scoped user oversight, audit visibility, sync health, and operations comparisons.

## Commands

Run migrations:

```bash
cd server
../.venv/bin/python manage.py migrate
```

Seed demo data:

```bash
cd server
../.venv/bin/python manage.py bootstrap_demo_data --reset
```

Run tests:

```bash
cd server
../.venv/bin/python manage.py test
```

Run Django checks:

```bash
cd server
../.venv/bin/python manage.py check
```

Run integrations readiness check:

```bash
cd server
../.venv/bin/python manage.py prelive_integrations_check --allow-warnings
```

Run the dev server:

```bash
cd server
../.venv/bin/python manage.py runserver 127.0.0.1:8000
```

## Docs

Implementation notes and migration details live in:

- `Docs/migration-plan.md`
- `Docs/demo-readiness.md`
- `STATUS.md`

Duplicate lowercase copies exist under `docs/` for compatibility with the original repo layout.

## Known Limitations

- Stripe support is production-shaped, but this repo still defaults to `mock` mode because no live keys are committed.
- Web push and FCM are exposed as hooks, not as a full subscription/device-management system.
- Geolocation uses browser coordinates with server-side distance heuristics. Real map-provider features can be layered in later via `MAPBOX_PUBLIC_TOKEN`.
- The sync pipeline is intentionally internal and observable, but it does not yet push to external downstream systems.
- Demo analytics are useful and seeded, but they are not a BI replacement.
