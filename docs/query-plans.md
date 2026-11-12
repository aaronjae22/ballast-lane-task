# Query plans of the task list's filters

Spec section 9 asks for the filter indexes to be checked with `EXPLAIN`. This page records how, what the plans show on 100,000 tasks, and what that leads to. Measured on 2026-11-12 with PostgreSQL 14.13 on the development machine; CI runs PostgreSQL 17.

## Why a test-sized table proves nothing

On a table of a few dozen rows, Postgres reads every page whatever the indexes, because that's cheaper than an index lookup. So there are two checks:

- **A regression test**, `tests/integration/test_query_plans.py`. It turns sequential scans off for its transaction (`SET LOCAL enable_seqscan = off`). The planner then takes an index whenever the query's shape allows one. The test asserts that the status and overdue filters use `tasks_task_status_due_idx`, with `status` in the index condition. A condition on `due_date` alone can also show up there, but over a scan of the whole index, because `due_date` is the index's second column. The test fails if a change makes these filters unable to use the index. A second test checks that no filter makes the query `DISTINCT` (see below).
- **A measurement on realistic data**, below. Whether Postgres picks the index on real data depends on the table's statistics, so this one runs once and is recorded here, not in CI.

## How the measurement was made

The script builds 100,000 tasks for 50 users and an admin, inside a transaction it rolls back, so the database is left as it was:
- About 70% of the tasks are done, 20% to do and 10% in progress: a board that has been in use for a while.
- One in five has no due date. The rest are due in the last 120 days or the next 30.

It runs `ANALYZE`, then `EXPLAIN (ANALYZE, BUFFERS)` on the first page of the list. That's the same query the API sends: `visible_tasks(user)`, `TaskFilter` with its default ordering, and `LIMIT 20`. Save the script below as `backend/explain_filters.py` and run it against a migrated database:

```bash
DJANGO_DEBUG=true DATABASE_URL=postgres://taskboard:taskboard@localhost:5432/taskboard \
  uv run python manage.py shell < explain_filters.py
```

```python
import random
from datetime import timedelta

from django.db import connection, transaction
from django.test import RequestFactory
from django.utils import timezone

from accounts.models import User
from tasks.api.filters import TaskFilter
from tasks.models import Task
from tasks.selectors import visible_tasks


class Rollback(Exception):
    """Raised at the end, so nothing this script creates is kept."""


def page_query(user, params):
    """The first page of the task list, as the API asks for it."""
    request = RequestFactory().get("/api/tasks/", params)
    request.user = user
    filterset = TaskFilter(request.GET, queryset=visible_tasks(user), request=request)
    assert filterset.is_valid(), filterset.errors
    return filterset.qs[:20]


random.seed(14)
try:
    with transaction.atomic():
        today, now = timezone.localdate(), timezone.now()
        users = User.objects.bulk_create(User(username=f"plan-user-{n}") for n in range(50))
        admin = User.objects.create(username="plan-admin", is_staff=True)
        # A board that has run for a while: most tasks done, due dates over the last four months
        # and the next month, one in five without a due date.
        statuses = ["done"] * 7 + ["to_do"] * 2 + ["in_progress"]
        tasks = []
        for n in range(100_000):
            status = random.choice(statuses)
            due_date = None if random.random() < 0.2 else today + timedelta(days=random.randint(-120, 30))
            tasks.append(
                Task(
                    title=f"Task {n}",
                    status=status,
                    due_date=due_date,
                    owner=random.choice(users),
                    assignee=random.choice([*users, None]),
                    completed_at=now if status == "done" else None,
                    created_at=now,
                    updated_at=now,
                )
            )
        Task.objects.bulk_create(tasks, batch_size=5000)
        with connection.cursor() as cursor:
            cursor.execute("ANALYZE tasks_task")
            cursor.execute("SELECT version()")
            print(cursor.fetchone()[0])
            cursor.execute("SELECT status, count(*) FROM tasks_task GROUP BY status ORDER BY status")
            print(cursor.fetchall())

        cases = [
            ("admin, ?overdue=true", admin, {"overdue": "true"}),
            ("admin, ?status=to_do", admin, {"status": "to_do"}),
            ("admin, ?status=in_progress&due_before=today", admin, {"status": "in_progress", "due_before": str(today)}),
            ("admin, ?due_before=today (no status)", admin, {"due_before": str(today)}),
            ("admin, ?search=task 4242", admin, {"search": "task 4242"}),
            ("admin, no filters", admin, {}),
            ("non-admin, ?overdue=true", users[0], {"overdue": "true"}),
            ("non-admin, no filters", users[0], {}),
        ]
        for label, user, params in cases:
            print(f"\n### {label}\n")
            print(page_query(user, params).explain(analyze=True, buffers=True))
        raise Rollback
except Rollback:
    pass
```

