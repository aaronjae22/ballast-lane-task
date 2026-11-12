"""Errors raised when a business rule is broken.

The DRF exception handler (iteration 3) maps each one to a single HTTP status, as listed in
spec section 4.
"""

from tasks.domain.status import Status


class DomainError(Exception):
    """Base class for every broken business rule."""


class DomainValidationError(DomainError):
    """A value breaks a field rule (HTTP 400).

    `field` names the input that broke it, so the API can report the error against that field.
    """

    def __init__(self, field: str, message: str) -> None:
        super().__init__(f"{field}: {message}")
        self.field = field
        self.message = message


class InvalidTransition(DomainError):
    """The task's status doesn't allow this action (HTTP 409)."""

    def __init__(self, action: str, status: Status) -> None:
        super().__init__(f"Can't {action} a task whose status is {status.value}.")
        self.action = action
        self.status = status
