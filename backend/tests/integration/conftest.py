"""Fixtures for integration tests: real users in the test database (Postgres)."""

from collections.abc import Callable

import pytest

from accounts.models import User

type MakeUser = Callable[..., User]


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
