"""Environment variables reach the Django settings they configure.

Settings are read at import time, so each test executes config/settings.py into
a fresh module object. Neither django.conf.settings nor sys.modules is touched,
and no database, Redis or SMTP server is contacted.
"""

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
from django.core.exceptions import ImproperlyConfigured

SETTINGS_PATH = Path(__file__).resolve().parents[2] / "config" / "settings.py"

ENV_VARS = [
    "DJANGO_DEBUG",
    "DJANGO_SECRET_KEY",
    "DJANGO_ALLOWED_HOSTS",
    "DJANGO_TIME_ZONE",
    "DATABASE_URL",
    "REDIS_URL",
    "DJANGO_CACHE",
    "DJANGO_REFRESH_COOKIE_SECURE",
    "EMAIL_HOST",
    "EMAIL_PORT",
    "EMAIL_HOST_USER",
    "EMAIL_HOST_PASSWORD",
    "EMAIL_USE_TLS",
    "DEFAULT_FROM_EMAIL",
]


def load_settings(monkeypatch: pytest.MonkeyPatch, **env: str) -> ModuleType:
    """Execute the base settings with only the given variables set (plus a secret key)."""
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DJANGO_SECRET_KEY", "test-only-not-a-secret")
    for name, value in env.items():
        monkeypatch.setenv(name, value)

    spec = importlib.util.spec_from_file_location("isolated_settings", SETTINGS_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_defaults_point_at_the_local_compose_services(monkeypatch: pytest.MonkeyPatch) -> None:
    s = load_settings(monkeypatch)

    db = s.DATABASES["default"]
    assert db["ENGINE"] == "django.db.backends.postgresql"
    assert (db["HOST"], db["PORT"], db["NAME"]) == ("localhost", 5433, "taskboard")
    assert (db["USER"], db["PASSWORD"]) == ("taskboard", "taskboard")
    assert s.CACHES["default"]["BACKEND"] == "django.core.cache.backends.redis.RedisCache"
    assert s.CACHES["default"]["LOCATION"] == "redis://localhost:6379/0"
    assert (s.EMAIL_HOST, s.EMAIL_PORT, s.EMAIL_USE_TLS) == ("localhost", 1025, False)
    assert s.ALLOWED_HOSTS == ["localhost", "127.0.0.1"]
    assert s.TIME_ZONE == "UTC"
    assert s.USE_TZ is True


def test_database_url_overrides_the_database(monkeypatch: pytest.MonkeyPatch) -> None:
    s = load_settings(monkeypatch, DATABASE_URL="postgres://app:s3cret@db.internal:6543/board")

    db = s.DATABASES["default"]
    assert db["ENGINE"] == "django.db.backends.postgresql"
    assert (db["HOST"], db["PORT"], db["NAME"]) == ("db.internal", 6543, "board")
    assert (db["USER"], db["PASSWORD"]) == ("app", "s3cret")


def test_redis_url_overrides_the_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    s = load_settings(monkeypatch, REDIS_URL="redis://cache.internal:6380/2")

    assert s.CACHES["default"]["LOCATION"] == "redis://cache.internal:6380/2"


def test_django_cache_locmem_swaps_redis_for_a_local_memory_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """For a host without Redis. Per process, so limits don't hold across processes."""
    s = load_settings(monkeypatch, DJANGO_CACHE="locmem")

    assert s.CACHES["default"]["BACKEND"] == "django.core.cache.backends.locmem.LocMemCache"


def test_django_cache_redis_is_the_default(monkeypatch: pytest.MonkeyPatch) -> None:
    s = load_settings(monkeypatch, DJANGO_CACHE="redis")

    assert s.CACHES["default"]["BACKEND"] == "django.core.cache.backends.redis.RedisCache"


@pytest.mark.parametrize("value", ["memcached", "LocMem", "dummy"])
def test_an_unknown_django_cache_is_refused(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    with pytest.raises(ImproperlyConfigured, match="DJANGO_CACHE"):
        load_settings(monkeypatch, DJANGO_CACHE=value)


@pytest.mark.parametrize(
    ("env", "secure"),
    [
        ({}, True),
        ({"DJANGO_DEBUG": "true"}, False),
        ({"DJANGO_DEBUG": "true", "DJANGO_REFRESH_COOKIE_SECURE": "true"}, True),
        ({"DJANGO_REFRESH_COOKIE_SECURE": "false"}, False),
    ],
    ids=["production", "local-development", "forced-on", "forced-off"],
)
def test_the_refresh_cookie_is_secure_outside_local_development(
    monkeypatch: pytest.MonkeyPatch, env: dict[str, str], secure: bool
) -> None:
    """Local development is DEBUG on; the override is for the prod image over http (ADR 0014)."""
    s = load_settings(monkeypatch, **env)

    assert s.REFRESH_COOKIE_SECURE is secure


def test_email_variables_override_smtp(monkeypatch: pytest.MonkeyPatch) -> None:
    s = load_settings(
        monkeypatch,
        EMAIL_HOST="smtp.example.com",
        EMAIL_PORT="587",
        EMAIL_HOST_USER="mailer",
        EMAIL_HOST_PASSWORD="mail-password",
        EMAIL_USE_TLS="true",
        DEFAULT_FROM_EMAIL="Board <board@example.com>",
    )

    assert s.EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend"
    assert (s.EMAIL_HOST, s.EMAIL_PORT) == ("smtp.example.com", 587)
    assert (s.EMAIL_HOST_USER, s.EMAIL_HOST_PASSWORD) == ("mailer", "mail-password")
    assert s.EMAIL_USE_TLS is True
    assert s.DEFAULT_FROM_EMAIL == "Board <board@example.com>"


def test_allowed_hosts_and_time_zone_follow_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = load_settings(
        monkeypatch,
        DJANGO_ALLOWED_HOSTS="api.example.com, localhost,",
        DJANGO_TIME_ZONE="America/New_York",
    )

    assert s.ALLOWED_HOSTS == ["api.example.com", "localhost"]
    assert s.TIME_ZONE == "America/New_York"
    assert s.USE_TZ is True
