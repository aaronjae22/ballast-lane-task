"""Celery jobs: the assignment email and the due-tomorrow reminder (spec section 7, ADR 0015).

Jobs take ids, never objects, and load what they need when they run, which may be well after
the write that queued them. Their names are explicit, so a rename of this module doesn't strand
messages already in the queue. config/celery.py points the worker's discovery here.
"""

import logging
from datetime import date, timedelta
from smtplib import SMTPRecipientsRefused
from typing import Any

from celery import shared_task

from accounts.models import User
from tasks.infrastructure.clock import DjangoClock
from tasks.infrastructure.emails import assignment_email, due_tomorrow_email
from tasks.selectors import due_on_for_assignee, reminder_recipients, visible_tasks

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
    user = _reachable_user(assignee_id)
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


@shared_task(name="tasks.send_due_tomorrow_reminders")
def send_due_tomorrow_reminders() -> None:
    """Beat's daily job: queue one digest per user with open tasks due tomorrow.

    "Tomorrow" is the Clock's today plus one, in TIME_ZONE (ADR 0012), computed once here and
    passed on as an ISO date. One job per user means a failed send retries one digest, not
    everyone's. This reads and never writes, outside any transaction, so it queues directly:
    on_commit is for jobs that a write causes (ADR 0015).
    """
    tomorrow = DjangoClock().today() + timedelta(days=1)
    for user_id in reminder_recipients(tomorrow).values_list("pk", flat=True):
        send_due_tomorrow_digest.delay(user_id, tomorrow.isoformat())


@shared_task(name="tasks.send_due_tomorrow_digest", **EMAIL_RETRY)
def send_due_tomorrow_digest(user_id: int, day: str) -> None:
    """Email the user their open tasks due on the day (an ISO date), if any are left.

    Between the fan-out and now, the tasks may have been completed or reassigned, and the user
    deactivated or left without an email address. Then nothing is sent, and it's logged.
    """
    due = date.fromisoformat(day)
    user = _reachable_user(user_id)
    if user is None:
        logger.info(
            "No due-tomorrow digest for user %s: unknown, inactive or no email address.", user_id
        )
        return
    tasks = list(due_on_for_assignee(user, due))
    if not tasks:
        logger.info("No due-tomorrow digest for user %s: no open tasks due %s.", user_id, day)
        return
    due_tomorrow_email(user, tasks, due).send()


def _reachable_user(user_id: int) -> User | None:
    """The user, if they exist, are active and have an email address to send to."""
    return User.objects.filter(pk=user_id, is_active=True).exclude(email="").first()
