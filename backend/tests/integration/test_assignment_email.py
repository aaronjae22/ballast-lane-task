"""The assignment email job (spec section 7, ADR 0015).

It runs after the assignment committed, maybe much later, so it re-reads the task and the
assignee and sends only if the assignment still holds. Jobs run in-process through .apply(),
retries included, and mail goes to Django's in-memory outbox: no broker, no SMTP server.
"""

import logging
import os
import smtplib
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import ClassVar

import pytest
from django.conf import settings
from django.core import mail
from django.core.mail import EmailMessage
from django.core.mail.backends.base import BaseEmailBackend
from pytest_django import Settings

from accounts.models import User
from tasks import models
from tasks.infrastructure.jobs import send_assignment_email
from tests.conftest import MakeUser, StoreTask
from tests.unit.builders import TOMORROW

pytestmark = pytest.mark.django_db

BACKEND_DIR = Path(__file__).resolve().parents[2]
LOGGER = "tasks.infrastructure.jobs"


DISCONNECTED = smtplib.SMTPServerDisconnected("Connection unexpectedly closed")


class FailingBackend(BaseEmailBackend):
    """An email backend whose every send raises `error`, counting the attempts."""

    error: ClassVar[Exception] = DISCONNECTED
    attempts: ClassVar[int] = 0

    def send_messages(self, email_messages: list[EmailMessage]) -> int:
        type(self).attempts += 1
        raise type(self).error


@pytest.fixture
def failing_backend(settings: Settings) -> type[FailingBackend]:
    settings.EMAIL_BACKEND = f"{__name__}.FailingBackend"
    FailingBackend.error, FailingBackend.attempts = DISCONNECTED, 0
    return FailingBackend


@pytest.fixture
def alice(make_user: MakeUser) -> User:
    return make_user("alice", email="alice@example.com", first_name="Alice", last_name="Johnson")


@pytest.fixture
def bob(make_user: MakeUser) -> User:
    return make_user("bob", email="bob@example.com", first_name="Bob", last_name="Smith")


def html_of(message: mail.EmailMessage) -> str:
    assert isinstance(message, mail.EmailMultiAlternatives)
    [(content, mimetype)] = message.alternatives
    assert mimetype == "text/html"
    return str(content)


def test_the_assignee_gets_an_email_about_the_task(
    alice: User, bob: User, store_task: StoreTask
) -> None:
    task = store_task(bob, alice, title="Write the spec", due_date=TOMORROW)

    result = send_assignment_email.apply(args=(task.id, alice.pk))

    assert result.successful()
    [message] = mail.outbox
    assert message.to == ["alice@example.com"]
    assert message.from_email == settings.DEFAULT_FROM_EMAIL
    assert message.subject == "You've been assigned: Write the spec"
    for body in (message.body, html_of(message)):
        assert "Alice Johnson" in body
        assert "Write the spec" in body
        assert "Thursday, 12 November 2026" in body
        assert "Bob Smith" in body  # the owner
        assert "To do" in body


def test_a_task_without_a_due_date_says_so(alice: User, bob: User, store_task: StoreTask) -> None:
    task = store_task(bob, alice, due_date=None)

    send_assignment_email.apply(args=(task.id, alice.pk))

    [message] = mail.outbox
    assert "No due date" in message.body
    assert "No due date" in html_of(message)


def test_the_title_is_escaped_in_html_and_left_as_it_is_in_plain_text(
    alice: User, bob: User, store_task: StoreTask
) -> None:
    task = store_task(bob, alice, title='Fix <b>bold</b> & "quotes"')

    send_assignment_email.apply(args=(task.id, alice.pk))

    [message] = mail.outbox
    assert message.subject == 'You\'ve been assigned: Fix <b>bold</b> & "quotes"'
    assert 'Fix <b>bold</b> & "quotes"' in message.body
    assert "Fix &lt;b&gt;bold&lt;/b&gt; &amp; &quot;quotes&quot;" in html_of(message)
    assert "<b>bold</b>" not in html_of(message)


