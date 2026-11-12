"""Fixtures for the API tests."""

from collections.abc import Callable

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import User
from tasks.api import wiring
from tests.unit.fakes import RecordingNotifier

type ClientFor = Callable[[User], APIClient]


@pytest.fixture(autouse=True)
def empty_cache() -> None:
    """The throttles count requests in the cache, so every test starts from zero (ADR 0014)."""
    cache.clear()


@pytest.fixture
def api_client() -> APIClient:
    """A client with no token."""
    return APIClient()


@pytest.fixture
def client_for() -> ClientFor:
    """A client that sends a real access token for this user, as the frontend will.

    The token goes through JWTAuthentication like any other, so the tests cover it too.
    """

    def make(user: User) -> APIClient:
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")
        return client

    return make


@pytest.fixture
def notifier(monkeypatch: pytest.MonkeyPatch) -> RecordingNotifier:
    """Stands in for whatever wiring.notifier() returns, now or after iteration 4."""
    recording = RecordingNotifier()
    monkeypatch.setattr(wiring, "notifier", lambda: recording)
    return recording
