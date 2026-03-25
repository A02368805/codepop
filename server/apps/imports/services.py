from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from io import StringIO

from apps.inventory.models import InventoryItem, SupplyUsageRecord
from apps.inventory.services import draft_supply_schedule_from_usage
from apps.maintenance.models import Machine, MachineType
from apps.maintenance.services import (
    append_machine_status_event,
    evaluate_warning_escalation,
)
from apps.notifications.models import Notification
from apps.notifications.services import notify_user
from apps.stores.models import Store
from apps.sync.services import create_audit_log, create_outbox_event, serialize_instance
from apps.users.permissions import user_has_region_scope, user_has_store_scope
from django.db import transaction
from django.utils import timezone

from .models import ImportJob

SUPPLY_USAGE_HEADERS = ["store_code", "inventory_sku", "usage_date", "quantity_used"]
REPAIR_STATUS_HEADERS = [
    "store_address",
    "machine_type_code",
    "machine_operational_from_date",
    "machine_status",
    "status_date",
]


class CSVImportError(Exception):
    def __init__(self, errors):
        super().__init__("CSV import failed validation.")
        self.errors = errors


@dataclass(frozen=True)
class ParsedSupplyUsageRow:
    store: Store
    inventory_item: InventoryItem
    usage_date: date
    quantity_used: Decimal


@dataclass(frozen=True)
class ParsedRepairStatusRow:
    store: Store
    machine_type: MachineType
    operational_from_date: date
    machine_status: str
    status_date: date


def _read_rows(csv_text):
    return csv.DictReader(StringIO(csv_text.strip()))


def _exact_headers(reader, expected_headers):
    if reader.fieldnames != expected_headers:
        raise CSVImportError(
            [
                {
                    "row": 1,
                    "field": "headers",
                    "message": f"Expected headers {expected_headers} but received {reader.fieldnames}.",
                }
            ]
        )


def _build_store_address_lookup(store):
    return f"{store.address_line_1} {store.city} {store.state_code}".lower()


def parse_supply_usage_csv(csv_text, *, uploaded_by):
    reader = _read_rows(csv_text)
    _exact_headers(reader, SUPPLY_USAGE_HEADERS)
    errors = []
    parsed_rows = []

    for row_number, row in enumerate(reader, start=2):
        try:
            store = Store.objects.get(store_code=row["store_code"])
            if not user_has_region_scope(uploaded_by, store.region):
                raise ValueError("Store is outside the user's regional scope.")
            inventory_item = InventoryItem.objects.get(sku=row["inventory_sku"])
            usage_date = date.fromisoformat(row["usage_date"])
            quantity_used = Decimal(row["quantity_used"])
            if quantity_used <= 0:
                raise ValueError("Quantity used must be positive.")
            parsed_rows.append(
                ParsedSupplyUsageRow(
                    store=store,
                    inventory_item=inventory_item,
                    usage_date=usage_date,
                    quantity_used=quantity_used,
                )
            )
        except Exception as exc:
            errors.append({"row": row_number, "message": str(exc)})

    if errors:
        raise CSVImportError(errors)
    return parsed_rows


def parse_repair_status_csv(csv_text, *, uploaded_by):
    reader = _read_rows(csv_text)
    _exact_headers(reader, REPAIR_STATUS_HEADERS)
    errors = []
    parsed_rows = []
    valid_statuses = {choice for choice, _ in Machine.Status.choices}

    for row_number, row in enumerate(reader, start=2):
        try:
            store = next(
                store
                for store in Store.objects.all()
                if _build_store_address_lookup(store) == row["store_address"].lower()
            )
            if (
                not user_has_store_scope(uploaded_by, store)
                and uploaded_by.role != uploaded_by.Role.SUPER_ADMIN
            ):
                raise ValueError("Store is outside the user's store scope.")
            machine_type = MachineType.objects.get(code=row["machine_type_code"])
            operational_from_date = date.fromisoformat(
                row["machine_operational_from_date"]
            )
            status_date = date.fromisoformat(row["status_date"])
            machine_status = row["machine_status"]
            if machine_status not in valid_statuses:
                raise ValueError("Invalid machine status value.")
            parsed_rows.append(
                ParsedRepairStatusRow(
                    store=store,
                    machine_type=machine_type,
                    operational_from_date=operational_from_date,
                    machine_status=machine_status,
                    status_date=status_date,
                )
            )
        except Exception as exc:
            errors.append({"row": row_number, "message": str(exc)})

    if errors:
        raise CSVImportError(errors)
    return parsed_rows


def _start_import_job(*, uploaded_by, import_type, original_filename):
    return ImportJob.objects.create(
        uploaded_by=uploaded_by,
        import_type=import_type,
        original_filename=original_filename,
        status=ImportJob.Status.PENDING,
    )


def _mark_job_processing(job):
    job.status = ImportJob.Status.PROCESSING
    job.save(update_fields=["status"])
    return job


def _finalize_job_success(job, *, row_count):
    job.row_count = row_count
    job.success_count = row_count
    job.error_count = 0
    job.error_report_json = []
    job.status = ImportJob.Status.SUCCEEDED
    job.completed_at = timezone.now()
    job.save()
    create_outbox_event(
        event_type=f"import.{job.import_type}.succeeded",
        instance=job,
        payload={
            "row_count": row_count,
            "uploaded_by_id": str(job.uploaded_by_id or ""),
        },
        source_scope={},
    )
    create_audit_log(
        actor=job.uploaded_by,
        action="import.completed",
        instance=job,
        after=serialize_instance(job),
    )
    if job.uploaded_by_id:
        notify_user(
            user=job.uploaded_by,
            title="Import completed",
            message=f"{job.original_filename} finished with {row_count} successful row(s).",
            category=Notification.Category.INFO,
        )
    return job