def test_a_title_with_a_line_break_still_makes_a_one_line_subject(
    alice: User, bob: User, store_task: StoreTask
) -> None:
    """Django refuses a header with a newline, and the domain allows one inside a title."""
    task = store_task(bob, alice, title="First line\nsecond  line")

    send_assignment_email.apply(args=(task.id, alice.pk))

    [message] = mail.outbox
    assert message.subject == "You've been assigned: First line second line"


type Change = Callable[[models.Task, User, User], None]


def delete_task(task: models.Task, alice: User, bob: User) -> None:
    task.delete()


def reassign_to_bob(task: models.Task, alice: User, bob: User) -> None:
    models.Task.objects.filter(pk=task.pk).update(assignee=bob)


def unassign(task: models.Task, alice: User, bob: User) -> None:
    models.Task.objects.filter(pk=task.pk).update(assignee=None)


def deactivate_alice(task: models.Task, alice: User, bob: User) -> None:
    User.objects.filter(pk=alice.pk).update(is_active=False)


def remove_alices_email(task: models.Task, alice: User, bob: User) -> None:
    User.objects.filter(pk=alice.pk).update(email="")


@pytest.mark.parametrize(
    "change",
    [delete_task, reassign_to_bob, unassign, deactivate_alice, remove_alices_email],
    ids=["task-deleted", "reassigned", "unassigned", "assignee-inactive", "no-email-address"],
)
def test_nothing_is_sent_when_the_assignment_no_longer_holds(
    caplog: pytest.LogCaptureFixture,
    alice: User,
    bob: User,
    store_task: StoreTask,
    change: Change,
) -> None:
    """Skipped, logged and not retried: trying again wouldn't change the answer."""
    caplog.set_level(logging.INFO, logger=LOGGER)
    task = store_task(bob, alice)
    change(models.Task.objects.get(pk=task.id), alice, bob)

    result = send_assignment_email.apply(args=(task.id, alice.pk))

    assert result.successful()
    assert mail.outbox == []
    [record] = [r for r in caplog.records if r.name == LOGGER]
    assert record.levelno == logging.INFO
    assert f"task {task.id}" in record.getMessage()


def test_an_unknown_assignee_gets_nothing(alice: User, bob: User, store_task: StoreTask) -> None:
    task = store_task(bob, alice)

    result = send_assignment_email.apply(args=(task.id, alice.pk + 1000))

    assert result.successful()
    assert mail.outbox == []


def test_a_failing_send_is_retried_five_times_then_gives_up(
    alice: User, bob: User, store_task: StoreTask, failing_backend: type[FailingBackend]
) -> None:
    task = store_task(bob, alice)

    result = send_assignment_email.apply(args=(task.id, alice.pk))

    assert failing_backend.attempts == 1 + 5
    assert result.failed()
    assert isinstance(result.result, smtplib.SMTPServerDisconnected)


def test_a_refused_address_is_not_retried(
    alice: User, bob: User, store_task: StoreTask, failing_backend: type[FailingBackend]
) -> None:
    """A permanent error: the same address would be refused again."""
    failing_backend.error = smtplib.SMTPRecipientsRefused({"alice@example.com": (550, b"No")})
    task = store_task(bob, alice)

    result = send_assignment_email.apply(args=(task.id, alice.pk))

    assert failing_backend.attempts == 1
    assert result.failed()


def test_the_worker_discovers_the_job_under_its_name() -> None:
    """The worker never imports the wiring, so the Celery app must find the job module itself.

    A subprocess, because this test module already imports the job.
    """
    script = (
        "import django; django.setup()\n"
        "from config import celery_app\n"
        "celery_app.loader.import_default_modules()\n"
        "print('tasks.send_assignment_email' in celery_app.tasks)\n"
    )
    env = {**os.environ, "DJANGO_SETTINGS_MODULE": "config.test_settings"}

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "True"
    assert send_assignment_email.name == "tasks.send_assignment_email"
