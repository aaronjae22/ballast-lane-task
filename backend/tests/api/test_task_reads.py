"""GET /api/tasks/ and /api/tasks/{id}/: reading tasks (spec section 5, ADRs 0003 and 0014).

Every read goes through visible_tasks(user), so a task the user can't see isn't listed and
its detail is 404, the same answer as for a task that doesn't exist.
"""

from datetime import date
from unittest import mock

import pytest
from django.db.models import Max
from pytest_django import DjangoAssertNumQueries
from rest_framework.test import APIClient

from accounts.models import User
from tasks import models
from tasks.domain.status import Status
from tests.api.conftest import ClientFor
from tests.conftest import MakeUser, StoreTask
from tests.unit.builders import EARLIER, NOW, TODAY, TOMORROW
from tests.unit.overdue_cases import OVERDUE_CASES

pytestmark = pytest.mark.django_db

TASKS_URL = "/api/tasks/"


def detail_url(task_id: int | None) -> str:
    return f"{TASKS_URL}{task_id}/"


def listed_ids(client: APIClient, **params: object) -> list[int]:
    response = client.get(TASKS_URL, params)
    assert response.status_code == 200
    return [task["id"] for task in response.json()["results"]]


def test_the_list_has_only_the_tasks_the_user_can_see(
    owner: User, other_user: User, store_task: StoreTask, client_for: ClientFor
) -> None:
    own = store_task(owner)
    store_task(other_user)

    response = client_for(owner).get(TASKS_URL)

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert [task["id"] for task in response.json()["results"]] == [own.id]


def test_a_task_shows_every_field_and_its_people_by_name(
    owner: User, make_user: MakeUser, store_task: StoreTask, client_for: ClientFor
) -> None:
    assignee = make_user("grace", first_name="Grace", last_name="Hopper")
    task = store_task(
        owner,
        assignee,
        title="Write the spec",
        description="Agreed in the kickoff",
        status=Status.DONE,
        due_date=TOMORROW,
        completed_at=NOW,
        created_at=EARLIER,
        updated_at=NOW,
    )

    response = client_for(owner).get(detail_url(task.id))

    assert response.status_code == 200
    assert response.json() == {
        "id": task.id,
        "title": "Write the spec",
        "description": "Agreed in the kickoff",
        "status": "done",
        "due_date": "2026-11-12",
        "is_overdue": False,
        "owner": {"id": owner.pk, "name": "owner"},
        "assignee": {"id": assignee.pk, "name": "Grace Hopper"},
        "completed_at": "2026-11-11T15:30:00Z",
        "created_at": "2026-11-01T09:00:00Z",
        "updated_at": "2026-11-11T15:30:00Z",
    }


def test_an_unassigned_task_has_a_null_assignee(
    owner: User, store_task: StoreTask, client_for: ClientFor
) -> None:
    task = store_task(owner)

    assert client_for(owner).get(detail_url(task.id)).json()["assignee"] is None


@pytest.mark.parametrize(
    ("status", "due_date", "overdue"), list(OVERDUE_CASES.values()), ids=list(OVERDUE_CASES)
)
def test_is_overdue_agrees_with_task_is_overdue_on_every_shared_case(
    owner: User,
    store_task: StoreTask,
    client_for: ClientFor,
    status: Status,
    due_date: date | None,
    overdue: bool,
) -> None:
    """Judged on the same TODAY as the domain's test, through the real clock."""
    task = store_task(owner, status=status, due_date=due_date)
    client = client_for(owner)

    with mock.patch("django.utils.timezone.now", return_value=NOW):
        detail = client.get(detail_url(task.id)).json()
        listed = client.get(TASKS_URL).json()["results"]

    assert task.is_overdue(TODAY) is overdue
    assert detail["is_overdue"] is overdue
    assert [item["is_overdue"] for item in listed] == [overdue]


