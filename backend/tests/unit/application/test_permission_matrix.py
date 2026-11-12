"""The permission matrix (spec section 3) run through every write use case.

The domain test checks the rule; this one checks that each use case asks for the right row.
View is not here: reads go through the visible_tasks selector (iteration 2).
"""

from collections.abc import Callable
from dataclasses import dataclass

import pytest

from tasks.application.assign_task import AssignTask
from tasks.application.delete_task import DeleteTask
from tasks.application.status_changes import CompleteTask, ReopenTask, StartTask
from tasks.application.update_task import UpdateTask
from tasks.domain.actor import Actor
from tasks.domain.errors import DomainError, NotAllowed, TaskNotFound
from tasks.domain.status import Status
from tests.unit.builders import (
    ADMIN,
    ASSIGNEE,
    EARLIER,
    OTHER_USER,
    OTHER_USER_ID,
    OWNER,
    stored_task,
)
from tests.unit.fakes import FakeUserLookup, FixedClock, InMemoryTaskRepository, RecordingNotifier
from tests.unit.permission_matrix import ALLOWED, MATRIX, NOT_ALLOWED, NOT_FOUND, ROLES


@dataclass
class Ports:
    repository: InMemoryTaskRepository
    users: FakeUserLookup
    notifier: RecordingNotifier
    clock: FixedClock


type Run = Callable[[Ports, Actor, int], object]

# Matrix action -> the use cases it covers: (name, status the task starts in, how to run it).
USE_CASES: dict[str, list[tuple[str, Status, Run]]] = {
    "edit": [
        (
            "update",
            Status.TO_DO,
            lambda p, a, i: UpdateTask(p.repository, p.clock).execute(a, i, title="New title"),
        ),
    ],
    "assign": [
        (
            "assign",
            Status.TO_DO,
            lambda p, a, i: AssignTask(p.repository, p.users, p.notifier, p.clock).execute(
                a, i, OTHER_USER_ID
            ),
        ),
    ],
    "change_status": [
        ("start", Status.TO_DO, lambda p, a, i: StartTask(p.repository, p.clock).execute(a, i)),
        (
            "complete",
            Status.TO_DO,
            lambda p, a, i: CompleteTask(p.repository, p.clock).execute(a, i),
        ),
        ("reopen", Status.DONE, lambda p, a, i: ReopenTask(p.repository, p.clock).execute(a, i)),
    ],
    "delete": [
        ("delete", Status.TO_DO, lambda p, a, i: DeleteTask(p.repository).execute(a, i)),
    ],
}
ACTORS = {"owner": OWNER, "assignee": ASSIGNEE, "admin": ADMIN, "anyone else": OTHER_USER}
ERRORS: dict[str, type[DomainError]] = {NOT_ALLOWED: NotAllowed, NOT_FOUND: TaskNotFound}

CASES = [
    pytest.param(run, status, role, outcome, id=f"{name}-{role}-{outcome}")
    for action, outcomes in MATRIX.items()
    if action != "view"
    for name, status, run in USE_CASES[action]
    for role, outcome in zip(ROLES, outcomes, strict=True)
]


def test_every_write_action_in_the_matrix_has_its_use_cases() -> None:
    assert set(USE_CASES) == set(MATRIX) - {"view"}


@pytest.mark.parametrize(("run", "status", "role", "outcome"), CASES)
def test_permission_matrix_through_the_use_cases(
    repository: InMemoryTaskRepository,
    users: FakeUserLookup,
    notifier: RecordingNotifier,
    clock: FixedClock,
    run: Run,
    status: Status,
    role: str,
    outcome: str,
) -> None:
    ports = Ports(repository, users, notifier, clock)
    task = stored_task(
        repository, status=status, completed_at=EARLIER if status is Status.DONE else None
    )
    assert task.id is not None

    if outcome == ALLOWED:
        run(ports, ACTORS[role], task.id)
    else:
        with pytest.raises(ERRORS[outcome]):
            run(ports, ACTORS[role], task.id)
        assert repository.all() == [task]
        assert notifier.assignments == []
