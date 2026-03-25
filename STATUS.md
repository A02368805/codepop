# STATUS

## Overall State

The canonical Django + HTMX workspace is demo-ready for the Group 3 operational scope. Maintenance workflows, role dashboards, notifications, analytics, sync/outbox visibility, and demo seeding are all implemented in the active `server/` application path.

## Done

- Completed the Django + HTMX modular-monolith migration and removed the old mobile-first starter from the active workspace
- Implemented the custom user model, strict RBAC, store and region assignments, and role-aware dashboards
- Built the customer flow for landing, store recommendation, menu browsing, customization, favorites, preferences, cart, checkout, confirmation, guest lookup, order history, and recommendation surfaces
- Implemented manager, admin, logistics_manager, repair_staff, and super_admin dashboards with HTMX partial updates
- Added authoritative payment services with `mock` and Stripe-ready modes, refund handling, checkout success/cancel routes, and a Stripe webhook boundary
- Added Celery-backed async foundations for queued CSV imports, outbox sync processing, retry scheduling, notification dispatch hooks, and recommendation refreshes
- Added in-app notifications, sync visibility, analytics summaries, geolocation-assisted store recommendation, and stronger validation/error handling
- Added simulated receiver projections, optimistic version checks, and conflict logging to the sync workspace
- Deepened the manager, admin, repair, analytics, and super-admin surfaces with more real scoped operational data
- Added payment, sync, import, notification, and permission coverage on top of the earlier backend and view tests
- Rebuilt the drink builder around grouped ingredients, live pricing, integrated AI fill, expanded soda/syrup/add-in/ice cream catalogs, and a more polished animated layout
- Reworked customer preferences into structured multi-select taste signals that the AI builder and recommendations now actually consume
- Converted inventory to item-first expandable grouping, fixed selected-store query scoping, and deepened the logistics dashboard with transfer recommendations, health summaries, supplier context, and date-window filtering
- Added a full logistics workspace for creating transfers, approving/reserving/shipping/delivering/receiving them, and placing plus receiving bulk supplier replenishment orders
- Updated Docker Compose to include web, db, redis, worker, and beat
- Updated docs and setup instructions for local dev, Docker, seeds, env vars, and demo workflows
- Added a demo runbook, acceptance checklist, and clearer legacy/cutover documentation for future contributors
- Added explicit deployment notes and a presentation script for final teammate handoff

## Remaining Gaps

- Real production Stripe credentials and end-to-end live payment verification are not bundled in the repo
- Web push and FCM remain integration hooks instead of a full subscription/device delivery system
- External downstream sync targets are still internal placeholders behind the outbox pattern
- Some dashboards can still be refined for accessibility and deeper drill-down views
- The builder AI is deterministic and explainable rather than LLM-backed, which keeps the demo stable but leaves room for future model integration

## Exact Commands To Run The App

### Docker

```bash
cp .env.example .env
docker compose up --build
docker compose exec web python manage.py bootstrap_demo_data --reset
```

### Local Venv

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
cd server
../.venv/bin/python manage.py migrate
../.venv/bin/python manage.py bootstrap_demo_data --reset
../.venv/bin/python manage.py runserver 127.0.0.1:8000
```

### Optional Local Async Workers

```bash
redis-server
cd server
CELERY_TASK_ALWAYS_EAGER=False ../.venv/bin/celery -A config worker -l info
CELERY_TASK_ALWAYS_EAGER=False ../.venv/bin/celery -A config beat -l info
```
