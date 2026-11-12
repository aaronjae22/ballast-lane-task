"""The reads behind the due-tomorrow reminder (spec section 7, ADR 0015).

reminder_recipients(day) is a system read across users, made for no one in particular, so it
doesn't go through visible_tasks. due_on_for_assignee(user, day) reads on one user's behalf,
so it does.
"""

from datetime import date

import pytest
from pytest_django import DjangoAssertNumQueries

from accounts.models import User
from tasks.domain.status import Status
from tasks.selectors import due_on_for_assignee, reminder_recipients, visible_tasks
from tests.conftest import MakeUser, StoreTask
from tests.unit.builders import EARLIER, TODAY, TOMORROW

pytestmark = pytest.mark.django_db

DAY = TOMORROW


@pytest.fixture
def alice(make_user: MakeUser) -> User:
    return make_user("alice", email="alice@example.com")


@pytest.fixture
def bob(make_user: MakeUser) -> User:
    return make_user("bob", email="bob@example.com")


def recipients(day: date = DAY) -> list[int]:
    return list(reminder_recipients(day).values_list("pk", flat=True))


@pytest.mark.parametrize("status", [Status.TO_DO, Status.IN_PROGRESS])
def test_an_assignee_with_an_open_task_due_that_day_gets_a_reminder(
    alice: User, bob: User, store_task: StoreTask, status: Status
) -> None:
    store_task(bob, alice, due_date=DAY, status=status)

    assert recipients() == [alice.pk]


def test_a_self_assigned_task_counts(alice: User, store_task: StoreTask) -> None:
    """The "someone else" rule is about assignment emails, not due dates."""
    store_task(alice, alice, due_date=DAY)

    assert recipients() == [alice.pk]


def test_done_tasks_other_days_and_unassigned_tasks_send_nothing(
    alice: User, bob: User, store_task: StoreTask
) -> None:
    store_task(bob, alice, due_date=DAY, status=Status.DONE, completed_at=EARLIER)
    store_task(bob, alice, due_date=TODAY)
    store_task(bob, alice, due_date=DAY + (DAY - TODAY))
    store_task(bob, alice, due_date=None)
    store_task(bob, None, due_date=DAY)  # bob owns it, but nobody is assigned

    assert recipients() == []


@pytest.mark.parametrize(
    "fields", [{"is_active": False}, {"email": ""}], ids=["inactive", "no-email-address"]
)
def test_an_assignee_who_cant_receive_email_is_left_out(
    make_user: MakeUser, bob: User, store_task: StoreTask, fields: dict[str, object]
) -> None:
    carol = make_user("carol", **({"email": "carol@example.com"} | fields))
    store_task(bob, carol, due_date=DAY)

    assert recipients() == []


def test_each_recipient_appears_once_in_one_query(
    alice: User,
    bob: User,
    store_task: StoreTask,
    django_assert_num_queries: DjangoAssertNumQueries,
) -> None:
    for _ in range(3):
        store_task(bob, alice, due_date=DAY)
    store_task(alice, bob, due_date=DAY)

    with django_assert_num_queries(1):
        assert recipients() == sorted([alice.pk, bob.pk])


def test_the_digest_holds_the_users_open_tasks_due_that_day_by_title(
    alice: User,
    bob: User,
    store_task: StoreTask,
    django_assert_num_queries: DjangoAssertNumQueries,
) -> None:
    later = store_task(bob, alice, title="Write the tests", due_date=DAY)
    sooner = store_task(
        bob, alice, title="Review the plan", due_date=DAY, status=Status.IN_PROGRESS
    )
    store_task(
        bob, alice, title="Done already", due_date=DAY, status=Status.DONE, completed_at=EARLIER
    )
    store_task(bob, alice, title="Another day", due_date=TODAY)
    store_task(alice, bob, title="Alice owns it, Bob has it", due_date=DAY)

    with django_assert_num_queries(1):
        tasks = list(due_on_for_assignee(alice, DAY))
        owners = [task.owner.username for task in tasks]

    assert [task.pk for task in tasks] == [sooner.id, later.id]
    assert owners == ["bob", "bob"]


def test_the_digest_reads_only_what_the_user_can_see(
    alice: User, bob: User, store_task: StoreTask
) -> None:
    store_task(bob, alice, due_date=DAY)

    digest = set(due_on_for_assignee(alice, DAY).values_list("pk", flat=True))

    assert digest
    assert digest <= set(visible_tasks(alice).values_list("pk", flat=True))
