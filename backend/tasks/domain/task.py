"""The Task entity and the rules that belong to a single task (spec section 3)."""

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Self

from tasks.domain.errors import DomainValidationError, InvalidTransition
from tasks.domain.status import Status

TITLE_MAX_LENGTH = 200


class Unset(Enum):
    """Marks an edit argument that wasn't given. None can't do it: it clears the due date."""

    UNSET = "UNSET"


UNSET = Unset.UNSET

# Spec section 3, "Status transitions": action -> (statuses it's allowed from, new status).
_TRANSITIONS: dict[str, tuple[frozenset[Status], Status]] = {
    "start": (frozenset({Status.TO_DO}), Status.IN_PROGRESS),
    "complete": (frozenset({Status.TO_DO, Status.IN_PROGRESS}), Status.DONE),
    "reopen": (frozenset({Status.DONE}), Status.TO_DO),
}


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

    def is_overdue(self, today: date) -> bool:
        """Due before today and not done. Computed whenever it's needed, never stored."""
        return (
            self.due_date is not None and self.due_date < today and self.status is not Status.DONE
        )

    def edit(
        self,
        *,
        title: str | Unset = UNSET,
        description: str | Unset = UNSET,
        due_date: date | Unset | None = UNSET,
        today: date,
        now: datetime,
    ) -> None:
        """Change the title, description or due date. Arguments left out keep their value.

        Everything is checked before anything changes, so a failed edit leaves the task as it
        was. The past-date rule applies only to a new due date: a task that is already overdue
        stays editable, and re-sending its current due date is allowed.
        """
        new_title = self.title if title is UNSET else _valid_title(title)
        new_description = self.description if description is UNSET else description
        new_due_date = self.due_date if due_date is UNSET else due_date
        if new_due_date != self.due_date:
            _check_due_date(new_due_date, today)
        self.title, self.description, self.due_date = new_title, new_description, new_due_date
        self.updated_at = now

    def start(self, *, now: datetime) -> None:
        self._transition("start", now)

    def complete(self, *, now: datetime) -> None:
        self._transition("complete", now)
        self.completed_at = now

    def reopen(self, *, now: datetime) -> None:
        self._transition("reopen", now)
        self.completed_at = None

    def _transition(self, action: str, now: datetime) -> None:
        """Move to the action's new status, or raise InvalidTransition and change nothing."""
        allowed_from, new_status = _TRANSITIONS[action]
        if self.status not in allowed_from:
            raise InvalidTransition(action, self.status)
        self.status = new_status
        self.updated_at = now


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
