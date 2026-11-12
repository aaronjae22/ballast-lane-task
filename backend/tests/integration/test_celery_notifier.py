"""CeleryNotifier: the Notifier that queues the assignment email (spec section 7, ADR 0015).

It queues only once the transaction commits, so a rolled-back assignment sends nothing. The
job itself is replaced by a recorder: no broker is needed, and the job's own tests cover
what it sends.
"""

import logging
from collections.abc import Callable
from contextlib import AbstractContextManager

import pytest
from django.db import transaction
from kombu.exceptions import OperationalError

from tasks.infrastructure import notifications
from tasks.infrastructure.notifications import CeleryNotifier

type CaptureOnCommit = Callable[..., AbstractContextManager[list[Callable[[], object]]]]


class RecordingJob:
    """Stands in for send_assignment_email: records each .delay() call's arguments."""

    def __init__(self, error: Exception | None = None) -> None:
        self.queued: list[tuple[object, ...]] = []
        self._error = error

    def delay(self, *args: object) -> None:
        if self._error is not None:
            raise self._error
        self.queued.append(args)


@pytest.fixture
def job(monkeypatch: pytest.MonkeyPatch) -> RecordingJob:
    recording = RecordingJob()
    monkeypatch.setattr(notifications, "send_assignment_email", recording)
    return recording


@pytest.mark.django_db
def test_one_job_is_queued_once_the_transaction_commits(
    job: RecordingJob, django_capture_on_commit_callbacks: CaptureOnCommit
) -> None:
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        CeleryNotifier().task_assigned(task_id=7, assignee_id=3)
        assert job.queued == []

    assert len(callbacks) == 1
    assert job.queued == [(7, 3)]


@pytest.mark.django_db
def test_a_rolled_back_assignment_queues_nothing(
    job: RecordingJob, django_capture_on_commit_callbacks: CaptureOnCommit
) -> None:
    with (
        django_capture_on_commit_callbacks(execute=True) as callbacks,
        pytest.raises(RuntimeError),
        transaction.atomic(),
    ):
        CeleryNotifier().task_assigned(task_id=7, assignee_id=3)
        raise RuntimeError("the write failed after the assignment")

    assert callbacks == []
    assert job.queued == []


@pytest.mark.django_db(transaction=True)
def test_a_broker_outage_at_commit_is_logged_and_does_not_fail_the_write(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """The write already committed: a 500 would tell the client it failed when it didn't.

    transaction=True, so a real commit runs the callback the way production does.
    """
    monkeypatch.setattr(
        notifications, "send_assignment_email", RecordingJob(OperationalError("Redis is down"))
    )

    with transaction.atomic():
        CeleryNotifier().task_assigned(task_id=7, assignee_id=3)

    [record] = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert "on_commit" in record.getMessage()
    assert "Redis is down" in record.getMessage()
