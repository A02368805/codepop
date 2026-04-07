from __future__ import annotations

from celery import shared_task

from .services import process_import_job


@shared_task
def process_import_job_async(import_job_id, csv_text):
    return process_import_job(import_job_id=import_job_id, csv_text=csv_text)