## Results

| Query (first page of 20) | Plan | Time |
|---|---|---|
| Admin, `?status=to_do` | Index scan on `(status, due_date)`, incremental sort, stops after 20 rows | 0.22 ms |
| Admin, `?status=in_progress&due_before=today` | Index scan on `(status, due_date)` with both conditions | 0.11 ms |
| Admin, `?overdue=true` | Bitmap index scan on `(status, due_date)` (19,023 rows), then a top-20 sort | 14.0 ms |
| Non-admin, `?overdue=true` | `BitmapAnd` of the owner/assignee `BitmapOr` and `(status, due_date)` | 1.4 ms |
| Non-admin, no filters | `BitmapOr` of the owner and assignee indexes (3,883 rows), top-20 sort | 3.1 ms |
| Admin, no filters | Parallel sequential scan, top-20 sort | 33.6 ms |
| Admin, `?due_before=today` | Parallel sequential scan, top-20 sort | 29.3 ms |
| Admin, `?search=task 4242` | Sequential scan with `upper(title) LIKE` | 9.9 ms |

The key lines of each plan:

```text
admin, ?status=to_do
  Limit -> Incremental Sort (Sort Key: due_date, id; Presorted Key: due_date)
    -> Index Scan using tasks_task_status_due_idx on tasks_task
         Index Cond: ((status)::text = 'to_do'::text)
  Execution Time: 0.217 ms

admin, ?overdue=true
  Limit -> Sort (top-N heapsort) -> Hash Joins
    -> Bitmap Index Scan on tasks_task_status_due_idx  (rows=19023)
         Index Cond: ((status = ANY ('{to_do,in_progress}')) AND (due_date IS NOT NULL)
                      AND (due_date < '2026-11-12'::date))
  Execution Time: 13.991 ms

non-admin, ?overdue=true
  -> BitmapAnd
       -> BitmapOr
            -> Bitmap Index Scan on tasks_task_owner_id_db3dcc3e     Index Cond: (owner_id = 1)
            -> Bitmap Index Scan on tasks_task_assignee_id_2c3ca866  Index Cond: (assignee_id = 1)
       -> Bitmap Index Scan on tasks_task_status_due_idx            (the overdue condition)
  Execution Time: 1.418 ms

admin, ?due_before=today
  -> Parallel Seq Scan on tasks_task  Filter: (due_date <= '2026-11-12'::date)
  Execution Time: 29.276 ms
```

## What the plans show

- **The `(status, due_date)` index serves the status and overdue filters.** Overdue is spelled as `status IN ('to_do', 'in_progress') AND due_date < today`, never `status <> 'done'`, so the index can serve it. A single status combined with a due-date bound uses both of the index's columns. Because the index is in due-date order, the default ordering needs only an incremental sort that stops after one page.
- **Visibility for a non-admin is cheap.** `owner OR assignee` becomes a `BitmapOr` of the two foreign-key indexes, and with overdue it's intersected with the status index. A user's own tasks are a small part of the table, so their list is fast without any filter.
- **One fix came out of this, in the same pull request: the status filter used DISTINCT.**
  - django-filter's `MultipleChoiceFilter` defaults to `distinct=True`, which is meant for filters that cross a to-many join.
  - A task has one status, so the DISTINCT never removed a row. But Postgres had to sort whole rows, joined users included, to find duplicates.
  - With DISTINCT, the admin's `?status=to_do` took 17.4 ms: a parallel sequential scan, then a quicksort of about 20,000 rows using 3 MB of memory, then `Unique`. Without it, the index scan and incremental sort take 0.43 ms on the same data.
  - The filter now sets `distinct=False`, and a test checks that no filter makes the query `DISTINCT`.
- **Not served by an index, deliberately for now:**
  - `due_after` or `due_before` without a status, and an admin's list with no filters, sequentially scan the whole table: about 30 ms at 100,000 tasks. `due_date` is the second column of the only index that has it, and PostgreSQL 14 to 17 can't skip-scan the leading `status` column (PostgreSQL 18 can).
  - `search` is `upper(title) LIKE '%...%'`, which no btree index serves.

  At this project's size (a small team, a demo seeded with about 25 tasks) none of these is worth an index yet.

## If the table grows

The candidates, in the order the plans suggest:
- **An index on `(due_date NULLS LAST, id)`.** It matches the default ordering exactly, so the admin's unfiltered list and the due-date-only filters could read one page from the index instead of sorting the whole table.
- **A `pg_trgm` GIN index on `title`** for `search`. That needs the `pg_trgm` extension, so it needs a migration that creates it.

Either would be a migration plus a new case in `tests/integration/test_query_plans.py`.
