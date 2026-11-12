"""Ports: what the use cases need from the outside world (spec section 4, ADR 0002).

Protocols only. The in-memory fakes in tests/unit/ implement them for unit tests; the ORM,
Celery and clock adapters in tasks/infrastructure/ implement them from iteration 2, and
tasks/api/wiring.py passes those to the use cases.
"""

from datetime import date, datetime
from typing import Protocol

from tasks.domain.task import Task


class TaskRepository(Protocol):
    """Where tasks are stored. Reads for the API go through selectors, not through here."""

    def get(self, task_id: int) -> Task | None:
        """The task with this id, or None if there's none."""

    def add(self, task: Task) -> Task:
        """Store a new task and return it with the id the store gave it."""

    def save(self, task: Task) -> None:
        """Store the changes to an existing task."""

    def delete(self, task_id: int) -> None:
        """Remove the task with this id."""


class UserLookup(Protocol):
    """Facts about users that the rules need."""

    def is_active_user(self, user_id: int) -> bool:
        """True if the id belongs to an active user; False if it's inactive or unknown."""


class Notifier(Protocol):
    """Side effects for other people. Adapters queue them after the transaction commits."""

    def task_assigned(self, *, task_id: int, assignee_id: int) -> None:
        """Tell the assignee that the task was assigned to them."""


class Clock(Protocol):
    """The current time. The domain never reads a clock; use cases ask this and pass values."""

    def now(self) -> datetime:
        """The current moment, timezone-aware."""

    def today(self) -> date:
        """Today's date in the configured time zone (settings.TIME_ZONE)."""
