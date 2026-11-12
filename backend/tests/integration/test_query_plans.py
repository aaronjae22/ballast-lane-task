"""The filter queries against the (status, due_date) index (spec section 9).

On a test-sized table Postgres reads every row whatever the indexes, because a few pages are
cheaper to scan than to look up. So each test turns sequential scans off for its transaction:
the planner then takes an index whenever the query's shape lets it. A test fails if a change
makes these filters unable to use the index. Whether Postgres chooses it on real data depends
on the table's statistics; docs/query-plans.md records the plans on 100,000 tasks.
"""

import pytest
from django.db import connection
from django.test import RequestFactory

from accounts.models import User
from tasks.api.filters import TaskFilter
from tasks.domain.status import Status
from tasks.selectors import visible_tasks
from tests.conftest import StoreTask
from tests.unit.builders import NOW, TODAY, TOMORROW, YESTERDAY
from tests.unit.fakes import FixedClock

pytestmark = pytest.mark.django_db

INDEX = "tasks_task_status_due_idx"
CLOCK = FixedClock(now=NOW, today=TODAY)

type Params = dict[str, str | list[str]]


@pytest.fixture(autouse=True)
def some_tasks(owner: User, store_task: StoreTask) -> None:
    for status in Status:
        for due_date in (YESTERDAY, TODAY, TOMORROW, None):
            store_task(owner, status=status, due_date=due_date)


@pytest.fixture(autouse=True)
def no_sequential_scans() -> None:
    """SET LOCAL lasts until the test's transaction rolls back."""
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL enable_seqscan = off")


def plan(user: User, params: Params) -> str:
    """EXPLAIN of the query the task list runs for these parameters, as an admin sees it.

    An admin's visible_tasks has no owner or assignee condition, so only the filters can use
    an index.
    """
    request = RequestFactory().get("/api/tasks/", params)
    request.user = user
    filterset = TaskFilter(request.GET, queryset=visible_tasks(user), request=request, clock=CLOCK)
    assert filterset.is_valid(), filterset.errors
    return filterset.qs.explain()


@pytest.mark.parametrize(
    ("params", "conditions"),
    [
        ({"overdue": "true"}, ["status", "due_date <"]),
        ({"status": "to_do"}, ["status"]),
        ({"status": ["to_do", "in_progress"]}, ["status"]),
        ({"status": "in_progress", "due_before": str(TODAY)}, ["status", "due_date <="]),
        (
            {"status": "to_do", "due_after": str(TODAY), "ordering": "-due_date"},
            ["status", "due_date >="],
        ),
    ],
    ids=["overdue", "one-status", "several-statuses", "status-and-due-before", "with-ordering"],
)
def test_the_status_and_overdue_filters_use_the_status_due_date_index(
    admin: User, params: Params, conditions: list[str]
) -> None:
    """Status leads the index, so it must be in the index condition: a due-date condition
    alone can still appear there, but over a scan of the whole index."""
    query_plan = plan(admin, params)

    assert INDEX in query_plan, query_plan
    index_condition = next(line for line in query_plan.splitlines() if "Index Cond" in line)
    for condition in conditions:
        assert condition in index_condition, query_plan
