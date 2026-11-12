"""visible_tasks(user): can_view() on the read side, driven by the same matrix row (ADR 0003)."""

import pytest
from pytest_django import DjangoAssertNumQueries

from accounts.models import User
from tasks.domain.actor import Actor
from tasks.domain.permissions import can_view
from tasks.selectors import visible_tasks
from tests.conftest import StoreTask
from tests.unit.permission_matrix import ALLOWED, MATRIX, ROLES

pytestmark = pytest.mark.django_db


def actor_for(user: User) -> Actor:
    return Actor(id=user.pk, is_admin=user.is_admin)


@pytest.mark.parametrize(
    ("role", "outcome"), list(zip(ROLES, MATRIX["view"], strict=True)), ids=list(ROLES)
)
def test_visible_tasks_follows_the_view_row_of_the_matrix(
    users_by_role: dict[str, User], store_task: StoreTask, role: str, outcome: str
) -> None:
    task = store_task(users_by_role["owner"], users_by_role["assignee"])
    user = users_by_role[role]

    visible = visible_tasks(user).filter(pk=task.id).exists()

    assert visible is (outcome == ALLOWED)
    assert can_view(actor_for(user), task) is visible


@pytest.mark.parametrize("role", ROLES)
def test_an_unassigned_task_is_visible_only_to_its_owner_and_admins(
    users_by_role: dict[str, User], store_task: StoreTask, role: str
) -> None:
    task = store_task(users_by_role["owner"])
    user = users_by_role[role]

    visible = visible_tasks(user).filter(pk=task.id).exists()

    assert visible is (role in ("owner", "admin"))
    assert can_view(actor_for(user), task) is visible


def test_among_several_tasks_a_user_sees_only_those_they_own_or_are_assigned(
    owner: User, assignee: User, admin: User, other_user: User, store_task: StoreTask
) -> None:
    owned = store_task(owner)
    assigned = store_task(other_user, owner)
    others = store_task(other_user, assignee)
    admins = store_task(admin)

    assert set(visible_tasks(owner).values_list("id", flat=True)) == {owned.id, assigned.id}
    assert set(visible_tasks(admin).values_list("id", flat=True)) == {
        owned.id,
        assigned.id,
        others.id,
        admins.id,
    }


def test_listing_tasks_with_their_owner_and_assignee_takes_one_query(
    owner: User,
    assignee: User,
    store_task: StoreTask,
    django_assert_num_queries: DjangoAssertNumQueries,
) -> None:
    for title in ("One", "Two", "Three"):
        store_task(owner, assignee, title=title)

    with django_assert_num_queries(1):
        names = [(task.owner.username, task.assignee.username) for task in visible_tasks(owner)]

    assert names == [("owner", "assignee")] * 3
