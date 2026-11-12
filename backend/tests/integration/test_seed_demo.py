"""seed_demo: demo users and tasks for a fresh stack (spec section 7, ADR 0015).

The seed builds domain Tasks and stores them through the repository, because CreateTask
rejects the past due dates overdue tasks need (ADR 0013). The database checks no domain rule,
so these tests check the rows it stores.
"""

from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.test import RequestFactory

from accounts.models import User
from accounts.seed import DEFAULT_DEMO_PASSWORD, SeedResult, seed_demo
from tasks import models
from tasks.api.filters import TaskFilter
from tasks.domain.status import Status
from tasks.domain.task import TITLE_MAX_LENGTH
from tasks.selectors import overdue, reminder_recipients, visible_tasks
from tests.conftest import MakeUser
from tests.unit.builders import NOW, TODAY, TOMORROW
from tests.unit.fakes import FixedClock

pytestmark = pytest.mark.django_db

CLOCK = FixedClock(now=NOW, today=TODAY)
USERNAMES = {"admin", "alice", "bob", "carol"}


def demo_users() -> dict[str, User]:
    return {user.username: user for user in User.objects.filter(username__in=USERNAMES)}


def test_it_creates_an_admin_and_three_users_who_can_log_in() -> None:
    assert seed_demo(CLOCK).users_created == 4

    users = demo_users()
    assert set(users) == USERNAMES
    assert users["admin"].is_admin and users["admin"].is_superuser
    for name in ("alice", "bob", "carol"):
        assert not users[name].is_staff and not users[name].is_superuser
    for user in users.values():
        assert user.is_active
        assert user.email == f"{user.username}@example.com"
        assert user.get_full_name()
        assert user.check_password(DEFAULT_DEMO_PASSWORD)


def test_a_deployment_sets_its_own_password(monkeypatch: pytest.MonkeyPatch) -> None:
    """The default is published in the README, and the seed creates a superuser."""
    monkeypatch.setenv("SEED_DEMO_PASSWORD", "this-deployments-own-password")

    seed_demo(CLOCK)

    for user in demo_users().values():
        assert user.check_password("this-deployments-own-password")
        assert not user.check_password(DEFAULT_DEMO_PASSWORD)


def test_tasks_cover_every_status_and_due_date_bucket() -> None:
    seed_demo(CLOCK)
    tasks = models.Task.objects.all()

    assert 20 <= tasks.count() <= 30
    for status in Status:
        assert tasks.filter(status=status.value).exists(), status
    buckets = {
        "overdue": tasks.filter(overdue(TODAY)),
        "today": tasks.filter(due_date=TODAY),
        "tomorrow": tasks.filter(due_date=TOMORROW),
        "next week": tasks.filter(due_date__range=(TODAY + timedelta(2), TODAY + timedelta(7))),
        "none": tasks.filter(due_date__isnull=True),
        "past but done": tasks.filter(due_date__lt=TODAY, status=Status.DONE.value),
        "unassigned": tasks.filter(assignee__isnull=True),
    }
    for name, bucket in buckets.items():
        assert bucket.exists(), name


def test_each_user_has_a_reminder_due_tomorrow() -> None:
    seed_demo(CLOCK)

    recipients = {user.username for user in reminder_recipients(TOMORROW)}
    assert recipients >= {"alice", "bob", "carol"}


@pytest.mark.parametrize(
    "params",
    [
        *({"status": status.value} for status in Status),
        {"overdue": "true"},
        {"overdue": "false"},
        {"due_after": TOMORROW.isoformat()},
        {"due_before": TODAY.isoformat()},
        {"search": "the"},
        {"assignee": "me"},
    ],
    ids=lambda params: "&".join(f"{key}={value}" for key, value in params.items()),
)
@pytest.mark.parametrize("username", ["alice", "bob", "carol"])
def test_every_filter_shows_results_for_every_user(username: str, params: dict[str, str]) -> None:
    seed_demo(CLOCK)
    user = demo_users()[username]
    request = RequestFactory().get("/api/tasks/", params)
    request.user = user

    filterset = TaskFilter(request.GET, visible_tasks(user), request=request, clock=CLOCK)

    assert filterset.is_valid(), filterset.errors
    assert filterset.qs.exists()


def test_every_row_keeps_the_domains_rules() -> None:
    """The rules the database doesn't check (ADR 0013)."""
    seed_demo(CLOCK)
    users = demo_users()

    for row in models.Task.objects.select_related("owner", "assignee"):
        assert row.title == row.title.strip()
        assert 1 <= len(row.title) <= TITLE_MAX_LENGTH
        status = Status(row.status)
        assert (row.completed_at is not None) is (status is Status.DONE), row.title
        assert row.created_at <= row.updated_at <= NOW
        assert row.completed_at is None or row.completed_at <= row.updated_at
        assert row.owner.username in users
        assert row.assignee is None or row.assignee.is_active


def test_a_second_run_creates_nothing() -> None:
    first = seed_demo(CLOCK)

    second = seed_demo(CLOCK)

    assert first == SeedResult(users_created=4, tasks_created=models.Task.objects.count())
    assert second == SeedResult(users_created=0, tasks_created=0)
    assert User.objects.count() == 4


def test_edits_and_deletions_survive_a_rerun() -> None:
    """A restart re-runs the seed: an edited title must not come back as a second task."""
    seed_demo(CLOCK)
    first, second = models.Task.objects.order_by("pk")[:2]
    original_title = first.title
    models.Task.objects.filter(pk=first.pk).update(title="Renamed in the demo")
    second.delete()
    count = models.Task.objects.count()

    seed_demo(CLOCK)

    assert models.Task.objects.count() == count
    assert not models.Task.objects.filter(title=original_title).exists()


def test_an_existing_user_is_never_changed(make_user: MakeUser) -> None:
    """So the seed can't reset a real account's password."""
    make_user("alice", password="alices-own-password", first_name="Real")

    result = seed_demo(CLOCK)

    alice = demo_users()["alice"]
    assert result.users_created == 3
    assert alice.check_password("alices-own-password")
    assert alice.first_name == "Real"


def test_the_command_reports_what_it_created() -> None:
    out = StringIO()

    call_command("seed_demo", stdout=out)
    call_command("seed_demo", stdout=out)

    count = models.Task.objects.count()
    assert out.getvalue().splitlines() == [
        f"Created 4 users and {count} tasks.",
        "Created 0 users and 0 tasks.",
    ]