def test_a_task_the_user_cant_see_is_404_like_a_missing_one(
    owner: User, other_user: User, store_task: StoreTask, client_for: ClientFor
) -> None:
    hidden = store_task(other_user)
    missing_id = models.Task.objects.aggregate(highest=Max("pk"))["highest"] + 1
    client = client_for(owner)

    for task_id in (hidden.id, missing_id):
        response = client.get(detail_url(task_id))

        assert response.status_code == 404
        assert response.json() == {"detail": f"Task {task_id} not found."}


@pytest.mark.parametrize(
    "task_id",
    [str(2**63), "9" * 5000],
    ids=["past-the-largest-id", "past-pythons-int-conversion-limit"],
)
def test_an_id_no_task_can_have_is_404(owner: User, client_for: ClientFor, task_id: str) -> None:
    assert client_for(owner).get(detail_url(task_id)).status_code == 404


@pytest.mark.parametrize("url", [TASKS_URL, detail_url(1)])
def test_reading_tasks_needs_a_token(api_client: APIClient, url: str) -> None:
    assert api_client.get(url).status_code == 401


# Pagination (ADR 0014): 20 a page, ?page_size= up to 50.


@pytest.fixture
def many_tasks(owner: User, store_task: StoreTask) -> list[int | None]:
    return [store_task(owner, title=f"Task {n}").id for n in range(55)]


def test_the_list_comes_20_tasks_a_page(
    owner: User, many_tasks: list[int | None], client_for: ClientFor
) -> None:
    client = client_for(owner)

    first = client.get(TASKS_URL).json()
    second = client.get(TASKS_URL, {"page": 2}).json()

    assert first["count"] == 55
    assert len(first["results"]) == 20
    assert first["previous"] is None
    assert first["next"] is not None
    assert len(second["results"]) == 20
    assert second["previous"] is not None


@pytest.mark.parametrize(
    ("page_size", "expected"),
    [("5", 5), ("50", 50), ("51", 50), ("not-a-number", 20)],
    ids=["smaller", "the-largest", "capped-at-50", "invalid-falls-back"],
)
def test_page_size_is_adjustable_up_to_50(
    owner: User,
    many_tasks: list[int | None],
    client_for: ClientFor,
    page_size: str,
    expected: int,
) -> None:
    response = client_for(owner).get(TASKS_URL, {"page_size": page_size})

    assert len(response.json()["results"]) == expected


def test_the_pages_together_list_every_task_once(
    owner: User, many_tasks: list[int | None], client_for: ClientFor
) -> None:
    client = client_for(owner)

    pages = [listed_ids(client, page=page, page_size=25) for page in (1, 2, 3)]

    assert sorted(task_id for page in pages for task_id in page) == sorted(many_tasks)


def test_a_page_past_the_end_is_404(
    owner: User, many_tasks: list[int | None], client_for: ClientFor
) -> None:
    assert client_for(owner).get(TASKS_URL, {"page": 4}).status_code == 404


# Query counts (spec section 9): more tasks never mean more queries.


@pytest.fixture
def tasks_with_different_people(
    owner: User, make_user: MakeUser, store_task: StoreTask
) -> list[int | None]:
    """Each with its own assignee, so a missing select_related would cost a query per task."""
    return [store_task(owner, make_user(f"assignee-{n}")).id for n in range(15)]


def test_listing_tasks_takes_three_queries_however_many_there_are(
    owner: User,
    tasks_with_different_people: list[int | None],
    client_for: ClientFor,
    django_assert_max_num_queries: DjangoAssertNumQueries,
) -> None:
    """The user (from the token), the count for pagination, and the page with its people."""
    client = client_for(owner)

    with django_assert_max_num_queries(3):
        response = client.get(TASKS_URL)

    assert len(response.json()["results"]) == 15


def test_showing_a_task_takes_two_queries(
    owner: User,
    tasks_with_different_people: list[int | None],
    client_for: ClientFor,
    django_assert_max_num_queries: DjangoAssertNumQueries,
) -> None:
    client = client_for(owner)

    with django_assert_max_num_queries(2):
        response = client.get(detail_url(tasks_with_different_people[0]))

    assert response.status_code == 200
