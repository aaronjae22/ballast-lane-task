"""TaskFilter: the list filters from spec section 5, applied to visible_tasks(user).

Each test filters the queryset the view will give it, so the filters can only narrow what the
user may see. Invalid values are form errors and empty values leave a filter off (ADR 0013).
"""

from datetime import date
from unittest import mock

import pytest
from django.db.models import Max
from django.test import RequestFactory

from accounts.models import User
from tasks.api.filters import TaskFilter
from tasks.domain.status import Status
from tasks.selectors import visible_tasks
from tests.integration.conftest import StoreTask
from tests.unit.builders import NOW, TODAY, TOMORROW, YESTERDAY
from tests.unit.fakes import FixedClock
from tests.unit.overdue_cases import OVERDUE_CASES

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
        ("write the", {"spec"}),
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


# Overdue: the same cases as Task.is_overdue(), judged on the same TODAY.

CLOCK = FixedClock(now=NOW, today=TODAY)


@pytest.mark.parametrize(
    ("status", "due_date", "overdue"), list(OVERDUE_CASES.values()), ids=list(OVERDUE_CASES)
)
def test_overdue_agrees_with_task_is_overdue_on_every_shared_case(
    owner: User, store_task: StoreTask, status: Status, due_date: date | None, overdue: bool
) -> None:
    task = store_task(owner, status=status, due_date=due_date)

    assert task.is_overdue(TODAY) is overdue
    assert (task.id in run_filters(owner, {"overdue": "true"}, clock=CLOCK)) is overdue
    assert (task.id in run_filters(owner, {"overdue": "false"}, clock=CLOCK)) is not overdue


def test_an_empty_overdue_leaves_the_filter_off(owner: User, store_task: StoreTask) -> None:
    late = store_task(owner, due_date=YESTERDAY)
    on_time = store_task(owner, due_date=TOMORROW)

    assert run_filters(owner, {"overdue": ""}, clock=CLOCK) == {late.id, on_time.id}


def test_overdue_judges_today_by_the_real_clock_by_default(
    owner: User, store_task: StoreTask
) -> None:
    late = store_task(owner, due_date=YESTERDAY)
    store_task(owner, due_date=TODAY)

    with mock.patch("django.utils.timezone.now", return_value=NOW):
        assert run_filters(owner, {"overdue": "true"}) == {late.id}


@pytest.mark.parametrize("value", ["yes", "1", "True", "maybe"])
def test_overdue_takes_only_true_or_false(owner: User, value: str) -> None:
    assert "overdue" in errors(owner, {"overdue": value})


# Assignee: "me" or a user id, within what the user may see.


@pytest.fixture
def by_assignee(
    owner: User, assignee: User, other_user: User, store_task: StoreTask
) -> dict[str, int | None]:
    return {
        "owner-to-self": store_task(owner, owner).id,
        "owner-to-assignee": store_task(owner, assignee).id,
        "owner-unassigned": store_task(owner).id,
        "other-to-owner": store_task(other_user, owner).id,
        # Not visible to the owner: it must never come back, whatever the filter.
        "other-to-assignee": store_task(other_user, assignee).id,
    }


def test_assignee_me_keeps_the_tasks_assigned_to_the_user(
    owner: User, by_assignee: dict[str, int | None]
) -> None:
    expected = {by_assignee["owner-to-self"], by_assignee["other-to-owner"]}

    assert run_filters(owner, {"assignee": "me"}) == expected


def test_assignee_id_keeps_that_users_tasks_among_those_visible(
    owner: User, assignee: User, by_assignee: dict[str, int | None]
) -> None:
    assert run_filters(owner, {"assignee": str(assignee.pk)}) == {by_assignee["owner-to-assignee"]}


def test_an_unknown_assignee_id_matches_nothing(
    owner: User, by_assignee: dict[str, int | None]
) -> None:
    unknown_id = User.objects.aggregate(highest=Max("pk"))["highest"] + 1

    assert run_filters(owner, {"assignee": str(unknown_id)}) == set()


def test_an_empty_assignee_leaves_the_filter_off(
    owner: User, by_assignee: dict[str, int | None]
) -> None:
    visible = set(by_assignee.values()) - {by_assignee["other-to-assignee"]}

    assert run_filters(owner, {"assignee": ""}) == visible


@pytest.mark.parametrize("value", ["ME", "someone", "-1", "0", "1.5"])
def test_assignee_takes_only_me_or_a_user_id(owner: User, value: str) -> None:
    assert "assignee" in errors(owner, {"assignee": value})


def test_assignee_combines_with_status_overdue_and_dates(
    owner: User, store_task: StoreTask
) -> None:
    match = store_task(owner, owner, status=Status.IN_PROGRESS, due_date=YESTERDAY)
    store_task(owner, owner, status=Status.TO_DO, due_date=YESTERDAY)
    store_task(owner, owner, status=Status.IN_PROGRESS, due_date=TOMORROW)
    store_task(owner, status=Status.IN_PROGRESS, due_date=YESTERDAY)

    params: Params = {"assignee": "me", "status": "in_progress", "overdue": "true"}

    assert run_filters(owner, params, clock=CLOCK) == {match.id}
