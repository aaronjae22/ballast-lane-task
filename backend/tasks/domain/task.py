"""The Task entity and the rules that belong to a single task (spec section 3)."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Self

from tasks.domain.errors import DomainValidationError
from tasks.domain.status import Status

TITLE_MAX_LENGTH = 200


@dataclass(kw_only=True, slots=True)
class Task:
    """A task on the board.

    The constructor rebuilds a task as it was stored and checks no rules, so a task that has
    since become overdue still loads. New tasks come from create(); changes go through the
    methods, which enforce the rules. "Today" and "now" are always passed in.
    """

    id: int | None
    title: str
    description: str
    status: Status
    due_date: date | None
    owner_id: int
    assignee_id: int | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        title: str,
        description: str = "",
        due_date: date | None = None,
        owner_id: int,
        assignee_id: int | None = None,
        assignee_is_active: bool = False,
        today: date,
        now: datetime,
    ) -> Self:
        """A new to-do task owned by its creator. It has no id until the repository adds it."""
        title = _valid_title(title)
        _check_due_date(due_date, today)
        _check_assignee(assignee_id, assignee_is_active)
        return cls(
            id=None,
            title=title,
            description=description,
            status=Status.TO_DO,
            due_date=due_date,
            owner_id=owner_id,
            assignee_id=assignee_id,
            completed_at=None,
            created_at=now,
            updated_at=now,
        )


def _valid_title(title: str) -> str:
    """The title without surrounding whitespace, if it is 1 to 200 characters long."""
    stripped = title.strip()
    if not 1 <= len(stripped) <= TITLE_MAX_LENGTH:
        raise DomainValidationError("title", f"Must be 1 to {TITLE_MAX_LENGTH} characters.")
    return stripped


def _check_due_date(due_date: date | None, today: date) -> None:
    if due_date is not None and due_date < today:
        raise DomainValidationError("due_date", "Can't be in the past.")


def _check_assignee(assignee_id: int | None, assignee_is_active: bool) -> None:
    # One message for unknown and inactive users, so the error doesn't reveal which it was.
    if assignee_id is not None and not assignee_is_active:
        raise DomainValidationError("assignee_id", "Must be an active user.")
