"""Status transitions: start, complete and reopen (spec section 3)."""

from dataclasses import replace

import pytest

from tasks.domain import errors
from tasks.domain.status import Status
from tests.unit.builders import EARLIER, NOW, make_task


def test_start_moves_a_to_do_task_to_in_progress() -> None:
    task = make_task(status=Status.TO_DO)

    task.start(now=NOW)

    assert (task.status, task.completed_at, task.updated_at) == (Status.IN_PROGRESS, None, NOW)


@pytest.mark.parametrize("status", [Status.TO_DO, Status.IN_PROGRESS])
def test_complete_moves_a_task_to_done_and_sets_completed_at(status: Status) -> None:
    task = make_task(status=status)

    task.complete(now=NOW)

    assert (task.status, task.completed_at, task.updated_at) == (Status.DONE, NOW, NOW)


def test_reopen_moves_a_done_task_to_to_do_and_clears_completed_at() -> None:
    task = make_task(status=Status.DONE, completed_at=EARLIER)

    task.reopen(now=NOW)

    assert (task.status, task.completed_at, task.updated_at) == (Status.TO_DO, None, NOW)


@pytest.mark.parametrize(
    ("action", "status"),
    [
        ("start", Status.IN_PROGRESS),
        ("start", Status.DONE),
        ("complete", Status.DONE),
        ("reopen", Status.TO_DO),
        ("reopen", Status.IN_PROGRESS),
    ],
)
def test_any_other_transition_is_invalid_and_changes_nothing(action: str, status: Status) -> None:
    task = make_task(status=status, completed_at=EARLIER if status is Status.DONE else None)
    before = replace(task)

    with pytest.raises(errors.InvalidTransition) as error:
        getattr(task, action)(now=NOW)

    assert (error.value.action, error.value.status) == (action, status)
    assert task == before
