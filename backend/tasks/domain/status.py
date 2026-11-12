"""Task statuses (spec section 3)."""

from enum import StrEnum


class Status(StrEnum):
    """Where a task is in its lifecycle. The values are what the API and the database store."""

    TO_DO = "to_do"
    IN_PROGRESS = "in_progress"
    DONE = "done"
