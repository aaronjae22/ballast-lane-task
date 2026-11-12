"""Fixtures for integration tests: real users and tasks in the test database (Postgres)."""

from collections.abc import Callable

import pytest

from accounts.models import User
from tasks.domain.task import Task
from tasks.infrastructure.repositories import DjangoTaskRepository
from tests.unit.builders import make_task
from tests.unit.permission_matrix import ROLES

type MakeUser = Callable[..., User]
type StoreTask = Callable[..., Task]


@pytest.fixture
def make_user(db: None) -> MakeUser:
    """Create a user with this username and any other fields (is_staff, is_active, ...)."""

    def make(username: str, **fields: object) -> User:
        return User.objects.create_user(username=username, **fields)

    return make


@pytest.fixture
def owner(make_user: MakeUser) -> User:
    return make_user("owner")


@pytest.fixture
def assignee(make_user: MakeUser) -> User:
    return make_user("assignee")


@pytest.fixture
def admin(make_user: MakeUser) -> User:
    return make_user("admin", is_staff=True)


@pytest.fixture
def other_user(make_user: MakeUser) -> User:
    return make_user("other")


@pytest.fixture
def users_by_role(owner: User, assignee: User, admin: User, other_user: User) -> dict[str, User]:
    """One user per column of tests/unit/permission_matrix.py, keyed by its role name."""
    users = dict(zip(ROLES, (owner, assignee, admin, other_user), strict=True))
    assert users["admin"].is_admin
    return users


@pytest.fixture
def store_task(db: None) -> StoreTask:
    """Store a task through the ORM repository, built like the unit tests' tasks.

    Real users stand in for builders' fixed ids, since Postgres assigns the ids.
    """

    def store(owner: User, assignee: User | None = None, **overrides: object) -> Task:
        fields = {"id": None, "owner_id": owner.pk, "assignee_id": assignee and assignee.pk}
        return DjangoTaskRepository().add(make_task(**(fields | overrides)))

    return store
