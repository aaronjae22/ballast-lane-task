"""LoggingNotifier: the Notifier until iteration 4 brings the Celery adapter (ADR 0014).

Like that adapter, it acts only once the transaction commits, so a rolled-back assignment
leaves no trace (spec section 7).
"""

import logging
from collections.abc import Callable
from contextlib import AbstractContextManager

import pytest
from django.db import transaction

from tasks.infrastructure.notifications import LoggingNotifier

pytestmark = pytest.mark.django_db

LOGGER = "tasks.infrastructure.notifications"

type CaptureOnCommit = Callable[..., AbstractContextManager[list[Callable[[], object]]]]


def test_an_assignment_is_logged_once_the_transaction_commits(
    caplog: pytest.LogCaptureFixture, django_capture_on_commit_callbacks: CaptureOnCommit
) -> None:
    caplog.set_level(logging.INFO, logger=LOGGER)

    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        LoggingNotifier().task_assigned(task_id=7, assignee_id=3)
        assert caplog.messages == []

    assert len(callbacks) == 1
    assert caplog.messages == ["Task 7 was assigned to user 3."]


def test_a_rolled_back_assignment_is_never_logged(
    caplog: pytest.LogCaptureFixture, django_capture_on_commit_callbacks: CaptureOnCommit
) -> None:
    caplog.set_level(logging.INFO, logger=LOGGER)

    with (
        django_capture_on_commit_callbacks(execute=True) as callbacks,
        pytest.raises(RuntimeError),
        transaction.atomic(),
    ):
        LoggingNotifier().task_assigned(task_id=7, assignee_id=3)
        raise RuntimeError("the write failed after the assignment")

    assert callbacks == []
    assert caplog.messages == []
