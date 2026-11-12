"""CreateTask: any signed-in user creates a task, optionally with an assignee (spec section 3)."""

from datetime import UTC, date, datetime

import pytest

from tasks.application.create_task import CreateTask
from tasks.domain.errors import DomainValidationError
from tasks.domain.status import Status
from tests.unit.builders import (
    ASSIGNEE_ID,
    NOW,
    OTHER_USER,
    OTHER_USER_ID,
    OWNER,
    OWNER_ID,
    TODAY,
    TOMORROW,
    YESTERDAY,
)
from tests.unit.fakes import FakeUserLookup, FixedClock, InMemoryTaskRepository, RecordingNotifier


@pytest.fixture
def create_task(
    repository: InMemoryTaskRepository,
    users: FakeUserLookup,
    notifier: RecordingNotifier,
    clock: FixedClock,
) -> CreateTask:
    return CreateTask(repository, users, notifier, clock)


def test_any_user_can_create_a_task_and_becomes_its_owner(
    create_task: CreateTask, repository: InMemoryTaskRepository
) -> None:
    task = create_task.execute(
        OTHER_USER, title="Write the spec", description="Sections 3 and 4", due_date=TOMORROW
    )

    assert task.id is not None
    assert (task.owner_id, task.status, task.created_at) == (OTHER_USER_ID, Status.TO_DO, NOW)
    assert (task.description, task.due_date) == ("Sections 3 and 4", TOMORROW)
    assert repository.all() == [task]


@pytest.mark.parametrize(
    ("fields", "field"),
    [({"title": ""}, "title"), ({"title": "Ok", "due_date": YESTERDAY}, "due_date")],
    ids=["empty-title", "past-due-date"],
)
def test_a_broken_rule_saves_nothing(
    create_task: CreateTask,
    repository: InMemoryTaskRepository,
    fields: dict[str, object],
    field: str,
) -> None:
    with pytest.raises(DomainValidationError) as error:
        create_task.execute(OWNER, **fields)

    assert error.value.field == field
    assert repository.all() == []


def test_an_assignee_who_isnt_an_active_user_saves_nothing_and_sends_no_email(
    create_task: CreateTask, repository: InMemoryTaskRepository, notifier: RecordingNotifier
) -> None:
    unknown_user_id = 99

    with pytest.raises(DomainValidationError) as error:
        create_task.execute(OWNER, title="Write the spec", assignee_id=unknown_user_id)

    assert error.value.field == "assignee_id"
    assert repository.all() == []
    assert notifier.assignments == []


def test_creating_a_task_for_someone_else_emails_them_once(
    create_task: CreateTask, notifier: RecordingNotifier
) -> None:
    task = create_task.execute(OWNER, title="Write the spec", assignee_id=ASSIGNEE_ID)

    assert task.assignee_id == ASSIGNEE_ID
    assert notifier.assignments == [(task.id, ASSIGNEE_ID)]


@pytest.mark.parametrize("assignee_id", [OWNER_ID, None], ids=["self", "no-assignee"])
def test_creating_a_task_for_yourself_or_no_one_sends_no_email(
    create_task: CreateTask, notifier: RecordingNotifier, assignee_id: int | None
) -> None:
    create_task.execute(OWNER, title="Write the spec", assignee_id=assignee_id)

    assert notifier.assignments == []


def test_today_comes_from_the_clock_not_from_the_utc_date_of_now(
    repository: InMemoryTaskRepository, users: FakeUserLookup, notifier: RecordingNotifier
) -> None:
    # 02:00 UTC on the 12th is still the 11th in a time zone west of UTC.
    clock = FixedClock(now=datetime(2026, 11, 12, 2, 0, tzinfo=UTC), today=date(2026, 11, 11))

    task = CreateTask(repository, users, notifier, clock).execute(
        OWNER, title="Write the spec", due_date=TODAY
    )

    assert (task.due_date, task.created_at) == (TODAY, clock.now())
