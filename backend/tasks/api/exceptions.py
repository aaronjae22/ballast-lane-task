"""The DRF exception handler: the one place domain errors become HTTP (spec section 4).

Each domain error is turned into the DRF exception for its status, then DRF's own handler
builds the response, so every error has DRF's shape and keeps its headers (WWW-Authenticate
on 401, Retry-After on 429). The use cases raise in ADR 0012's order, so a task that's
missing or hidden is 404 before a 403, and a 403 comes before a 400 or 409.
"""

from typing import Any

from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from tasks.domain.errors import (
    DomainValidationError,
    InvalidTransition,
    NotAllowed,
    TaskNotFound,
)


class Conflict(exceptions.APIException):
    """The task's status doesn't allow the action (HTTP 409)."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "The task's status doesn't allow this action."
    default_code = "invalid_transition"


def exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """DRF's handler, after translating a domain error into the DRF exception for its status.

    Anything else passes through untouched: DRF answers its own exceptions, and Django turns
    the rest into a 500. A DomainError without a mapping would be one of those 500s, which
    the exception handler's tests guard against.
    """
    return drf_exception_handler(_translate(exc), context)


def _translate(exc: Exception) -> Exception:
    match exc:
        case TaskNotFound():
            # Missing, not visible, or deleted before save(): the same answer (ADR 0003).
            return exceptions.NotFound(str(exc))
        case NotAllowed():
            return exceptions.PermissionDenied(str(exc))
        case InvalidTransition():
            return Conflict(str(exc))
        case DomainValidationError():
            # Keyed by the field, like DRF's own validation errors.
            return exceptions.ValidationError({exc.field: [exc.message]})
    return exc
