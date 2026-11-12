"""TaskRepository: one contract for the in-memory fake and the ORM repository.

The use-case tests trust the fake. Running the same cases against Postgres holds the ORM
repository to the fake's behaviour. Misuse isn't part of the port, so the ORM repository's
own answers to it (ADR 0013) are tested on their own at the end.
"""

from dataclasses import replace
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from django.db import connection
from django.db.transaction import TransactionManagementError
from django.test.utils import CaptureQueriesContext

from accounts.models import User
from tasks import models
from tasks.application.ports import TaskRepository
from tasks.domain.errors import TaskNotFound
from tasks.domain.status import Status
from tasks.domain.task import Task
from tasks.infrastructure.repositories import DjangoTaskRepository
from tests.unit.builders import NOW, TOMORROW, YESTERDAY, make_task
from tests.unit.fakes import InMemoryTaskRepository

pytestmark = pytest.mark.django_db

# Microseconds and a non-UTC zone, to show the stored instant is exactly the one given.
MANAGUA = ZoneInfo("America/Managua")
CREATED_AT = datetime(2026, 11, 2, 8, 15, 30, 123456, tzinfo=MANAGUA)
COMPLETED_AT = datetime(2026, 11, 10, 18, 45, 12, 654321, tzinfo=MANAGUA)


@pytest.fixture(params=[InMemoryTaskRepository, DjangoTaskRepository], ids=["in-memory", "orm"])
def repository(request: pytest.FixtureRequest) -> TaskRepository:
    return request.param()


def new_task(owner: User, **overrides: object) -> Task:
    """A task not stored yet, with every optional field empty unless given."""
    return make_task(**({"id": None, "owner_id": owner.pk} | overrides))


def complete_task(owner: User, assignee: User) -> Task:
    """A task not stored yet, with every field set."""
    return new_task(
        owner,
        title="Write the spec",
        description="Agreed in the kickoff",
        status=Status.DONE,
        due_date=YESTERDAY,
        assignee_id=assignee.pk,
        completed_at=COMPLETED_AT,
        created_at=CREATED_AT,
        updated_at=COMPLETED_AT,
    )


def test_add_gives_the_task_an_id(repository: TaskRepository, owner: User) -> None:
    task = new_task(owner)

    first = repository.add(task)
    second = repository.add(task)

    assert first.id is not None
    assert second.id not in (None, first.id)
    assert first == replace(task, id=first.id)


@pytest.mark.parametrize("every_field_set", [True, False], ids=["every-field-set", "bare"])
def test_get_returns_the_task_with_every_field_equal(
    repository: TaskRepository, owner: User, assignee: User, every_field_set: bool
) -> None:
    task = complete_task(owner, assignee) if every_field_set else new_task(owner)
    added = repository.add(task)
    assert added.id is not None

    assert repository.get(added.id) == added


def test_get_returns_none_for_a_missing_id(repository: TaskRepository, owner: User) -> None:
    added = repository.add(new_task(owner))
    assert added.id is not None

    assert repository.get(added.id + 1000) is None


def test_a_change_without_save_is_not_stored(repository: TaskRepository, owner: User) -> None:
    added = repository.add(new_task(owner))
    assert added.id is not None
    loaded = repository.get(added.id)
    assert loaded is not None

    loaded.title = "Changed but not saved"

    assert repository.get(added.id) == added


def test_save_stores_new_values(repository: TaskRepository, owner: User, assignee: User) -> None:
    added = repository.add(new_task(owner))
    assert added.id is not None
    changed = replace(
        added,
        title="Changed",
        description="New notes",
        status=Status.DONE,
        due_date=TOMORROW,
        assignee_id=assignee.pk,
        completed_at=NOW,
        updated_at=NOW,
    )

    repository.save(changed)

    assert repository.get(added.id) == changed


def test_save_clears_optional_values(
    repository: TaskRepository, owner: User, assignee: User
) -> None:
    added = repository.add(complete_task(owner, assignee))
    assert added.id is not None
    cleared = replace(
        added, status=Status.TO_DO, due_date=None, assignee_id=None, completed_at=None
    )

    repository.save(cleared)

    assert repository.get(added.id) == cleared


def test_delete_removes_only_that_task(repository: TaskRepository, owner: User) -> None:
    kept = repository.add(new_task(owner, title="Kept"))
    deleted = repository.add(new_task(owner, title="Deleted"))
    assert kept.id is not None and deleted.id is not None

    repository.delete(deleted.id)

    assert repository.get(deleted.id) is None
    assert repository.get(kept.id) == kept


# The ORM repository on its own: locking and misuse (ADR 0013).


def test_get_locks_the_row_in_one_query(owner: User) -> None:
    repository = DjangoTaskRepository()
    added = repository.add(new_task(owner))
    assert added.id is not None

    with CaptureQueriesContext(connection) as queries:
        repository.get(added.id)

    assert len(queries) == 1
    assert "FOR UPDATE" in queries[0]["sql"]


@pytest.mark.django_db(transaction=True)
def test_get_is_refused_outside_a_transaction(owner: User) -> None:
    repository = DjangoTaskRepository()
    added = repository.add(new_task(owner))
    assert added.id is not None

    with pytest.raises(TransactionManagementError):
        repository.get(added.id)


def test_add_refuses_a_task_that_already_has_an_id(owner: User) -> None:
    with pytest.raises(ValueError, match="already has an id"):
        DjangoTaskRepository().add(new_task(owner, id=1))

    assert not models.Task.objects.exists()


def test_save_never_brings_back_a_deleted_task(owner: User) -> None:
    repository = DjangoTaskRepository()
    added = repository.add(new_task(owner))
    models.Task.objects.filter(pk=added.id).delete()

    with pytest.raises(TaskNotFound):
        repository.save(added)

    assert not models.Task.objects.exists()


def test_delete_of_a_missing_id_does_nothing(owner: User) -> None:
    repository = DjangoTaskRepository()
    kept = repository.add(new_task(owner))
    assert kept.id is not None

    repository.delete(kept.id + 1000)

    assert repository.get(kept.id) == kept
