"""The task admin is read-only: it writes straight to the model, skipping every domain rule."""

import pytest
from django.contrib import admin
from django.test import Client
from django.urls import reverse

from accounts.models import User
from tasks.admin import TaskAdmin
from tasks.models import Task
from tests.unit.builders import EARLIER

pytestmark = pytest.mark.django_db

CHANGELIST = "admin:tasks_task_changelist"


@pytest.fixture
def row(owner: User) -> Task:
    return Task.objects.create(
        title="Write the spec", owner=owner, created_at=EARLIER, updated_at=EARLIER
    )


def test_task_is_registered_with_the_read_only_admin() -> None:
    assert isinstance(admin.site._registry[Task], TaskAdmin)


@pytest.mark.parametrize(
    ("params", "count"),
    [
        ({}, 1),
        ({"q": "SPEC"}, 1),
        ({"q": "nothing like it"}, 0),
        ({"status__exact": "to_do"}, 1),
        ({"status__exact": "done"}, 0),
    ],
    ids=["all", "search-hit", "search-miss", "status-hit", "status-miss"],
)
def test_the_list_shows_searches_and_filters_tasks(
    admin_client: Client, row: Task, params: dict[str, str], count: int
) -> None:
    response = admin_client.get(reverse(CHANGELIST), params)

    assert response.status_code == 200
    assert response.context["cl"].result_count == count


def test_the_list_offers_no_bulk_actions(admin_client: Client, row: Task) -> None:
    response = admin_client.get(reverse(CHANGELIST))

    assert response.context["action_form"] is None


def test_the_detail_page_is_view_only(admin_client: Client, row: Task) -> None:
    response = admin_client.get(reverse("admin:tasks_task_change", args=[row.pk]))

    assert response.status_code == 200
    assert response.context["has_change_permission"] is False


def test_tasks_cannot_be_added(admin_client: Client) -> None:
    response = admin_client.post(reverse("admin:tasks_task_add"), {"title": "Skips the rules"})

    assert response.status_code == 403
    assert not Task.objects.exists()


def test_tasks_cannot_be_changed(admin_client: Client, row: Task) -> None:
    response = admin_client.post(
        reverse("admin:tasks_task_change", args=[row.pk]), {"title": "Changed"}
    )

    assert response.status_code == 403
    row.refresh_from_db()
    assert row.title == "Write the spec"


def test_tasks_cannot_be_deleted(admin_client: Client, row: Task) -> None:
    response = admin_client.post(reverse("admin:tasks_task_delete", args=[row.pk]), {"post": "yes"})

    assert response.status_code == 403
    assert Task.objects.filter(pk=row.pk).exists()
