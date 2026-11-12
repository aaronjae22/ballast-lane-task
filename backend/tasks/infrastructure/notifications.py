"""A Notifier that logs, until iteration 4 brings the Celery adapter (ADR 0014)."""

import logging

from django.db import transaction

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
