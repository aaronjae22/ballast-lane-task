"""DeleteTask: owner or admin removes a task (spec section 3)."""

import pytest

from tasks.application.delete_task import DeleteTask
from tasks.domain.actor import Actor
from tasks.domain.errors import NotAllowed, TaskNotFound
from tests.unit.builders import ADMIN, ASSIGNEE, OTHER_USER, OWNER, stored_task
from tests.unit.fakes import InMemoryTaskRepository


@pytest.fixture
def delete_task(repository: InMemoryTaskRepository) -> DeleteTask:
    return DeleteTask(repository)


@pytest.mark.parametrize("actor", [OWNER, ADMIN], ids=["owner", "admin"])
def test_the_owner_or_an_admin_can_delete_a_task(
    delete_task: DeleteTask, repository: InMemoryTaskRepository, actor: Actor
) -> None:
    task = stored_task(repository)
    other = stored_task(repository, title="Keep me")

    delete_task.execute(actor, task.id)

    assert repository.all() == [other]


@pytest.mark.parametrize(
    ("actor", "error"),
    [(ASSIGNEE, NotAllowed), (OTHER_USER, TaskNotFound)],
    ids=["assignee-NotAllowed", "anyone-else-TaskNotFound"],
)
def test_others_cant_delete_a_task(
    delete_task: DeleteTask,
    repository: InMemoryTaskRepository,
    actor: Actor,
    error: type[Exception],
) -> None:
    task = stored_task(repository)

    with pytest.raises(error):
        delete_task.execute(actor, task.id)

    assert repository.all() == [task]


def test_a_missing_task_is_not_found(delete_task: DeleteTask) -> None:
    with pytest.raises(TaskNotFound):
        delete_task.execute(OWNER, 99)
