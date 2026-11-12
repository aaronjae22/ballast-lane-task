"""The composition root: each write use case built with the real adapters (spec section 4).

Views call these functions for every write and never build a use case themselves. Each one:
- maps the request's user to the domain's Actor, here and nowhere else (ADR 0013);
- runs its use case inside transaction.atomic(). The repository's get() locks the task's row
  and refuses to run outside a transaction, and the notifier acts only once that same
  transaction commits, so a write that fails anywhere stores nothing and notifies no one.

Unit tests build the use cases with in-memory fakes instead; API tests replace notifier().
"""

from typing import Any

from django.db import transaction

from accounts.models import User
from tasks.application.assign_task import AssignTask
from tasks.application.create_task import CreateTask
from tasks.application.delete_task import DeleteTask
from tasks.application.ports import Notifier
from tasks.application.status_changes import CompleteTask, ReopenTask, StartTask
from tasks.application.update_task import UpdateTask
from tasks.domain.actor import Actor
from tasks.domain.task import Task
from tasks.infrastructure.clock import DjangoClock
from tasks.infrastructure.notifications import LoggingNotifier
from tasks.infrastructure.repositories import DjangoTaskRepository
from tasks.infrastructure.users import DjangoUserLookup


def actor_for(user: User) -> Actor:
    """The user as the rules see them: their id, and whether they're an admin (is_staff)."""
    return Actor(id=user.pk, is_admin=user.is_admin)


def notifier() -> Notifier:
    """The assignment notifier. Iteration 4 changes this line to the Celery adapter."""
    return LoggingNotifier()


@transaction.atomic
def create_task(user: User, **fields: Any) -> Task:
    """Fields as CreateTask takes them: title, and optionally description, due_date, assignee_id."""
    use_case = CreateTask(DjangoTaskRepository(), DjangoUserLookup(), notifier(), DjangoClock())
    return use_case.execute(actor_for(user), **fields)


@transaction.atomic
def update_task(user: User, task_id: int, **fields: Any) -> Task:
    """Only the fields given change; one left out keeps its value (UpdateTask's UNSET)."""
    return UpdateTask(DjangoTaskRepository(), DjangoClock()).execute(
        actor_for(user), task_id, **fields
    )


@transaction.atomic
def assign_task(user: User, task_id: int, assignee_id: int | None) -> Task:
    use_case = AssignTask(DjangoTaskRepository(), DjangoUserLookup(), notifier(), DjangoClock())
    return use_case.execute(actor_for(user), task_id, assignee_id)


@transaction.atomic
def start_task(user: User, task_id: int) -> Task:
    return StartTask(DjangoTaskRepository(), DjangoClock()).execute(actor_for(user), task_id)


@transaction.atomic
def complete_task(user: User, task_id: int) -> Task:
    return CompleteTask(DjangoTaskRepository(), DjangoClock()).execute(actor_for(user), task_id)


@transaction.atomic
def reopen_task(user: User, task_id: int) -> Task:
    return ReopenTask(DjangoTaskRepository(), DjangoClock()).execute(actor_for(user), task_id)


@transaction.atomic
def delete_task(user: User, task_id: int) -> None:
    DeleteTask(DjangoTaskRepository()).execute(actor_for(user), task_id)
