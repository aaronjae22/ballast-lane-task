"""POST /api/tasks/{id}/start/, /complete/, /reopen/: the status transitions (ADR 0004).

Each maps to one use case. The owner, the assignee or an admin may (the HTTP matrix covers
who). A transition the status doesn't allow is 409 and changes nothing (spec section 3).
"""

from datetime import datetime

import pytest
from rest_framework.response import Response
from rest_framework.test import APIClient

from accounts.models import User
from tasks import models
from tasks.domain.status import Status
from tasks.domain.task import Task
from tests.api.conftest import ClientFor
from tests.conftest import StoreTask
from tests.unit.builders import EARLIER

pytestmark = pytest.mark.django_db


def act(client: APIClient, task: Task, action: str, body: object = None) -> Response:
    return client.post(f"/api/tasks/{task.id}/{action}/", body)


def stored(task: Task) -> models.Task:
    return models.Task.objects.get(pk=task.id)


@pytest.mark.parametrize(
    ("action", "start", "end"),
    [
        ("start", Status.TO_DO, Status.IN_PROGRESS),
        ("complete", Status.TO_DO, Status.DONE),
        ("complete", Status.IN_PROGRESS, Status.DONE),
        ("reopen", Status.DONE, Status.TO_DO),
    ],
    ids=["start", "complete-to-do", "complete-in-progress", "reopen"],
)
def test_each_allowed_transition_returns_the_task_in_its_new_status(
    owner: User,
    store_task: StoreTask,
    client_for: ClientFor,
    action: str,
    start: Status,
    end: Status,
) -> None:
    task = store_task(owner, status=start, completed_at=EARLIER if start is Status.DONE else None)

    response = act(client_for(owner), task, action)

    assert response.status_code == 200
    assert response.json()["status"] == end.value
    assert stored(task).status == end.value
    assert stored(task).updated_at > EARLIER


def test_completing_sets_completed_at_and_reopening_clears_it(
    owner: User, store_task: StoreTask, client_for: ClientFor
) -> None:
    task = store_task(owner)
    client = client_for(owner)

    completed = act(client, task, "complete").json()
    assert completed["completed_at"] is not None
    assert stored(task).completed_at == datetime.fromisoformat(completed["completed_at"])

    reopened = act(client, task, "reopen").json()
    assert reopened["completed_at"] is None
    assert stored(task).completed_at is None


@pytest.mark.parametrize(
    ("action", "start"),
    [
        ("start", Status.IN_PROGRESS),
        ("start", Status.DONE),
        ("complete", Status.DONE),
        ("reopen", Status.TO_DO),
        ("reopen", Status.IN_PROGRESS),
    ],
    ids=["start-in-progress", "start-done", "complete-done", "reopen-to-do", "reopen-in-progress"],
)
def test_a_transition_the_status_doesnt_allow_is_409_and_saves_nothing(
    owner: User, store_task: StoreTask, client_for: ClientFor, action: str, start: Status
) -> None:
    """The use case loads the task and fails before saving: status, completed_at and
    updated_at are all as they were."""
    task = store_task(owner, status=start, completed_at=EARLIER if start is Status.DONE else None)
    before = models.Task.objects.filter(pk=task.id).values().get()

    response = act(client_for(owner), task, action)

    assert response.status_code == 409
    assert response.json() == {"detail": f"Can't {action} a task whose status is {start.value}."}
    assert models.Task.objects.filter(pk=task.id).values().get() == before


@pytest.mark.parametrize("action", ["start", "complete", "reopen"])
def test_a_body_with_any_field_is_400(
    owner: User, store_task: StoreTask, client_for: ClientFor, action: str
) -> None:
    """They take no body; a field sent anyway is refused, not ignored (ADR 0014)."""
    task = store_task(owner, status=Status.DONE if action == "reopen" else Status.TO_DO)

    response = act(client_for(owner), task, action, {"status": "in_progress"})

    assert response.status_code == 400
    assert response.json() == {"status": ["Unknown field."]}


@pytest.mark.parametrize("action", ["start", "complete", "reopen"])
def test_changing_status_needs_a_token(
    owner: User, store_task: StoreTask, api_client: APIClient, action: str
) -> None:
    task = store_task(owner)

    assert act(api_client, task, action).status_code == 401
