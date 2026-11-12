"""Errors raised when a business rule is broken.

The DRF exception handler (iteration 3) maps each one to a single HTTP status, as listed in
spec section 4.
"""


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
