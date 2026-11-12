"""tasks/api/wiring.py: the composition root (spec section 4, ADRs 0013 and 0014).

It builds each write use case with the real adapters and runs it inside a transaction, and
it's the one place a user becomes the domain's Actor. The transaction tests use
transaction=True, because a plain django_db test already runs inside one and would hide a
missing transaction.atomic().
"""

from collections.abc import Callable
from typing import Any

import pytest
from django.db import connection

from accounts.models import User
from tasks import models
from tasks.api import wiring
from tasks.domain.actor import Actor
from tasks.domain.status import Status
from tasks.infrastructure.notifications import LoggingNotifier
from tests.conftest import StoreTask
from tests.unit.builders import EARLIER
from tests.unit.fakes import RecordingNotifier


@pytest.fixture
def notifier(monkeypatch: pytest.MonkeyPatch) -> RecordingNotifier:
    """Stands in for whatever wiring.notifier() returns, now or after iteration 4."""
    recording = RecordingNotifier()
    monkeypatch.setattr(wiring, "notifier", lambda: recording)
    return recording


class AtomicSpy:
    """A notifier that records whether it was called inside a transaction."""

    def __init__(self) -> None:
        self.in_atomic_block: list[bool] = []

    def task_assigned(self, *, task_id: int, assignee_id: int) -> None:
        self.in_atomic_block.append(connection.in_atomic_block)


class FailingNotifier:
    def task_assigned(self, *, task_id: int, assignee_id: int) -> None:
        raise RuntimeError("the notifier failed after save()")


@pytest.mark.parametrize(
    ("fields", "expected"),
    [
        ({"pk": 5}, Actor(id=5, is_admin=False)),
        ({"pk": 6, "is_staff": True}, Actor(id=6, is_admin=True)),
        # A superuser without is_staff isn't an admin (ADR 0013).
        ({"pk": 7, "is_superuser": True}, Actor(id=7, is_admin=False)),
    ],
    ids=["user", "staff", "superuser-without-staff"],
)
def test_actor_for_maps_the_id_and_the_admin_flag(
    fields: dict[str, object], expected: Actor
) -> None:
    assert wiring.actor_for(User(**fields)) == expected


type Write = Callable[[dict[str, User], int], Any]

# Each write that loads a task: (status the task starts in, how to run it).
LOADING_WRITES: dict[str, tuple[Status, Write]] = {
    "update": (Status.TO_DO, lambda u, i: wiring.update_task(u["owner"], i, title="New title")),
    "assign": (Status.TO_DO, lambda u, i: wiring.assign_task(u["owner"], i, u["other"].pk)),
    "start": (Status.TO_DO, lambda u, i: wiring.start_task(u["owner"], i)),
    "complete": (Status.TO_DO, lambda u, i: wiring.complete_task(u["owner"], i)),
    "reopen": (Status.DONE, lambda u, i: wiring.reopen_task(u["owner"], i)),
    "delete": (Status.TO_DO, lambda u, i: wiring.delete_task(u["owner"], i)),
}


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(("status", "write"), LOADING_WRITES.values(), ids=list(LOADING_WRITES))
def test_every_write_that_loads_a_task_runs_inside_a_transaction(
    owner: User,
    other_user: User,
    store_task: StoreTask,
    notifier: RecordingNotifier,
    status: Status,
    write: Write,
) -> None:
    """Outside one, the repository's get() raises TransactionManagementError (ADR 0013)."""
    completed_at = EARLIER if status is Status.DONE else None
    task = store_task(owner, status=status, completed_at=completed_at)
    assert task.id is not None

    write({"owner": owner, "other": other_user}, task.id)


@pytest.mark.django_db(transaction=True)
def test_create_runs_inside_a_transaction(
    monkeypatch: pytest.MonkeyPatch, owner: User, assignee: User
) -> None:
    spy = AtomicSpy()
    monkeypatch.setattr(wiring, "notifier", lambda: spy)

    wiring.create_task(owner, title="Write the spec", assignee_id=assignee.pk)

    assert spy.in_atomic_block == [True]


@pytest.mark.django_db(transaction=True)
def test_a_failure_after_saving_rolls_the_write_back(
    monkeypatch: pytest.MonkeyPatch, owner: User, assignee: User, store_task: StoreTask
) -> None:
    task = store_task(owner)
    assert task.id is not None
    monkeypatch.setattr(wiring, "notifier", lambda: FailingNotifier())

    with pytest.raises(RuntimeError):
        wiring.assign_task(owner, task.id, assignee.pk)

    assert models.Task.objects.get(pk=task.id).assignee_id is None


@pytest.mark.django_db
def test_create_stores_the_task_with_the_real_adapters(
    owner: User, assignee: User, notifier: RecordingNotifier
) -> None:
    task = wiring.create_task(owner, title="  Write the spec  ", assignee_id=assignee.pk)

    row = models.Task.objects.get(pk=task.id)
    assert (row.title, row.owner_id, row.assignee_id) == ("Write the spec", owner.pk, assignee.pk)
    assert notifier.assignments == [(task.id, assignee.pk)]


@pytest.mark.django_db
def test_the_admin_flag_reaches_the_use_cases(
    owner: User, admin: User, store_task: StoreTask
) -> None:
    """An admin may edit a task they neither own nor are assigned to (spec section 3)."""
    task = store_task(owner)
    assert task.id is not None

    wiring.update_task(admin, task.id, title="Edited by an admin")

    assert models.Task.objects.get(pk=task.id).title == "Edited by an admin"


def test_the_wiring_uses_the_logging_notifier_until_iteration_4() -> None:
    assert isinstance(wiring.notifier(), LoggingNotifier)
