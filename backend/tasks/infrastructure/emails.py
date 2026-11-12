"""Emails rendered from templates in tasks/templates/emails/ (spec section 7).

Rendering only: the Celery jobs in jobs.py decide who gets what, and when. Every email has a
plain-text body and an HTML alternative. The plain-text templates turn autoescaping off, so
a title with "&" or "<" reads as typed there and is escaped only in the HTML.
"""

from typing import Any

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from accounts.models import User
from tasks import models


def assignment_email(task: models.Task, assignee: User) -> EmailMultiAlternatives:
    """Tells the assignee about a task assigned to them, as the task is now."""
    return _email("emails/task_assigned", {"task": task, "assignee": assignee}, to=assignee.email)


def _email(template: str, context: dict[str, Any], *, to: str) -> EmailMultiAlternatives:
    """The subject, plain-text body and HTML alternative from <template>_subject.txt, .txt, .html.

    The subject is collapsed to one line: a title may contain a line break, and Django refuses
    a header with one. The sender is DEFAULT_FROM_EMAIL.
    """
    subject = " ".join(render_to_string(f"{template}_subject.txt", context).split())
    message = EmailMultiAlternatives(subject, render_to_string(f"{template}.txt", context), to=[to])
    message.attach_alternative(render_to_string(f"{template}.html", context), "text/html")
    return message
