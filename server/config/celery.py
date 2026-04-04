import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("codepop")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
app.conf.beat_schedule = {
    "process-pending-sync-events": {
        "task": "apps.sync.tasks.process_pending_outbox_events_async",
        "schedule": 60.0,
        "args": (25,),
    },
    "process-stranded-sync-events-nightly": {
        "task": "apps.sync.tasks.retry_failed_outbox_events_async",
        "schedule": crontab(minute=0, hour="*/6"),
        "args": (100,),
    },
    "retry-failed-peer-deliveries": {
        "task": "apps.sync.tasks.retry_failed_peer_deliveries_async",
        "schedule": crontab(minute="*/5"),
    },
}
