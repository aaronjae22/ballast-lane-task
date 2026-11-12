"""LoggingNotifier: the Notifier until iteration 4 brings the Celery adapter (ADR 0014).

Like that adapter, it acts only once the transaction commits, so a rolled-back assignment
leaves no trace (spec section 7).
"""

import logging
import os
import subprocess
import sys
from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path

import pytest
from django.db import transaction

from tasks.infrastructure.notifications import LoggingNotifier

pytestmark = pytest.mark.django_db

LOGGER = "tasks.infrastructure.notifications"
BACKEND_DIR = Path(__file__).resolve().parents[2]

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


@pytest.mark.parametrize("settings_module", ["config.settings", "config.test_settings"])
def test_the_message_reaches_stderr_under_the_projects_own_logging(settings_module: str) -> None:
    """No caplog here: it would lower the level itself and hide a missing LOGGING config.

    Outside a transaction, on_commit runs the callback at once, so no database is needed.
    """
    script = (
        "import django; django.setup()\n"
        "from tasks.infrastructure.notifications import LoggingNotifier\n"
        "LoggingNotifier().task_assigned(task_id=7, assignee_id=3)\n"
    )
    env = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": settings_module,
        "DJANGO_SECRET_KEY": "test-only-not-a-secret",
    }

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Task 7 was assigned to user 3." in result.stderr
