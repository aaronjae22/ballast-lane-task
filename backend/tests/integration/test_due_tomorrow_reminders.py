"""The due-tomorrow reminder (spec section 7, ADR 0015).

Beat runs send_due_tomorrow_reminders daily. It finds the recipients and queues one digest per
user with the day as an ISO date, so a failed send retries one person's digest, not everyone's.
"Tomorrow" is the Clock's today plus one, in TIME_ZONE (ADR 0012). Time is fixed by patching
django.utils.timezone.now, as the Clock's own tests do. Jobs run in-process: no broker.
"""

from collections.abc import Callable
from datetime import UTC, date, datetime
from unittest import mock

import pytest
from django.core import mail
from pytest_django import Settings

from accounts.models import User
from config import celery_app
from tasks.domain.status import Status
from tasks.infrastructure import jobs
from tasks.infrastructure.jobs import send_due_tomorrow_digest, send_due_tomorrow_reminders
from tests.conftest import MakeUser, StoreTask
from tests.unit.builders import EARLIER

pytestmark = pytest.mark.django_db

THURSDAY = date(2026, 11, 12)
FRIDAY = date(2026, 11, 13)


class RecordingJob:
    """Stands in for send_due_tomorrow_digest: records each .delay() call's arguments."""

    def __init__(self) -> None:
        self.queued: list[tuple[object, ...]] = []

    def delay(self, *args: object) -> None:
        self.queued.append(args)


@pytest.fixture
def digest_job(monkeypatch: pytest.MonkeyPatch) -> RecordingJob:
    recording = RecordingJob()
    monkeypatch.setattr(jobs, "send_due_tomorrow_digest", recording)
    return recording


@pytest.fixture
def alice(make_user: MakeUser) -> User:
    return make_user("alice", email="alice@example.com", first_name="Alice", last_name="Johnson")


@pytest.fixture
def bob(make_user: MakeUser) -> User:
    return make_user("bob", email="bob@example.com", first_name="Bob", last_name="Smith")


@pytest.mark.parametrize(
    ("time_zone", "instant", "tomorrow"),
    [
        # 21:00 on Wednesday the 11th in Managua (UTC-6), though UTC is already on Thursday.
        ("America/Managua", datetime(2026, 11, 12, 3, 0, tzinfo=UTC), THURSDAY),
        # 10:00 on Thursday the 12th in Kiritimati (UTC+14), though UTC is still on Wednesday.
        ("Pacific/Kiritimati", datetime(2026, 11, 11, 20, 0, tzinfo=UTC), FRIDAY),
    ],
    ids=["behind-utc", "ahead-of-utc"],
)
def test_tomorrow_is_the_day_after_the_local_today(
    settings: Settings,
    digest_job: RecordingJob,
    alice: User,
    bob: User,
    store_task: StoreTask,
    time_zone: str,
    instant: datetime,
    tomorrow: date,
) -> None:
    settings.TIME_ZONE = time_zone
    store_task(bob, alice, due_date=THURSDAY)
    store_task(alice, bob, due_date=FRIDAY)
    recipient = alice if tomorrow == THURSDAY else bob

    with mock.patch("django.utils.timezone.now", return_value=instant):
        send_due_tomorrow_reminders.apply()

    assert digest_job.queued == [(recipient.pk, tomorrow.isoformat())]


def test_each_recipient_gets_one_digest_job_with_ids_and_an_iso_date(
    settings: Settings, digest_job: RecordingJob, alice: User, bob: User, store_task: StoreTask
) -> None:
    settings.TIME_ZONE = "UTC"
    store_task(bob, alice, due_date=THURSDAY)
    store_task(bob, alice, due_date=THURSDAY)
    store_task(alice, bob, due_date=THURSDAY)

    with mock.patch(
        "django.utils.timezone.now", return_value=datetime(2026, 11, 11, 8, 0, tzinfo=UTC)
    ):
        send_due_tomorrow_reminders.apply()

    assert digest_job.queued == [(alice.pk, "2026-11-12"), (bob.pk, "2026-11-12")]


