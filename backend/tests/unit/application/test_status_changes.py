"""StartTask, CompleteTask and ReopenTask: owner, assignee or admin (spec section 3)."""

from datetime import datetime

import pytest

from tasks.application.status_changes import CompleteTask, ReopenTask, StartTask
from tasks.domain.actor import Actor
from tasks.domain.errors import InvalidTransition, TaskNotFound
from tasks.domain.status import Status
from tasks.domain.task import Task
from tests.unit.builders import ADMIN, ASSIGNEE, EARLIER, NOW, OTHER_USER, OWNER, stored_task
from tests.unit.fakes import FixedClock, InMemoryTaskRepository

type StatusChange = type[StartTask | CompleteTask | ReopenTask]


def stored_with_status(repository: InMemoryTaskRepository, status: Status) -> Task:
    return stored_task(
        repository, status=status, completed_at=EARLIER if status is Status.DONE else None
    )


@pytest.mark.parametrize("actor", [OWNER, ASSIGNEE, ADMIN], ids=["owner", "assignee", "admin"])
@pytest.mark.parametrize(
    ("use_case", "before", "after", "completed_at"),
    [
        (StartTask, Status.TO_DO, Status.IN_PROGRESS, None),
        (CompleteTask, Status.TO_DO, Status.DONE, NOW),
        (CompleteTask, Status.IN_PROGRESS, Status.DONE, NOW),
        (ReopenTask, Status.DONE, Status.TO_DO, None),
    ],
    ids=["start", "complete-from-to-do", "complete-from-in-progress", "reopen"],
)
def test_the_owner_assignee_or_an_admin_can_change_the_status(
    repository: InMemoryTaskRepository,
    clock: FixedClock,
    actor: Actor,
    use_case: StatusChange,
    before: Status,
    after: Status,
    completed_at: datetime | None,
) -> None:
    task = stored_with_status(repository, before)

    updated = use_case(repository, clock).execute(actor, task.id)

    assert (updated.status, updated.completed_at, updated.updated_at) == (after, completed_at, NOW)
    assert repository.get(task.id) == updated


@pytest.mark.parametrize(
    ("use_case", "status"),
    [
        (StartTask, Status.IN_PROGRESS),
        (StartTask, Status.DONE),
        (CompleteTask, Status.DONE),
        (ReopenTask, Status.TO_DO),
        (ReopenTask, Status.IN_PROGRESS),
    ],
    ids=["start-in-progress", "start-done", "complete-done", "reopen-to-do", "reopen-in-progress"],
)
def test_an_invalid_transition_raises_and_saves_nothing(
    repository: InMemoryTaskRepository, clock: FixedClock, use_case: StatusChange, status: Status
) -> None:
    task = stored_with_status(repository, status)

    with pytest.raises(InvalidTransition):
        use_case(repository, clock).execute(OWNER, task.id)

    assert repository.get(task.id) == task


@pytest.mark.parametrize("use_case", [StartTask, CompleteTask, ReopenTask])
def test_anyone_else_gets_not_found_whatever_the_status_allows(
    repository: InMemoryTaskRepository, clock: FixedClock, use_case: StatusChange
) -> None:
    task = stored_with_status(repository, Status.IN_PROGRESS)

    with pytest.raises(TaskNotFound):
        use_case(repository, clock).execute(OTHER_USER, task.id)

    assert repository.get(task.id) == task


@pytest.mark.parametrize("use_case", [StartTask, CompleteTask, ReopenTask])
def test_a_missing_task_is_not_found(
    repository: InMemoryTaskRepository, clock: FixedClock, use_case: StatusChange
) -> None:
    with pytest.raises(TaskNotFound):
        use_case(repository, clock).execute(OWNER, 99)
