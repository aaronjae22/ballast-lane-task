"""Fixtures for the API tests."""

import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def empty_cache() -> None:
    """The throttles count requests in the cache, so every test starts from zero (ADR 0014)."""
    cache.clear()
