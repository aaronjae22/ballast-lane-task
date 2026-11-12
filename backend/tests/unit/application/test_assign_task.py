"""AssignTask: assign, reassign and unassign, and the assignment email (spec section 3)."""

import pytest

from tasks.application.assign_task import AssignTask
from tasks.domain.actor import Actor
from tasks.domain.errors import DomainValidationError, NotAllowed, TaskNotFound
from tests.unit.builders import (
    ADMIN,
    ADMIN_ID,
    ASSIGNEE,
    ASSIGNEE_ID,
    NOW,
    OTHER_USER,
    OTHER_USER_ID,
    OWNER,
    OWNER_ID,
    stored_task,
)
from tests.unit.fakes import FakeUserLookup, FixedClock, InMemoryTaskRepository, RecordingNotifier


@pytest.fixture
def assign_task(
    repository: InMemoryTaskRepository,
    users: FakeUserLookup,
    notifier: RecordingNotifier,
    clock: FixedClock,
) -> AssignTask:
    return AssignTask(repository, users, notifier, clock)


@pytest.mark.parametrize(
    ("current", "actor", "new", "emailed"),
    [
        (None, OWNER, ASSIGNEE_ID, ASSIGNEE_ID),
        (ASSIGNEE_ID, OWNER, OTHER_USER_ID, OTHER_USER_ID),
        (None, ADMIN, OWNER_ID, OWNER_ID),
        (None, OWNER, OWNER_ID, None),
        (None, ADMIN, ADMIN_ID, None),
        (ASSIGNEE_ID, OWNER, None, None),
        (ASSIGNEE_ID, OWNER, ASSIGNEE_ID, None),
    ],
    ids=[
        "assign-someone-else",
        "reassign-to-someone-else",
        "admin-assigns-the-owner",
        "owner-self-assigns",
        "admin-self-assigns",
        "unassign",
        "same-person-again",
    ],
)
def test_the_assignee_is_saved_and_emailed_only_when_it_changes_to_someone_else(
    assign_task: AssignTask,
    repository: InMemoryTaskRepository,
    notifier: RecordingNotifier,
    current: int | None,
    actor: Actor,
    new: int | None,
    emailed: int | None,
) -> None:
    task = stored_task(repository, assignee_id=current)

    updated = assign_task.execute(actor, task.id, new)

    assert (updated.assignee_id, updated.updated_at) == (new, NOW)
    assert repository.get(task.id) == updated
    assert notifier.assignments == ([] if emailed is None else [(task.id, emailed)])


def test_an_assignee_who_isnt_an_active_user_is_rejected_saves_nothing_and_sends_no_email(
    assign_task: AssignTask, repository: InMemoryTaskRepository, notifier: RecordingNotifier
) -> None:
    task = stored_task(repository, assignee_id=None)

    with pytest.raises(DomainValidationError) as error:
        assign_task.execute(OWNER, task.id, 99)

    assert error.value.field == "assignee_id"
    assert repository.get(task.id) == task
    assert notifier.assignments == []


def test_reassigning_a_deactivated_assignee_who_already_has_the_task_is_allowed(
    repository: InMemoryTaskRepository, notifier: RecordingNotifier, clock: FixedClock
) -> None:
    task = stored_task(repository, assignee_id=ASSIGNEE_ID)
    users = FakeUserLookup({OWNER_ID})

    updated = AssignTask(repository, users, notifier, clock).execute(OWNER, task.id, ASSIGNEE_ID)

    assert updated.assignee_id == ASSIGNEE_ID
    assert notifier.assignments == []


def test_a_missing_task_is_not_found(assign_task: AssignTask) -> None:
    with pytest.raises(TaskNotFound):
        assign_task.execute(OWNER, 99, ASSIGNEE_ID)


@pytest.mark.parametrize(
    ("actor", "error"),
    [(ASSIGNEE, NotAllowed), (OTHER_USER, TaskNotFound)],
    ids=["assignee-NotAllowed", "anyone-else-TaskNotFound"],
)
def test_others_cant_assign_and_no_email_is_sent(
    assign_task: AssignTask,
    repository: InMemoryTaskRepository,
    notifier: RecordingNotifier,
    actor: Actor,
    error: type[Exception],
) -> None:
    task = stored_task(repository, assignee_id=ASSIGNEE_ID)

    with pytest.raises(error):
        assign_task.execute(actor, task.id, OTHER_USER_ID)

    assert repository.get(task.id) == task
    assert notifier.assignments == []
