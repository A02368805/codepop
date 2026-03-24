# STATUS

## Overall State

Prompt 4 is effectively complete for demo readiness. The active repo now matches the rewritten Django + HTMX architecture, includes the core domain model and dashboards, and is runnable with seeded demo data, background-job hooks, payment modes, analytics, and integration-oriented tests. The latest polish pass also upgraded the customer builder, multi-select taste preferences, grouped inventory UX, richer logistics operations, builder-native AI fill behavior, and a real logistics workflow for transfer creation plus supplier ordering and receipt.

## Done

- Completed the Django + HTMX modular-monolith migration and kept the old mobile-first starter archived under `legacy/`
- Implemented the custom user model, strict RBAC, store and region assignments, and role-aware dashboards
- Built the customer flow for landing, store recommendation, menu browsing, customization, favorites, preferences, cart, checkout, confirmation, guest lookup, order history, and recommendation surfaces
- Implemented manager, admin, logistics_manager, repair_staff, and super_admin dashboards with HTMX partial updates
- Added authoritative payment services with `mock` and Stripe-ready modes, refund handling, checkout success/cancel routes, and a Stripe webhook boundary
- Added Celery-backed async foundations for queued CSV imports, outbox sync processing, retry scheduling, notification dispatch hooks, and recommendation refreshes
- Added in-app notifications, sync visibility, analytics summaries, geolocation-assisted store recommendation, and stronger validation/error handling
- Added payment, sync, import, notification, and permission coverage on top of the earlier backend and view tests
- Rebuilt the drink builder around grouped ingredients, live pricing, integrated AI fill, expanded soda/syrup/add-in/ice cream catalogs, and a more polished animated layout
- Reworked customer preferences into structured multi-select taste signals that the AI builder and recommendations now actually consume
- Converted inventory to item-first expandable grouping, fixed selected-store query scoping, and deepened the logistics dashboard with transfer recommendations, health summaries, supplier context, and date-window filtering
- Added a full logistics workspace for creating transfers, approving/reserving/shipping/delivering/receiving them, and placing plus receiving bulk supplier replenishment orders
- Updated Docker Compose to include web, db, redis, worker, and beat
- Updated docs and setup instructions for local dev, Docker, seeds, env vars, and demo workflows

## Remaining Gaps

- Real production Stripe credentials and end-to-end live payment verification are not bundled in the repo
- Web push and FCM remain integration hooks instead of a full subscription/device delivery system
- External downstream sync targets are still internal placeholders behind the outbox pattern
- Some dashboards can still be refined for accessibility, richer drill-downs, and broader production observability
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
