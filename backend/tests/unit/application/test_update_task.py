"""UpdateTask: owner or admin edits title, description and due date (spec sections 3 and 5)."""

import pytest

from tasks.application.update_task import UpdateTask
from tasks.domain.actor import Actor
from tasks.domain.errors import DomainValidationError, NotAllowed, TaskNotFound
from tests.unit.builders import (
    ADMIN,
    ASSIGNEE,
    LAST_WEEK,
    NOW,
    OTHER_USER,
    OWNER,
    TOMORROW,
    YESTERDAY,
    stored_task,
)
from tests.unit.fakes import FixedClock, InMemoryTaskRepository


@pytest.fixture
def update_task(repository: InMemoryTaskRepository, clock: FixedClock) -> UpdateTask:
    return UpdateTask(repository, clock)


@pytest.mark.parametrize("actor", [OWNER, ADMIN], ids=["owner", "admin"])
def test_the_owner_or_an_admin_can_edit_and_the_change_is_saved(
    update_task: UpdateTask, repository: InMemoryTaskRepository, actor: Actor
) -> None:
    task = stored_task(repository, title="Old title", description="Old notes")

    updated = update_task.execute(actor, task.id, title="New title")

    assert (updated.title, updated.description, updated.updated_at) == (
        "New title",
        "Old notes",
        NOW,
    )
    assert repository.get(task.id) == updated


def test_fields_left_out_keep_their_value(
    update_task: UpdateTask, repository: InMemoryTaskRepository
) -> None:
    task = stored_task(repository, title="Old title", due_date=TOMORROW)

    updated = update_task.execute(OWNER, task.id, due_date=None)

    assert (updated.title, updated.due_date) == ("Old title", None)


def test_a_task_that_is_already_overdue_can_still_be_edited(
    update_task: UpdateTask, repository: InMemoryTaskRepository
) -> None:
    task = stored_task(repository, due_date=LAST_WEEK)

    updated = update_task.execute(OWNER, task.id, title="New title", due_date=LAST_WEEK)

    assert (updated.title, updated.due_date) == ("New title", LAST_WEEK)


def test_a_new_due_date_in_the_past_is_rejected_and_nothing_is_saved(
    update_task: UpdateTask, repository: InMemoryTaskRepository
) -> None:
    task = stored_task(repository, due_date=TOMORROW)

    with pytest.raises(DomainValidationError):
        update_task.execute(OWNER, task.id, title="New title", due_date=YESTERDAY)

    assert repository.get(task.id) == task


def test_a_missing_task_is_not_found(update_task: UpdateTask) -> None:
    with pytest.raises(TaskNotFound):
        update_task.execute(OWNER, 99, title="New title")


@pytest.mark.parametrize(
    ("actor", "error"),
    [(ASSIGNEE, NotAllowed), (OTHER_USER, TaskNotFound)],
    ids=["assignee-NotAllowed", "anyone-else-TaskNotFound"],
)
@pytest.mark.parametrize("title", ["New title", ""], ids=["valid-edit", "invalid-edit"])
def test_others_cant_edit_and_permission_is_checked_before_the_values(
    update_task: UpdateTask,
    repository: InMemoryTaskRepository,
    actor: Actor,
    error: type[Exception],
    title: str,
) -> None:
    task = stored_task(repository)

    with pytest.raises(error):
        update_task.execute(actor, task.id, title=title)

    assert repository.get(task.id) == task
