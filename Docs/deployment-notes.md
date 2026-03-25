# CodePop Deployment Notes

## Supported Local Paths

### Docker

```bash
cp .env.example .env
docker compose up --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py bootstrap_demo_data --reset
```

### Local Virtualenv

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

## Runtime Notes

- `PAYMENT_MODE=mock` is the safe demo default.
- SQLite works for quick local runs, but PostgreSQL is still the intended shared-environment target.
- Local development defaults to eager Celery execution unless `CELERY_TASK_ALWAYS_EAGER=False`.
- When async workers are enabled, run Redis plus Celery worker and beat.

## Production-Shaped Boundaries

- Stripe checkout and webhook handling are implemented, but live credentials are not committed.
- Sync/outbox processing is observable and policy-driven, but downstream external connectors are still placeholders.
- Device registration and push delivery hooks exist, but live FCM/web-push delivery is not configured here.

## Recommended Demo Configuration

- Use `DEBUG=True` locally.
- Keep `PAYMENT_MODE=mock`.
- Seed with `bootstrap_demo_data --reset` before demos so dashboards, notifications, maintenance queues, sync projections, and analytics are all populated.
