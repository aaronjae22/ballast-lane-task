import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.handlers.asgi import ASGIHandler
from django.core.handlers.wsgi import WSGIHandler
from django.urls import reverse

from accounts.models import User
from config.settings import env_bool

BACKEND_DIR = Path(__file__).resolve().parents[2]


def import_base_settings(**env: str) -> subprocess.CompletedProcess[str]:
    """Import config.settings in a fresh interpreter with only the given Django variables."""
    clean_env = {k: v for k, v in os.environ.items() if not k.startswith("DJANGO_")}
    return subprocess.run(
        [sys.executable, "-c", "import config.settings"],
        cwd=BACKEND_DIR,
        env={**clean_env, **env},
        capture_output=True,
        text=True,
        check=False,
    )


def test_auth_user_model_is_the_custom_user() -> None:
    assert settings.AUTH_USER_MODEL == "accounts.User"
    assert get_user_model() is User


def test_insecure_default_secret_key_is_refused_when_debug_is_off() -> None:
    result = import_base_settings()

    assert result.returncode != 0
    assert "ImproperlyConfigured" in result.stderr
    assert "DJANGO_SECRET_KEY must be set" in result.stderr


def test_insecure_default_secret_key_is_allowed_when_debug_is_on() -> None:
    result = import_base_settings(DJANGO_DEBUG="true")

    assert result.returncode == 0, result.stderr


def test_secret_key_from_the_environment_is_accepted_when_debug_is_off() -> None:
    result = import_base_settings(DJANGO_SECRET_KEY="a-real-secret-from-the-environment")

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("value", "expected"),
    [("1", True), ("true", True), (" YES ", True), ("on", True), ("0", False), ("off", False)],
)
def test_env_bool_parses_common_spellings(
    monkeypatch: pytest.MonkeyPatch, value: str, expected: bool
) -> None:
    monkeypatch.setenv("SOME_FLAG", value)

    assert env_bool("SOME_FLAG") is expected


@pytest.mark.parametrize("value", [None, ""])
def test_env_bool_falls_back_to_the_default_when_unset_or_empty(
    monkeypatch: pytest.MonkeyPatch, value: str | None
) -> None:
    if value is None:
        monkeypatch.delenv("SOME_FLAG", raising=False)
    else:
        monkeypatch.setenv("SOME_FLAG", value)

    assert env_bool("SOME_FLAG", default=True) is True


def test_wsgi_and_asgi_entry_points_load() -> None:
    from config.asgi import application as asgi_application
    from config.wsgi import application as wsgi_application

    assert isinstance(wsgi_application, WSGIHandler)
    assert isinstance(asgi_application, ASGIHandler)


def test_admin_is_routed() -> None:
    assert reverse("admin:index") == "/admin/"
