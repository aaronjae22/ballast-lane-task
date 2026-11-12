"""POST /api/tasks/{id}/assign/: assign, reassign or unassign through AssignTask (ADR 0004).

Body: {"assignee_id": int | null}, required. The owner or an admin only (the HTTP matrix
covers who). The new assignee is notified only when the assignee changes to someone other
than the person making the change (spec section 3).
"""

import pytest
from rest_framework.response import Response
from rest_framework.test import APIClient

from accounts.models import User
from tasks import models
from tasks.domain.task import Task
from tests.api.conftest import ClientFor
from tests.conftest import MakeUser, StoreTask
from tests.unit.fakes import RecordingNotifier

pytestmark = pytest.mark.django_db


def assign(client: APIClient, task: Task, body: object) -> Response:
    return client.post(f"/api/tasks/{task.id}/assign/", body)


def stored_assignee(task: Task) -> int | None:
    return models.Task.objects.get(pk=task.id).assignee_id


def test_assigning_returns_the_task_and_notifies_the_new_assignee(
    owner: User,
    assignee: User,
    store_task: StoreTask,
    client_for: ClientFor,
    notifier: RecordingNotifier,
) -> None:
    task = store_task(owner)

    response = assign(client_for(owner), task, {"assignee_id": assignee.pk})

    assert response.status_code == 200
    assert response.json()["assignee"] == {"id": assignee.pk, "name": "assignee"}
    assert stored_assignee(task) == assignee.pk
    assert notifier.assignments == [(task.id, assignee.pk)]


def test_reassigning_notifies_only_someone_new(
    owner: User,
    assignee: User,
    other_user: User,
    store_task: StoreTask,
    client_for: ClientFor,
    notifier: RecordingNotifier,
) -> None:
    task = store_task(owner, assignee)
    client = client_for(owner)

    same = assign(client, task, {"assignee_id": assignee.pk})
    other = assign(client, task, {"assignee_id": other_user.pk})

    assert (same.status_code, other.status_code) == (200, 200)
    assert notifier.assignments == [(task.id, other_user.pk)]


def test_unassigning_and_self_assigning_notify_no_one(
    owner: User,
    assignee: User,
    store_task: StoreTask,
    client_for: ClientFor,
    notifier: RecordingNotifier,
) -> None:
    task = store_task(owner, assignee)
    client = client_for(owner)

    unassigned = assign(client, task, {"assignee_id": None})
    assert unassigned.json()["assignee"] is None
    assert stored_assignee(task) is None
    assign(client, task, {"assignee_id": owner.pk})

    assert stored_assignee(task) == owner.pk
    assert notifier.assignments == []


@pytest.mark.parametrize(
    ("body", "field", "message"),
    [
        ({}, "assignee_id", "This field is required."),
        ({"assignee_id": "someone"}, "assignee_id", "A valid integer is required."),
        ({"assignee_id": "deactivated"}, "assignee_id", "Must be an active user."),
        ({"assignee_id": "unknown"}, "assignee_id", "Must be an active user."),
        ({"assignee_id": None, "status": "done"}, "status", "Unknown field."),
    ],
    ids=["missing", "not-an-id", "inactive", "unknown", "unknown-field"],
)
def test_a_bad_assignment_is_400_keyed_by_field_and_changes_nothing(
    owner: User,
    assignee: User,
    make_user: MakeUser,
    store_task: StoreTask,
    client_for: ClientFor,
    notifier: RecordingNotifier,
    body: dict[str, object],
    field: str,
    message: str,
) -> None:
    task = store_task(owner, assignee)
    deactivated = make_user("deactivated", is_active=False)
    values = {"deactivated": deactivated.pk, "unknown": deactivated.pk + 1000}
    body = {key: values.get(str(value), value) for key, value in body.items()}

    response = assign(client_for(owner), task, body)

    assert response.status_code == 400
    assert response.json() == {field: [message]}
    assert stored_assignee(task) == assignee.pk
    assert notifier.assignments == []


def test_assigning_needs_a_token(
    owner: User, assignee: User, store_task: StoreTask, api_client: APIClient
) -> None:
    task = store_task(owner)

    assert assign(api_client, task, {"assignee_id": assignee.pk}).status_code == 401
    assert stored_assignee(task) is None
