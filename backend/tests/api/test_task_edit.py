"""PATCH /api/tasks/{id}/: edit a task through UpdateTask (spec section 5, ADRs 0004 and 0012).

Only the title, description and due date. A field left out keeps its value, and an explicit
null due date clears it. Status and assignee have their own endpoints, so sending them is a
400, not a silent no-op. There's no PUT.
"""

from datetime import timedelta
from unittest import mock

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from tasks import models
from tasks.domain.task import Task
from tasks.infrastructure.repositories import DjangoTaskRepository
from tests.api.conftest import ClientFor
from tests.conftest import StoreTask
from tests.unit.builders import EARLIER, LAST_WEEK, TOMORROW

pytestmark = pytest.mark.django_db


def url(task: Task) -> str:
    return f"/api/tasks/{task.id}/"


@pytest.fixture
def task(owner: User, store_task: StoreTask) -> Task:
    return store_task(owner, title="Write the spec", description="Notes", due_date=TOMORROW)


def test_editing_the_title_keeps_every_field_left_out(
    owner: User, task: Task, client_for: ClientFor
) -> None:
    response = client_for(owner).patch(url(task), {"title": "  Write the final spec  "})

    assert response.status_code == 200
    body = response.json()
    assert (body["title"], body["description"]) == ("Write the final spec", "Notes")
    assert body["due_date"] == str(TOMORROW)
    row = models.Task.objects.get(pk=task.id)
    assert (row.title, row.description, row.due_date) == ("Write the final spec", "Notes", TOMORROW)
    assert row.updated_at > EARLIER


def test_an_explicit_null_due_date_clears_it(
    owner: User, task: Task, client_for: ClientFor
) -> None:
    response = client_for(owner).patch(url(task), {"due_date": None})

    assert response.status_code == 200
    assert response.json()["due_date"] is None
    assert models.Task.objects.get(pk=task.id).due_date is None


def test_the_description_can_be_emptied(owner: User, task: Task, client_for: ClientFor) -> None:
    assert client_for(owner).patch(url(task), {"description": ""}).json()["description"] == ""


def test_an_empty_body_changes_only_updated_at(
    owner: User, task: Task, client_for: ClientFor
) -> None:
    """Every successful write moves updated_at, as auto_now would (ADR 0012)."""
    response = client_for(owner).patch(url(task), {})

    assert response.status_code == 200
    row = models.Task.objects.get(pk=task.id)
    assert (row.title, row.description, row.due_date) == ("Write the spec", "Notes", TOMORROW)
    assert row.updated_at > EARLIER


def test_an_overdue_task_stays_editable_but_cant_get_a_new_past_date(
    owner: User, store_task: StoreTask, client_for: ClientFor
) -> None:
    """Re-sending its current past due date is allowed; a different past date isn't."""
    overdue = store_task(owner, due_date=LAST_WEEK)
    client = client_for(owner)
    yesterday = timezone.localdate() - timedelta(days=1)

    same = client.patch(url(overdue), {"title": "Still late", "due_date": str(LAST_WEEK)})
    other = client.patch(url(overdue), {"due_date": str(yesterday)})

    assert same.status_code == 200
    assert other.status_code == 400
    assert other.json() == {"due_date": ["Can't be in the past."]}
    assert models.Task.objects.get(pk=overdue.id).due_date == LAST_WEEK


@pytest.mark.parametrize(
    ("body", "field", "message"),
    [
        ({"title": "   "}, "title", "Must be 1 to 200 characters."),
        ({"title": None}, "title", "This field may not be null."),
        ({"due_date": "next week"}, "due_date", None),
        ({"status": "done"}, "status", "Unknown field."),
        ({"assignee_id": 2}, "assignee_id", "Unknown field."),
    ],
    ids=["blank-title", "null-title", "not-a-date", "status", "assignee"],
)
def test_a_bad_edit_is_400_keyed_by_field_and_changes_nothing(
    owner: User,
    task: Task,
    client_for: ClientFor,
    body: dict[str, object],
    field: str,
    message: str | None,
) -> None:
    """Status and assignee have their own endpoints (ADR 0004), so PATCH refuses them."""
    before = models.Task.objects.filter(pk=task.id).values().get()

    response = client_for(owner).patch(url(task), body)

    assert response.status_code == 400
    assert set(response.json()) == {field}
    if message is not None:
        assert response.json()[field] == [message]
    assert models.Task.objects.filter(pk=task.id).values().get() == before


def test_there_is_no_put(owner: User, task: Task, client_for: ClientFor) -> None:
    response = client_for(owner).put(url(task), {"title": "Replaced", "description": ""})

    assert response.status_code == 405


@pytest.mark.django_db(transaction=True)
def test_an_edit_runs_in_its_own_transaction(
    owner: User, task: Task, client_for: ClientFor
) -> None:
    """No test transaction around it here, so a view that skipped the wiring's atomic() would
    meet TransactionManagementError from the repository's locking get() (ADR 0013)."""
    response = client_for(owner).patch(url(task), {"title": "Edited"})

    assert response.status_code == 200
    assert models.Task.objects.get(pk=task.id).title == "Edited"


def test_a_task_deleted_between_loading_and_saving_is_404(
    owner: User, task: Task, client_for: ClientFor
) -> None:
    """The repository's save() never inserts, and raises TaskNotFound for a row that's gone."""
    real_get = DjangoTaskRepository.get

    def get_then_lose_the_row(repository: DjangoTaskRepository, task_id: int) -> Task | None:
        loaded = real_get(repository, task_id)
        models.Task.objects.filter(pk=task_id).delete()
        return loaded

    with mock.patch.object(DjangoTaskRepository, "get", get_then_lose_the_row):
        response = client_for(owner).patch(url(task), {"title": "Too late"})

    assert response.status_code == 404
    assert response.json() == {"detail": f"Task {task.id} not found."}
    assert not models.Task.objects.filter(pk=task.id).exists()


def test_editing_needs_a_token(task: Task, api_client: APIClient) -> None:
    assert api_client.patch(url(task), {"title": "Edited"}).status_code == 401
