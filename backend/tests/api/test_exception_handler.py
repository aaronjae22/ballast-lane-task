"""The one place where domain errors become HTTP responses (spec section 4, AGENTS.md).

Each domain error maps to exactly one status. 404 covers a missing task, a hidden one, and
one deleted before save(): the repository and the domain raise the same TaskNotFound for all
three. A 400 has the same shape as DRF's own validation errors, keyed by the field.
"""

import pytest
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.settings import api_settings

from tasks.api.exceptions import exception_handler
from tasks.domain.errors import (
    DomainError,
    DomainValidationError,
    InvalidTransition,
    NotAllowed,
    TaskNotFound,
)
from tasks.domain.status import Status

DOMAIN_ERRORS = [
    pytest.param(TaskNotFound(7), 404, {"detail": "Task 7 not found."}, id="TaskNotFound"),
    pytest.param(
        NotAllowed("Only the task's owner or an admin can edit."),
        403,
        {"detail": "Only the task's owner or an admin can edit."},
        id="NotAllowed",
    ),
    pytest.param(
        InvalidTransition("start", Status.DONE),
        409,
        {"detail": "Can't start a task whose status is done."},
        id="InvalidTransition",
    ),
    pytest.param(
        DomainValidationError("title", "Must be 1 to 200 characters."),
        400,
        {"title": ["Must be 1 to 200 characters."]},
        id="DomainValidationError",
    ),
]


def handle(exc: Exception) -> Response | None:
    return exception_handler(exc, {})


def subclasses(cls: type) -> set[type]:
    return {sub for direct in cls.__subclasses__() for sub in {direct} | subclasses(direct)}


@pytest.mark.parametrize(("error", "status", "body"), DOMAIN_ERRORS)
def test_each_domain_error_becomes_one_status_and_body(
    error: DomainError, status: int, body: dict[str, object]
) -> None:
    response = handle(error)

    assert response is not None
    assert (response.status_code, response.data) == (status, body)


def test_every_domain_error_has_a_status() -> None:
    """A new DomainError must be mapped, or it would reach the client as a 500."""
    mapped = {type(case.values[0]) for case in DOMAIN_ERRORS}

    assert subclasses(DomainError) == mapped


def test_an_invalid_transition_says_so_in_its_error_code() -> None:
    response = handle(InvalidTransition("reopen", Status.TO_DO))

    assert response is not None
    assert response.data["detail"].code == "invalid_transition"


def test_drf_errors_keep_their_status_body_and_headers() -> None:
    throttled = handle(exceptions.Throttled(wait=42))
    invalid = handle(exceptions.ValidationError({"title": ["This field is required."]}))

    assert throttled is not None and invalid is not None
    assert (throttled.status_code, throttled["Retry-After"]) == (429, "42")
    assert (invalid.status_code, invalid.data) == (400, {"title": ["This field is required."]})


def test_any_other_exception_is_left_to_django() -> None:
    assert handle(ValueError("not an API error")) is None


def test_drf_uses_this_handler() -> None:
    assert api_settings.EXCEPTION_HANDLER is exception_handler
