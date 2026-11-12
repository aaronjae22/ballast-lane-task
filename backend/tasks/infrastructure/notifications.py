"""Notifier adapters: the assignment email through Celery (spec section 7, ADR 0015)."""

import logging

from django.db import transaction

from tasks.infrastructure.jobs import send_assignment_email

logger = logging.getLogger(__name__)


class LoggingNotifier:
    """Logs each assignment once the transaction commits.

    The port says adapters act after the commit, and the Celery adapter will queue its email
    the same way, so a rolled-back assignment leaves no trace here either.
    """

    def task_assigned(self, *, task_id: int, assignee_id: int) -> None:
        transaction.on_commit(
            lambda: logger.info("Task %s was assigned to user %s.", task_id, assignee_id)
        )


class CeleryNotifier:
    """Queues the assignment email once the transaction commits.

    A rolled-back assignment queues nothing. The job takes ids and re-reads the task when it
    runs. robust=True: if the broker is down at commit time, Django logs the error and the
    request still succeeds, because the assignment is already saved (ADR 0015). That email is
    lost; the log shows it.
    """

    def task_assigned(self, *, task_id: int, assignee_id: int) -> None:
        # A named function, not functools.partial: Django's robust on_commit names the callback
        # by its __qualname__ when it logs a failure, and a partial has none.
        def queue_assignment_email() -> None:
            send_assignment_email.delay(task_id, assignee_id)

        transaction.on_commit(queue_assignment_email, robust=True)
