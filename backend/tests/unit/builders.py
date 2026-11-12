"""Shared values for unit tests: fixed dates and user ids, so no test reads a clock."""

from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING

from tasks.domain.actor import Actor
from tasks.domain.status import Status
from tasks.domain.task import Task

if TYPE_CHECKING:
    from tests.unit.fakes import InMemoryTaskRepository

TODAY = date(2026, 11, 11)
YESTERDAY = TODAY - timedelta(days=1)
LAST_WEEK = TODAY - timedelta(days=7)
TOMORROW = TODAY + timedelta(days=1)
NOW = datetime(2026, 11, 11, 15, 30, tzinfo=UTC)
EARLIER = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)

OWNER_ID = 1
ASSIGNEE_ID = 2
ADMIN_ID = 3
OTHER_USER_ID = 4

OWNER = Actor(id=OWNER_ID)
ASSIGNEE = Actor(id=ASSIGNEE_ID)
ADMIN = Actor(id=ADMIN_ID, is_admin=True)
OTHER_USER = Actor(id=OTHER_USER_ID)


def make_task(**overrides: object) -> Task:
    """A stored task, rebuilt without the create() rules (so it can already be overdue)."""
    fields: dict[str, object] = {
        "id": 1,
        "title": "Write the spec",
        "description": "",
        "status": Status.TO_DO,
        "due_date": None,
        "owner_id": OWNER_ID,
        "assignee_id": None,
        "completed_at": None,
        "created_at": EARLIER,
        "updated_at": EARLIER,
    }
    return Task(**(fields | overrides))


def stored_task(repository: "InMemoryTaskRepository", **overrides: object) -> Task:
    """Store a task owned by OWNER and assigned to ASSIGNEE, and return it with its id."""
    fields: dict[str, object] = {"id": None, "owner_id": OWNER_ID, "assignee_id": ASSIGNEE_ID}
    return repository.add(make_task(**(fields | overrides)))
