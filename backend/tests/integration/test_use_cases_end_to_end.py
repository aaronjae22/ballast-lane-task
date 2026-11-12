"""Every write use case once against the real adapters and Postgres.

The unit tests prove the rules with fakes; these prove the real repository, user lookup and
clock fit the use cases. Only the notifier is a fake, until the Celery adapter (iteration 4).
Rows are read back through the model, not the repository, so a mapping bug can't hide itself.
"""

from dataclasses import dataclass
from datetime import timedelta

import pytest
from django.utils import timezone

from accounts.models import User
from tasks import models
from tasks.application.assign_task import AssignTask
from tasks.application.create_task import CreateTask
from tasks.application.delete_task import DeleteTask
from tasks.application.status_changes import CompleteTask, ReopenTask, StartTask
from tasks.application.update_task import UpdateTask
from tasks.domain.actor import Actor
from tasks.domain.errors import DomainValidationError
from tasks.domain.status import Status
from tasks.domain.task import Task
from tasks.infrastructure.clock import DjangoClock
from tasks.infrastructure.repositories import DjangoTaskRepository
from tasks.infrastructure.users import DjangoUserLookup
from tests.integration.conftest import MakeUser
from tests.unit.fakes import RecordingNotifier

pytestmark = pytest.mark.django_db


@dataclass
class Adapters:
    tasks: DjangoTaskRepository
    users: DjangoUserLookup
    notifier: RecordingNotifier
    clock: DjangoClock


@pytest.fixture
def adapters() -> Adapters:
    return Adapters(DjangoTaskRepository(), DjangoUserLookup(), RecordingNotifier(), DjangoClock())


def actor(user: User) -> Actor:
    return Actor(id=user.pk)


def stored(task: Task) -> models.Task:
    return models.Task.objects.get(pk=task.id)


@pytest.fixture
def created(adapters: Adapters, owner: User) -> Task:
    """A task the owner created through CreateTask, unassigned."""
    a = adapters
    return CreateTask(a.tasks, a.users, a.notifier, a.clock).execute(actor(owner), title="Spec")


def test_create_stores_the_task_and_notifies_another_assignee(
    adapters: Adapters, owner: User, assignee: User
) -> None:
    a = adapters
    before = timezone.now()

    task = CreateTask(a.tasks, a.users, a.notifier, a.clock).execute(
        actor(owner),
        title="  Write the spec  ",
        description="Kickoff notes",
        due_date=a.clock.today(),
        assignee_id=assignee.pk,
    )

    row = stored(task)
    assert (row.title, row.description, row.status) == ("Write the spec", "Kickoff notes", "to_do")
    assert (row.owner_id, row.assignee_id, row.due_date) == (owner.pk, assignee.pk, task.due_date)
    assert before <= row.created_at == row.updated_at <= timezone.now()
    assert a.notifier.assignments == [(task.id, assignee.pk)]


def test_create_with_an_inactive_assignee_stores_nothing(
    adapters: Adapters, owner: User, make_user: MakeUser
) -> None:
    a = adapters
    deactivated = make_user("deactivated", is_active=False)

    with pytest.raises(DomainValidationError):
        CreateTask(a.tasks, a.users, a.notifier, a.clock).execute(
            actor(owner), title="Write the spec", assignee_id=deactivated.pk
        )

    assert not models.Task.objects.exists()
    assert a.notifier.assignments == []


def test_update_stores_the_title_description_and_due_date(
    adapters: Adapters, owner: User, created: Task
) -> None:
    assert created.id is not None
    tomorrow = adapters.clock.today() + timedelta(days=1)

    UpdateTask(adapters.tasks, adapters.clock).execute(
        actor(owner), created.id, title="New title", description="New notes", due_date=tomorrow
    )

    row = stored(created)
    assert (row.title, row.description, row.due_date) == ("New title", "New notes", tomorrow)
    assert row.updated_at >= created.updated_at


def test_assign_stores_the_assignee_and_notifies_them(
    adapters: Adapters, owner: User, assignee: User, created: Task
) -> None:
    a = adapters
    assert created.id is not None

    AssignTask(a.tasks, a.users, a.notifier, a.clock).execute(actor(owner), created.id, assignee.pk)

    assert stored(created).assignee_id == assignee.pk
    assert a.notifier.assignments == [(created.id, assignee.pk)]


def test_start_stores_the_new_status(adapters: Adapters, owner: User, created: Task) -> None:
    assert created.id is not None

    StartTask(adapters.tasks, adapters.clock).execute(actor(owner), created.id)

    assert stored(created).status == Status.IN_PROGRESS


def test_complete_then_reopen_stores_then_clears_completed_at(
    adapters: Adapters, owner: User, created: Task
) -> None:
    assert created.id is not None

    completed = CompleteTask(adapters.tasks, adapters.clock).execute(actor(owner), created.id)
    row = stored(created)
    assert (row.status, row.completed_at) == (Status.DONE, completed.completed_at)
    assert row.completed_at is not None

    ReopenTask(adapters.tasks, adapters.clock).execute(actor(owner), created.id)
    row = stored(created)
    assert (row.status, row.completed_at) == (Status.TO_DO, None)


def test_delete_removes_the_row(adapters: Adapters, owner: User, created: Task) -> None:
    assert created.id is not None

    DeleteTask(adapters.tasks).execute(actor(owner), created.id)

    assert not models.Task.objects.filter(pk=created.id).exists()
