"""
Shared exception hierarchy for all applications.

Base:
  AppError
    ├── ServiceError (recoverable business rule violations)
    │   ├── ValidationError (input validation failure)
    │   └── ConflictError (state machine or duplicate violation)
    └── NotFoundError (resource not found or inaccessible)

App-specific exceptions inherit from these base types.
"""


class AppError(Exception):
    """Base exception for all application errors.

    Carries a user-facing message accessible via str(exception).
    Each error type has a code for programmatic handling.
    """

    code = "error"


class ServiceError(AppError):
    """Raised by service functions for recoverable business rule violations.

    Indicates that a requested operation could not be completed due to
    the current state or data constraints, not due to system/code errors.
    """

    code = "service_error"


class ValidationError(ServiceError):
    """Input validation failed a business rule.

    Raised when user-provided or calculated data does not meet constraints.
    """

    code = "validation_error"


class ConflictError(ServiceError):
    """Action conflicts with current state or constraints.

    Examples: duplicate resource, state machine violation, race condition.
    """

    code = "conflict"


class NotFoundError(AppError):
    """Requested resource does not exist or is not accessible to caller."""

    code = "not_found"
