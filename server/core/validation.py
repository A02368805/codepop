"""
Common validation helpers that raise core.exceptions.ValidationError.

These are re-usable guards for business rule constraints. Use them in
service functions, forms, or view logic to ensure data meets requirements
before proceeding.
"""

from core.exceptions import ValidationError


def require_positive(value, field="value"):
    """Ensure value is a positive number (> 0).

    Args:
        value: The number to validate.
        field: Human-readable field name for error message.

    Returns:
        value (unchanged if valid)

    Raises:
        ValidationError: If value is None, 0, or negative.
    """
    if value is None or value <= 0:
        raise ValidationError(f"{field} must be a positive number.")
    return value


def require_non_negative(value, field="value"):
    """Ensure value is non-negative (>= 0).

    Args:
        value: The number to validate.
        field: Human-readable field name for error message.

    Returns:
        value (unchanged if valid)

    Raises:
        ValidationError: If value is None or negative.
    """
    if value is None or value < 0:
        raise ValidationError(f"{field} cannot be negative.")
    return value


def require_in_range(value, lo, hi, field="value"):
    """Ensure value is within [lo, hi] inclusive.

    Args:
        value: The number to validate.
        lo: Lower bound (inclusive).
        hi: Upper bound (inclusive).
        field: Human-readable field name for error message.

    Returns:
        value (unchanged if valid)

    Raises:
        ValidationError: If value is outside the range.
    """
    if not (lo <= value <= hi):
        raise ValidationError(f"{field} must be between {lo} and {hi}.")
    return value


def require_future(dt, field="datetime"):
    """Ensure datetime is in the future (after now).

    Args:
        dt: A datetime.datetime to validate.
        field: Human-readable field name for error message.

    Returns:
        dt (unchanged if valid)

    Raises:
        ValidationError: If dt is None or is not after now.
    """
    from django.utils import timezone

    if dt is None or dt <= timezone.now():
        raise ValidationError(f"{field} must be in the future.")
    return dt


def require_non_blank(value, field="value"):
    """Ensure value is not blank/empty.

    Args:
        value: The value to validate.
        field: Human-readable field name for error message.

    Returns:
        value (unchanged if valid)

    Raises:
        ValidationError: If value is None, empty string, or whitespace-only.
    """
    if not value or not str(value).strip():
        raise ValidationError(f"{field} cannot be blank.")
    return value