def _finalize_job_failure(job, exc):
    job.status = ImportJob.Status.FAILED
    job.error_report_json = exc.errors
    job.error_count = len(exc.errors)
    job.completed_at = timezone.now()
    job.save()
    create_outbox_event(
        event_type=f"import.{job.import_type}.failed",
        instance=job,
        payload={
            "error_count": job.error_count,
            "uploaded_by_id": str(job.uploaded_by_id or ""),
        },
        source_scope={},
    )
    create_audit_log(
        actor=job.uploaded_by,
        action="import.failed",
        instance=job,
        after=serialize_instance(job),
    )
    if job.uploaded_by_id:
        notify_user(
            user=job.uploaded_by,
            title="Import failed",
            message=f"{job.original_filename} failed validation. Review the import history panel for details.",
            category=Notification.Category.ALERT,
        )
    raise exc


def _process_supply_usage_import(job, csv_text):
    _mark_job_processing(job)
    try:
        parsed_rows = parse_supply_usage_csv(csv_text, uploaded_by=job.uploaded_by)
        with transaction.atomic():
            for parsed_row in parsed_rows:
                SupplyUsageRecord.objects.update_or_create(
                    store=parsed_row.store,
                    inventory_item=parsed_row.inventory_item,
                    usage_date=parsed_row.usage_date,
                    defaults={
                        "quantity_used": parsed_row.quantity_used,
                        "source_import_job": job,
                    },
                )
                draft_supply_schedule_from_usage(
                    store=parsed_row.store,
                    inventory_item=parsed_row.inventory_item,
                    quantity_used=parsed_row.quantity_used,
                    source_type="hub",
                    source_reference={"region_code": parsed_row.store.region.code},
                )
        return _finalize_job_success(job, row_count=len(parsed_rows))
    except CSVImportError as exc:
        _finalize_job_failure(job, exc)


def _process_repair_status_import(job, csv_text, *, allow_machine_create=True):
    _mark_job_processing(job)
    try:
        parsed_rows = parse_repair_status_csv(csv_text, uploaded_by=job.uploaded_by)
        with transaction.atomic():
            for parsed_row in parsed_rows:
                machine_uid = (
                    f"{parsed_row.store.store_code}-{parsed_row.machine_type.code}-"
                    f"{parsed_row.operational_from_date.isoformat()}"
                )
                machine = Machine.objects.filter(machine_uid=machine_uid).first()
                if machine is None:
                    if not allow_machine_create:
                        raise CSVImportError(
                            [
                                {
                                    "row": 0,
                                    "message": f"Machine {machine_uid} does not exist.",
                                }
                            ]
                        )
                    machine = Machine.objects.create(
                        machine_uid=machine_uid,
                        store=parsed_row.store,
                        machine_type=parsed_row.machine_type,
                        display_name=f"{parsed_row.store.store_code} {parsed_row.machine_type.name}",
                        operational_from_date=parsed_row.operational_from_date,
                        current_status=Machine.Status.NORMAL,
                    )
                append_machine_status_event(
                    machine,
                    status=parsed_row.machine_status,
                    status_date=parsed_row.status_date,
                    source_import_job=job,
                    actor=job.uploaded_by,
                )
                evaluate_warning_escalation(
                    machine, as_of_date=parsed_row.status_date, actor=job.uploaded_by
                )
        return _finalize_job_success(job, row_count=len(parsed_rows))
    except CSVImportError as exc:
        _finalize_job_failure(job, exc)


def import_supply_usage_csv(
    csv_text, *, uploaded_by, original_filename="supply_usage.csv"
):
    job = _start_import_job(
        uploaded_by=uploaded_by,
        import_type=ImportJob.ImportType.SUPPLY_USAGE,
        original_filename=original_filename,
    )
    return _process_supply_usage_import(job, csv_text)


def import_repair_status_csv(
    csv_text,
    *,
    uploaded_by,
    original_filename="repair_status.csv",
    allow_machine_create=True,
):
    job = _start_import_job(
        uploaded_by=uploaded_by,
        import_type=ImportJob.ImportType.REPAIR_STATUS,
        original_filename=original_filename,
    )
    return _process_repair_status_import(
        job, csv_text, allow_machine_create=allow_machine_create
    )


def queue_import_job(*, uploaded_by, import_type, original_filename, csv_text):
    job = _start_import_job(
        uploaded_by=uploaded_by,
        import_type=import_type,
        original_filename=original_filename,
    )
    create_audit_log(
        actor=uploaded_by,
        action="import.queued",
        instance=job,
        after=serialize_instance(job),
    )
    from .tasks import process_import_job_async

    transaction.on_commit(lambda: process_import_job_async.delay(str(job.pk), csv_text))
    return job


def process_import_job(*, import_job_id, csv_text):
    job = ImportJob.objects.select_related("uploaded_by").get(pk=import_job_id)
    if job.import_type == ImportJob.ImportType.SUPPLY_USAGE:
        return _process_supply_usage_import(job, csv_text)
    if job.import_type == ImportJob.ImportType.REPAIR_STATUS:
        return _process_repair_status_import(job, csv_text)
    raise ValueError(f"Unsupported import type: {job.import_type}")
