"""POST /api/tasks/: create a task through CreateTask (spec sections 3 and 5, ADR 0014).

The serializer checks only the shape of the body. The rules (title length after trimming,
no past due date, an active assignee) are the domain's, and come back as 400s keyed by the
field, the same shape as a shape error (ADR 0012). Any signed-in user can create a task and
becomes its owner.
"""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from tasks import models
from tests.api.conftest import ClientFor
from tests.conftest import MakeUser
from tests.unit.fakes import RecordingNotifier

pytestmark = pytest.mark.django_db

TASKS_URL = "/api/tasks/"


def test_creating_a_task_returns_it_with_the_caller_as_owner(
    owner: User, assignee: User, client_for: ClientFor, notifier: RecordingNotifier
) -> None:
    today = timezone.localdate()
    body = {
        "title": "  Write the spec  ",
        "description": "Agreed in the kickoff",
        "due_date": str(today),
        "assignee_id": assignee.pk,
    }

    response = client_for(owner).post(TASKS_URL, body)

    assert response.status_code == 201
    task = response.json()
    row = models.Task.objects.get(pk=task["id"])
    assert task["title"] == row.title == "Write the spec"
    assert task["description"] == "Agreed in the kickoff"
    assert task["due_date"] == str(today)
    assert (task["status"], task["completed_at"], task["is_overdue"]) == ("to_do", None, False)
    assert task["owner"] == {"id": owner.pk, "name": "owner"}
    assert task["assignee"] == {"id": assignee.pk, "name": "assignee"}
    assert task["created_at"] == task["updated_at"]


def test_a_title_is_all_a_task_needs(owner: User, client_for: ClientFor) -> None:
    response = client_for(owner).post(TASKS_URL, {"title": "Write the spec"})

    assert response.status_code == 201
    task = response.json()
    assert (task["description"], task["due_date"], task["assignee"]) == ("", None, None)


def test_assigning_someone_else_notifies_them_and_yourself_doesnt(
    owner: User, assignee: User, client_for: ClientFor, notifier: RecordingNotifier
) -> None:
    client = client_for(owner)

    for_someone = client.post(TASKS_URL, {"title": "Theirs", "assignee_id": assignee.pk}).json()
    client.post(TASKS_URL, {"title": "Mine", "assignee_id": owner.pk})

    assert notifier.assignments == [(for_someone["id"], assignee.pk)]


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({}, "title"),
        ({"title": None}, "title"),
        ({"title": "Spec", "description": None}, "description"),
        ({"title": "Spec", "due_date": "tomorrow"}, "due_date"),
        ({"title": "Spec", "assignee_id": "someone"}, "assignee_id"),
    ],
    ids=["no-title", "null-title", "null-description", "not-a-date", "not-an-id"],
)
def test_a_body_of_the_wrong_shape_is_400_keyed_by_field(
    owner: User,
    client_for: ClientFor,
    notifier: RecordingNotifier,
    body: dict[str, object],
    field: str,
) -> None:
    response = client_for(owner).post(TASKS_URL, body)

    assert response.status_code == 400
    assert set(response.json()) == {field}
    assert not models.Task.objects.exists()


@pytest.mark.parametrize("field", ["status", "owner_id", "completed_at", "id"])
def test_a_field_create_doesnt_take_is_400(owner: User, client_for: ClientFor, field: str) -> None:
    """Silently ignoring it would answer 201 and leave the client believing it was set."""
    response = client_for(owner).post(TASKS_URL, {"title": "Spec", field: "anything"})

    assert response.status_code == 400
    assert response.json() == {field: ["Unknown field."]}
    assert not models.Task.objects.exists()


def test_a_body_that_isnt_an_object_is_400(owner: User, client_for: ClientFor) -> None:
    response = client_for(owner).post(TASKS_URL, ["Spec"])

    assert response.status_code == 400
    assert not models.Task.objects.exists()


@pytest.mark.parametrize(
    ("body", "field", "message"),
    [
        ({"title": "   "}, "title", "Must be 1 to 200 characters."),
        ({"title": "x" * 201}, "title", "Must be 1 to 200 characters."),
        ({"due_date": "yesterday"}, "due_date", "Can't be in the past."),
        ({"assignee_id": "deactivated"}, "assignee_id", "Must be an active user."),
        ({"assignee_id": "unknown"}, "assignee_id", "Must be an active user."),
        ({"assignee_id": 2**63}, "assignee_id", "Must be an active user."),
    ],
    ids=["blank-title", "long-title", "past-due-date", "inactive", "unknown", "past-any-id"],
)
def test_a_broken_rule_is_400_keyed_by_field_and_stores_nothing(
    owner: User,
    make_user: MakeUser,
    client_for: ClientFor,
    notifier: RecordingNotifier,
    body: dict[str, object],
    field: str,
    message: str,
) -> None:
    """The rules are the domain's (ADR 0012): the serializer lets these shapes through."""
    deactivated = make_user("deactivated", is_active=False)
    values = {
        "yesterday": str(timezone.localdate() - timedelta(days=1)),
        "deactivated": deactivated.pk,
        "unknown": deactivated.pk + 1000,
    }
    body = {"title": "Spec"} | {key: values.get(value, value) for key, value in body.items()}

    response = client_for(owner).post(TASKS_URL, body)

    assert response.status_code == 400
    assert response.json() == {field: [message]}
    assert not models.Task.objects.exists()
    assert notifier.assignments == []


def test_a_title_of_exactly_200_characters_is_fine(owner: User, client_for: ClientFor) -> None:
    assert client_for(owner).post(TASKS_URL, {"title": "x" * 200}).status_code == 201


def test_creating_a_task_needs_a_token(api_client: APIClient) -> None:
    assert api_client.post(TASKS_URL, {"title": "Spec"}).status_code == 401
    assert not models.Task.objects.exists()