def test_the_digest_lists_the_users_open_tasks_due_that_day(
    alice: User, bob: User, store_task: StoreTask
) -> None:
    store_task(bob, alice, title="Write the tests", due_date=THURSDAY)
    store_task(alice, alice, title="Review & merge", due_date=THURSDAY, status=Status.IN_PROGRESS)
    store_task(
        bob,
        alice,
        title="Done already",
        due_date=THURSDAY,
        status=Status.DONE,
        completed_at=EARLIER,
    )
    store_task(bob, alice, title="Due on Friday", due_date=FRIDAY)

    result = send_due_tomorrow_digest.apply(args=(alice.pk, "2026-11-12"))

    assert result.successful()
    [message] = mail.outbox
    assert message.to == ["alice@example.com"]
    assert message.subject == "Due tomorrow: 2 tasks"
    assert "Thursday, 12 November 2026" in message.body
    review, write = message.body.index("Review & merge"), message.body.index("Write the tests")
    assert review < write  # by title
    assert "Bob Smith" in message.body
    assert "In progress" in message.body
    assert "Done already" not in message.body
    assert "Due on Friday" not in message.body
    assert isinstance(message, mail.EmailMultiAlternatives)
    [(html, mimetype)] = message.alternatives
    assert mimetype == "text/html"
    assert "Review &amp; merge" in html
    assert "Write the tests" in html


def test_a_digest_of_one_task_names_it_in_the_subject(
    alice: User, bob: User, store_task: StoreTask
) -> None:
    store_task(bob, alice, title="Write the tests", due_date=THURSDAY)

    send_due_tomorrow_digest.apply(args=(alice.pk, "2026-11-12"))

    [message] = mail.outbox
    assert message.subject == "Due tomorrow: Write the tests"


def complete_everything(alice: User) -> None:
    alice.assigned_tasks.update(status=Status.DONE.value, completed_at=EARLIER)


def deactivate(alice: User) -> None:
    User.objects.filter(pk=alice.pk).update(is_active=False)


def remove_email(alice: User) -> None:
    User.objects.filter(pk=alice.pk).update(email="")


@pytest.mark.parametrize(
    "change",
    [complete_everything, deactivate, remove_email],
    ids=["all-done-since", "user-inactive", "no-email-address"],
)
def test_no_digest_when_nothing_is_left_to_remind_about(
    alice: User, bob: User, store_task: StoreTask, change: Callable[[User], None]
) -> None:
    """Between the fan-out and the send, the tasks or the user may have changed."""
    store_task(bob, alice, due_date=THURSDAY)
    change(alice)

    result = send_due_tomorrow_digest.apply(args=(alice.pk, "2026-11-12"))

    assert result.successful()
    assert mail.outbox == []


def test_a_digest_retries_a_failing_send_like_the_assignment_email() -> None:
    assert send_due_tomorrow_digest.autoretry_for == (OSError,)
    assert send_due_tomorrow_digest.max_retries == 5
    assert send_due_tomorrow_digest.name == "tasks.send_due_tomorrow_digest"


def test_from_beat_to_the_outbox(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
    alice: User,
    bob: User,
    store_task: StoreTask,
) -> None:
    """The whole chain in-process: eager for this test only, never globally (ADR 0015)."""
    monkeypatch.setattr(celery_app.conf, "task_always_eager", True)
    settings.TIME_ZONE = "UTC"
    store_task(bob, alice, due_date=THURSDAY)
    store_task(alice, bob, due_date=THURSDAY)
    store_task(alice, None, due_date=THURSDAY)

    with mock.patch(
        "django.utils.timezone.now", return_value=datetime(2026, 11, 11, 8, 0, tzinfo=UTC)
    ):
        send_due_tomorrow_reminders.apply()

    assert sorted(message.to[0] for message in mail.outbox) == [
        "alice@example.com",
        "bob@example.com",
    ]
