"""Fixtures for unit tests: the four ports as in-memory fakes."""

import pytest

from tests.unit.builders import ADMIN_ID, ASSIGNEE_ID, NOW, OTHER_USER_ID, OWNER_ID, TODAY
from tests.unit.fakes import FakeUserLookup, FixedClock, InMemoryTaskRepository, RecordingNotifier


@pytest.fixture
def repository() -> InMemoryTaskRepository:
    return InMemoryTaskRepository()


@pytest.fixture
def users() -> FakeUserLookup:
    """Every user in tests/unit/builders.py is active; any other id is unknown."""
    return FakeUserLookup({OWNER_ID, ASSIGNEE_ID, ADMIN_ID, OTHER_USER_ID})


@pytest.fixture
def notifier() -> RecordingNotifier:
    return RecordingNotifier()


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(now=NOW, today=TODAY)
