"""The task list's filters and ordering through HTTP (spec section 5, ADRs 0013 and 0014).

tests/integration/test_task_filters.py covers each filter's logic on the FilterSet. These
check that the view wires TaskFilter to the request, over visible_tasks: a few cases each,
and an invalid value as a 400 keyed by its parameter, like any validation error.
"""

from unittest import mock

import pytest
from rest_framework.test import APIClient

from accounts.models import User
from tasks.domain.status import Status
from tests.api.conftest import ClientFor
from tests.conftest import StoreTask
from tests.unit.builders import NOW, TODAY, TOMORROW, YESTERDAY

pytestmark = pytest.mark.django_db

TASKS_URL = "/api/tasks/"

type Params = dict[str, str | list[str]]


def listed(client: APIClient, params: Params) -> list[int]:
    response = client.get(TASKS_URL, params)
    assert response.status_code == 200, response.json()
    return [task["id"] for task in response.json()["results"]]


@pytest.fixture
def board(
    owner: User, assignee: User, other_user: User, store_task: StoreTask
) -> dict[str, int | None]:
    """The owner's view: four tasks they can see, and one they can't."""
    return {
        "late": store_task(owner, owner, title="Write the spec", due_date=YESTERDAY).id,
        "today": store_task(
            owner, assignee, title="Review the spec", status=Status.IN_PROGRESS, due_date=TODAY
        ).id,
        "done": store_task(
            owner, title="Book the venue", status=Status.DONE, due_date=YESTERDAY
        ).id,
        "later": store_task(other_user, owner, title="Plan the demo", due_date=TOMORROW).id,
        "hidden": store_task(other_user, assignee, title="Write the spec").id,
    }


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        ({"status": "to_do"}, ["late", "later"]),
        ({"status": ["in_progress", "done"]}, ["done", "today"]),
        ({"due_after": str(TODAY)}, ["today", "later"]),
        ({"due_before": str(YESTERDAY)}, ["late", "done"]),
        ({"due_after": str(TODAY), "due_before": str(TODAY)}, ["today"]),
        ({"overdue": "true"}, ["late"]),
        ({"overdue": "false"}, ["done", "today", "later"]),
        ({"assignee": "me"}, ["late", "later"]),
        ({"search": "SPEC"}, ["late", "today"]),
        ({"status": "to_do", "assignee": "me", "search": "plan"}, ["later"]),
    ],
    ids=[
        "status",
        "statuses",
        "due-after",
        "due-before",
        "due-on",
        "overdue",
        "not-overdue",
        "assignee-me",
        "search",
        "combined",
    ],
)
def test_each_filter_narrows_the_list_and_keeps_its_order(
    owner: User,
    board: dict[str, int | None],
    client_for: ClientFor,
    params: Params,
    expected: list[str],
) -> None:
    """In the default order: soonest due first, ties by id, and no due date last."""
    with mock.patch("django.utils.timezone.now", return_value=NOW):
        assert listed(client_for(owner), params) == [board[name] for name in expected]


def test_an_assignee_id_never_reaches_a_task_the_user_cant_see(
    owner: User, assignee: User, board: dict[str, int | None], client_for: ClientFor
) -> None:
    assert listed(client_for(owner), {"assignee": str(assignee.pk)}) == [board["today"]]


@pytest.mark.parametrize(
    ("ordering", "expected"),
    [
        ("-due_date", ["later", "today", "late", "done"]),
        ("status", ["late", "later", "today", "done"]),
        ("-status,due_date", ["done", "today", "late", "later"]),
    ],
)
def test_ordering_comes_from_the_query_string(
    owner: User,
    board: dict[str, int | None],
    client_for: ClientFor,
    ordering: str,
    expected: list[str],
) -> None:
    assert listed(client_for(owner), {"ordering": ordering}) == [board[name] for name in expected]


@pytest.mark.parametrize(
    ("params", "invalid"),
    [
        ({"status": "archived"}, {"status"}),
        ({"due_after": "tomorrow"}, {"due_after"}),
        ({"due_before": "2026-13-01"}, {"due_before"}),
        ({"overdue": "yes"}, {"overdue"}),
        ({"assignee": "someone"}, {"assignee"}),
        ({"ordering": "title"}, {"ordering"}),
        ({"overdue": "yes", "ordering": "bogus"}, {"overdue", "ordering"}),
    ],
    ids=["status", "due-after", "due-before", "overdue", "assignee", "ordering", "two-at-once"],
)
def test_an_invalid_value_is_400_keyed_by_its_parameter(
    owner: User, client_for: ClientFor, params: Params, invalid: set[str]
) -> None:
    response = client_for(owner).get(TASKS_URL, params)

    assert response.status_code == 400
    assert set(response.json()) == invalid
    assert all(isinstance(messages, list) for messages in response.json().values())
