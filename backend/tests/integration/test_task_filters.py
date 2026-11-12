"""TaskFilter: the list filters from spec section 5, applied to visible_tasks(user).

Each test filters the queryset the view will give it, so the filters can only narrow what the
user may see. Invalid values are form errors and empty values leave a filter off (ADR 0013).
"""

import pytest
from django.test import RequestFactory

from accounts.models import User
from tasks.api.filters import TaskFilter
from tasks.domain.status import Status
from tasks.selectors import visible_tasks
from tests.integration.conftest import StoreTask
from tests.unit.builders import TODAY, TOMORROW, YESTERDAY

pytestmark = pytest.mark.django_db

type Params = dict[str, str | list[str]]


def make_filterset(user: User, params: Params, **filterset_kwargs: object) -> TaskFilter:
    """The FilterSet as the view will build it: from a real query string, for this user."""
    request = RequestFactory().get("/api/tasks/", params)
    request.user = user
    return TaskFilter(
        request.GET, queryset=visible_tasks(user), request=request, **filterset_kwargs
    )


def run_filters(user: User, params: Params, **filterset_kwargs: object) -> set[int]:
    """The ids of the tasks the filters return; the params must be valid."""
    filterset = make_filterset(user, params, **filterset_kwargs)
    assert filterset.is_valid(), filterset.errors
    return set(filterset.qs.values_list("id", flat=True))


def errors(user: User, params: Params) -> dict[str, list[str]]:
    filterset = make_filterset(user, params)
    assert not filterset.is_valid()
    return dict(filterset.errors)


# Status: one or several values, as repeated parameters.


@pytest.fixture
def by_status(owner: User, store_task: StoreTask) -> dict[Status, int | None]:
    return {status: store_task(owner, status=status).id for status in Status}


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        ({"status": "to_do"}, {Status.TO_DO}),
        ({"status": ["to_do", "done"]}, {Status.TO_DO, Status.DONE}),
        ({"status": ""}, set(Status)),
        ({}, set(Status)),
    ],
    ids=["one", "several", "empty", "absent"],
)
def test_status_keeps_the_tasks_in_any_of_the_given_statuses(
    owner: User, by_status: dict[Status, int | None], params: Params, expected: set[Status]
) -> None:
    assert run_filters(owner, params) == {by_status[status] for status in expected}


@pytest.mark.parametrize("value", ["archived", "to_do,done", "TO_DO"])
def test_an_unknown_status_is_an_error(owner: User, value: str) -> None:
    assert "status" in errors(owner, {"status": value})


# Due dates: both bounds include the boundary day; tasks without a due date never match.


@pytest.fixture
def by_due_date(owner: User, store_task: StoreTask) -> dict[str, int | None]:
    return {
        "yesterday": store_task(owner, due_date=YESTERDAY).id,
        "today": store_task(owner, due_date=TODAY).id,
        "tomorrow": store_task(owner, due_date=TOMORROW).id,
        "none": store_task(owner, due_date=None).id,
    }


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        ({"due_after": str(TODAY)}, {"today", "tomorrow"}),
        ({"due_before": str(TODAY)}, {"yesterday", "today"}),
        ({"due_after": str(TODAY), "due_before": str(TODAY)}, {"today"}),
        (
            {"due_after": str(YESTERDAY), "due_before": str(TOMORROW)},
            {"yesterday", "today", "tomorrow"},
        ),
        ({"due_after": str(TOMORROW), "due_before": str(YESTERDAY)}, set()),
        ({"due_after": "", "due_before": ""}, {"yesterday", "today", "tomorrow", "none"}),
    ],
    ids=["after", "before", "one-day", "whole-range", "empty-range", "empty-values"],
)
def test_due_after_and_due_before_include_the_boundary_day(
    owner: User, by_due_date: dict[str, int | None], params: Params, expected: set[str]
) -> None:
    assert run_filters(owner, params) == {by_due_date[name] for name in expected}


@pytest.mark.parametrize("name", ["due_after", "due_before"])
@pytest.mark.parametrize("value", ["2026-13-01", "tomorrow"])
def test_an_invalid_date_is_an_error(owner: User, name: str, value: str) -> None:
    assert name in errors(owner, {name: value})


# Search: part of the title, ignoring case; the description isn't searched.


@pytest.fixture
def by_title(owner: User, store_task: StoreTask) -> dict[str, int | None]:
    return {
        "spec": store_task(owner, title="Write the spec").id,
        "review": store_task(owner, title="Review the SPEC draft").id,
        "venue": store_task(owner, title="Book the venue", description="See the spec").id,
    }


@pytest.mark.parametrize(
    ("search", "expected"),
    [
        ("spec", {"spec", "review"}),
        ("Spec", {"spec", "review"}),
        ("the spec", {"spec"}),
        ("budget", set()),
        ("", {"spec", "review", "venue"}),
    ],
    ids=["lowercase", "mixed-case", "phrase", "no-match", "empty"],
)
def test_search_matches_part_of_the_title_ignoring_case(
    owner: User, by_title: dict[str, int | None], search: str, expected: set[str]
) -> None:
    assert run_filters(owner, {"search": search}) == {by_title[name] for name in expected}


# Together, and within what the user may see.


def test_filters_combine_and_each_one_narrows_the_result(
    owner: User, store_task: StoreTask
) -> None:
    match = store_task(owner, title="Write the spec", due_date=TODAY)
    store_task(owner, title="Spec review", status=Status.DONE, due_date=TODAY)
    store_task(owner, title="Spec slides", due_date=TOMORROW)
    store_task(owner, title="Book the venue", due_date=TODAY)

    params: Params = {"status": "to_do", "due_before": str(TODAY), "search": "spec"}

    assert run_filters(owner, params) == {match.id}


def test_filters_never_return_a_task_the_user_cannot_see(
    owner: User, other_user: User, store_task: StoreTask
) -> None:
    own = store_task(owner, title="Write the spec")
    store_task(other_user, title="Write the spec")

    assert run_filters(owner, {"status": "to_do", "search": "spec"}) == {own.id}
