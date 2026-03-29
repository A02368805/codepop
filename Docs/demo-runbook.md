# CodePop Demo Runbook

## Goal

Use this sequence when you want a clean end-to-end demo of the canonical Django workspace without guessing which pages matter most.

## Setup

```bash
cp .env.example .env
cd server
../.venv/bin/python manage.py migrate
../.venv/bin/python manage.py bootstrap_demo_data --reset
../.venv/bin/python manage.py runserver 127.0.0.1:8000
```

## Demo Order

1. Open the home page and explain that the active implementation is Django + HTMX with role-scoped dashboards.
2. Sign in as `manager.c001@floatstack.local` and show the manager dashboard, order queue, low-stock alerts, inventory overview, and unread operational notifications.
3. Sign in as `admin.c001@floatstack.local` and show scoped user management, role breakdown, audit activity, and store-scoped governance tools.
4. Sign in as `repair.north@floatstack.local` and show the repair dashboard plus `/maintenance/` for urgent machines, route batches, assignment acknowledge/start/block/complete flows, and seeded maintenance history.
5. Sign in as `logistics.c@floatstack.local` and show the logistics dashboard, `/supply-hubs/`, `/imports/`, and `/sync/` for transfers, AI draft schedules, import outcomes, receiver projections, and logged sync conflicts.
6. Sign in as `superadmin@floatstack.local` and show the super-admin dashboard plus `/analytics/` for cross-region comparisons, revenue, maintenance summaries, sync health, and audit visibility.
7. Finish with an account or guest order flow to show the customer path still works inside the same product shell.

## Suggested Talking Points

- Orders, logistics, maintenance, analytics, and notifications all live in one scoped server-rendered product.
- Outbox events are durable and observable.
- Notifications are real in-app records with unread/read state and device-registration hooks.
- Sync conflicts are intentionally simple: stale events are ignored and logged, while invalid receiver updates are surfaced for review.
- Demo data is seeded from the canonical management command, not from ad hoc fixtures.

## Useful Seeded Accounts

- Customer: `account.casey@floatstack.local`
- Manager: `manager.c001@floatstack.local`
- Admin: `admin.c001@floatstack.local`
- Logistics: `logistics.c@floatstack.local`
- Repair: `repair.north@floatstack.local`
- Super admin: `superadmin@floatstack.local`

Password for all seeded users:

```text
FloatStack123!
```
