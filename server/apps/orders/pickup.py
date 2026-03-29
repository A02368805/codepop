from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

MIN_PREP_BUFFER_MINUTES = 12
SUGGESTED_SLOT_SPACING_MINUTES = 15
DISPLAY_SLOT_COUNT = 2


def _round_up_to_five_minutes(moment):
    moment = moment.replace(second=0, microsecond=0)
    remainder = moment.minute % 5
    if remainder:
        moment += timedelta(minutes=5 - remainder)
    return moment


def format_pickup_time(moment):
    return moment.strftime("%I:%M %p").lstrip("0")


def compute_asap_pickup_time(*, now=None):
    now = timezone.localtime(now or timezone.now())
    return _round_up_to_five_minutes(now + timedelta(minutes=MIN_PREP_BUFFER_MINUTES))


def pickup_time_choices(*, now=None):
    asap_time = compute_asap_pickup_time(now=now)
    choices = [("asap", "ASAP")]
    for offset_index in range(DISPLAY_SLOT_COUNT):
        slot = asap_time + timedelta(
            minutes=SUGGESTED_SLOT_SPACING_MINUTES * offset_index
        )
        choices.append((slot.isoformat(), format_pickup_time(slot)))
    return choices


def parse_pickup_choice(value, *, now=None):
    if not value:
        return None
    if value == "asap":
        return compute_asap_pickup_time(now=now)
    parsed = timezone.datetime.fromisoformat(value)
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed
