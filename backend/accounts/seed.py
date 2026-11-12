"""Demo data for a fresh stack: python manage.py seed_demo (spec section 7, ADR 0015).

An admin, three users and 25 tasks across every status and due-date bucket, so every filter
shows results. Due dates are relative to the day it runs. It's idempotent:
- Users are found by username, and an existing one is never changed.
- Tasks are created only while no demo user owns any, so edits and deletions survive reruns.

CreateTask rejects past due dates, so the seed builds domain Tasks and stores them through the
repository (ADR 0013). Each task is created as if on a past day, then started or completed, so
the domain still strips titles, allows only valid transitions and sets completed_at. It sends
no email.
"""

import os
from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction

from accounts.models import User
from tasks import models
from tasks.application.ports import Clock
from tasks.domain.status import Status
from tasks.domain.task import Task
from tasks.infrastructure.repositories import DjangoTaskRepository

# For local use only, and documented in the README. A deployment anyone else can reach sets
# SEED_DEMO_PASSWORD: the seed creates a superuser (ADR 0015).
DEFAULT_DEMO_PASSWORD = "demo-password"

# username -> (first name, last name, admin). Emails are <username>@example.com.
DEMO_USERS = {
    "admin": ("Ada", "Admin", True),
    "alice": ("Alice", "Johnson", False),
    "bob": ("Bob", "Smith", False),
    "carol": ("Carol", "Diaz", False),
}

TO_DO, IN_PROGRESS, DONE = Status.TO_DO, Status.IN_PROGRESS, Status.DONE
# Every task is created this many days before the seed runs, before its earliest due date.
CREATED_DAYS_AGO = 10

# (title, owner, assignee, status, due in days from today or None)
DEMO_TASKS: tuple[tuple[str, str, str | None, Status, int | None], ...] = (
    # Overdue: due in the past and not done.
    ("Send the October invoice", "alice", "bob", TO_DO, -7),
    ("Fix the login redirect bug", "bob", "carol", IN_PROGRESS, -2),
    ("Renew the TLS certificate", "admin", "alice", TO_DO, -2),
    ("Archive last quarter's reports", "carol", "carol", TO_DO, -7),
    ("Book the team offsite venue", "carol", None, IN_PROGRESS, -2),
    # Due in the past but done: not overdue.
    ("Publish the release notes", "alice", "alice", DONE, -5),
    ("Answer the security questionnaire", "admin", "bob", DONE, -3),
    ("Collect the conference receipts", "bob", "carol", DONE, -4),
    # Due today.
    ("Update the onboarding checklist", "bob", "alice", TO_DO, 0),
    ("Review the pull request backlog", "alice", "carol", IN_PROGRESS, 0),
    ("Order the new laptops", "admin", None, TO_DO, 0),
    ("Prepare the sprint demo", "carol", "bob", DONE, 0),
    # Due tomorrow: each of alice, bob and carol gets a reminder.
    ("Draft the Q1 roadmap", "bob", "alice", TO_DO, 1),
    ("Run the database backup drill", "admin", "bob", IN_PROGRESS, 1),
    ("Write the API changelog", "alice", "carol", TO_DO, 1),
    ("Clean up the staging servers", "bob", None, TO_DO, 1),
    # Due next week.
    ("Plan the accessibility audit", "alice", "bob", TO_DO, 5),
    ("Migrate the CI runners", "bob", "bob", IN_PROGRESS, 6),
    ("Interview the frontend candidates", "carol", "alice", TO_DO, 7),
    ("Refresh the style guide", "admin", "carol", DONE, 7),
    ("Set up the status page", "alice", None, TO_DO, 6),
    # No due date.
    ("Read the incident postmortem", "bob", "carol", TO_DO, None),
    ("Tidy the shared drive", "carol", None, TO_DO, None),
    ("Learn the new deploy tooling", "alice", "alice", IN_PROGRESS, None),
    ("Write the team handbook", "admin", "alice", DONE, None),
)


@dataclass(frozen=True)
class SeedResult:
    users_created: int
    tasks_created: int


def demo_password() -> str:
    """SEED_DEMO_PASSWORD, or the local default. Read when the seed runs."""
    return os.environ.get("SEED_DEMO_PASSWORD") or DEFAULT_DEMO_PASSWORD


@transaction.atomic
def seed_demo(clock: Clock) -> SeedResult:
    """Create whatever demo data is missing, in one transaction. Changes nothing that exists."""
    users, users_created = _users()
    if models.Task.objects.filter(owner__in=users.values()).exists():
        return SeedResult(users_created, 0)
    repository = DjangoTaskRepository()
    for spec in DEMO_TASKS:
        repository.add(_task(*spec, users=users, clock=clock))
    return SeedResult(users_created, len(DEMO_TASKS))


def _users() -> tuple[dict[str, User], int]:
    password = demo_password()
    users, created_count = {}, 0
    for username, (first_name, last_name, is_admin) in DEMO_USERS.items():
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                "email": f"{username}@example.com",
                "is_staff": is_admin,
                "is_superuser": is_admin,
            },
        )
        if created:
            # set_password, not create_user's validators: the password is the deployer's choice.
            user.set_password(password)
            user.save(update_fields=["password"])
            created_count += 1
        users[username] = user
    return users, created_count


def _task(
    title: str,
    owner: str,
    assignee: str | None,
    status: Status,
    due_in: int | None,
    *,
    users: dict[str, User],
    clock: Clock,
) -> Task:
    """The task as if created CREATED_DAYS_AGO, then moved to its status through the domain."""
    today, now = clock.today(), clock.now()
    created_at = now - timedelta(days=CREATED_DAYS_AGO)
    assignee_user = users[assignee] if assignee else None
    task = Task.create(
        title=title,
        due_date=None if due_in is None else today + timedelta(days=due_in),
        owner_id=users[owner].pk,
        assignee_id=assignee_user.pk if assignee_user else None,
        assignee_is_active=bool(assignee_user and assignee_user.is_active),
        today=today - timedelta(days=CREATED_DAYS_AGO),
        now=created_at,
    )
    if status is IN_PROGRESS:
        task.start(now=created_at + timedelta(days=2))
    elif status is DONE:
        task.complete(now=now - timedelta(days=1))
    return task
