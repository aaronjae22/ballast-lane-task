"""Celery jobs: the assignment email (spec section 7, ADR 0015).

Jobs take ids, never objects, and load what they need when they run, which may be well after
the write that queued them. Their names are explicit, so a rename of this module doesn't strand
messages already in the queue. config/celery.py points the worker's discovery here.
"""

import logging
from smtplib import SMTPRecipientsRefused
from typing import Any

from celery import shared_task

from accounts.models import User
from tasks.infrastructure.emails import assignment_email
from tasks.selectors import visible_tasks

logger = logging.getLogger(__name__)

# Sending email retries on OSError: connection errors, timeouts and SMTPException (a subclass),
# with exponential backoff and jitter, up to 5 times over at most ~10 minutes a step. A refused
# address is permanent, so it isn't retried. Celery acks before running (its default), so a
# worker that dies mid-send loses that email rather than sending it twice.
EMAIL_RETRY: dict[str, Any] = {
    "autoretry_for": (OSError,),
    "dont_autoretry_for": (SMTPRecipientsRefused,),
    "max_retries": 5,
    "retry_backoff": True,
    "retry_backoff_max": 600,
    "retry_jitter": True,
}


@shared_task(name="tasks.send_assignment_email", **EMAIL_RETRY)
def send_assignment_email(task_id: int, assignee_id: int) -> None:
    """Email the assignee about the task, if it's still theirs.

    By the time this runs the task may be deleted or assigned to someone else, and the user may
    be deactivated or have no email address. Each case is logged and skipped, not retried:
    trying again wouldn't change the answer. The task is read through visible_tasks(user), as
    every read on a user's behalf is, and the email shows it as it is now.
    """
    user = User.objects.filter(pk=assignee_id, is_active=True).exclude(email="").first()
    if user is None:
        logger.info(
            "No assignment email for task %s: user %s is unknown, inactive or has no email "
            "address.",
            task_id,
            assignee_id,
        )
        return
    task = visible_tasks(user).filter(pk=task_id, assignee=user).first()
    if task is None:
        logger.info(
            "No assignment email for task %s: it was deleted or is no longer assigned to user %s.",
            task_id,
            assignee_id,
        )
        return
    assignment_email(task, user).send()
