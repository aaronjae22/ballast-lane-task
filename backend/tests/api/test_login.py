"""POST /api/auth/token/: log in (spec section 6, ADRs 0006 and 0014).

The access token comes back in the body, for the frontend to keep in memory. The refresh
token goes only into an httpOnly cookie that JavaScript can't read, scoped to /api/auth/.
"""

import pytest
from rest_framework.response import Response
from rest_framework.test import APIClient

from accounts.models import User
from tests.conftest import MakeUser

pytestmark = pytest.mark.django_db

LOGIN_URL = "/api/auth/token/"
ME_URL = "/api/users/me/"
COOKIE = "refresh_token"
PASSWORD = "correct horse battery staple"
ONE_DAY = 24 * 60 * 60


@pytest.fixture
def user(make_user: MakeUser) -> User:
    return make_user("ada", password=PASSWORD)


def log_in(client: APIClient, username: str = "ada", password: str = PASSWORD) -> Response:
    return client.post(LOGIN_URL, {"username": username, "password": password})


def test_logging_in_returns_only_the_access_token_in_the_body(
    user: User, api_client: APIClient
) -> None:
    response = log_in(api_client)

    assert response.status_code == 200
    assert set(response.json()) == {"access"}
    assert response.cookies[COOKIE].value not in response.content.decode()


def test_the_refresh_token_goes_into_a_cookie_javascript_cant_read(
    user: User, api_client: APIClient
) -> None:
    cookie = log_in(api_client).cookies[COOKIE]

    assert cookie.value
    assert cookie["httponly"] is True
    assert cookie["samesite"] == "Strict"
    assert cookie["path"] == "/api/auth/"
    # Test settings run with DEBUG off, as production does.
    assert cookie["secure"] is True
    assert cookie["max-age"] == ONE_DAY


def test_the_access_token_signs_the_user_in(user: User, api_client: APIClient) -> None:
    access = log_in(api_client).json()["access"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = api_client.get(ME_URL)

    assert response.status_code == 200
    assert response.json()["id"] == user.pk


@pytest.mark.parametrize(
    ("username", "password", "active"),
    [("ada", "wrong password", True), ("nobody", PASSWORD, True), ("ada", PASSWORD, False)],
    ids=["wrong-password", "unknown-user", "inactive-user"],
)
def test_a_failed_login_is_401_with_no_cookie(
    user: User, api_client: APIClient, username: str, password: str, active: bool
) -> None:
    user.is_active = active
    user.save()

    response = log_in(api_client, username, password)

    assert response.status_code == 401
    assert COOKIE not in response.cookies


def test_a_failed_login_doesnt_reveal_which_accounts_exist(
    user: User, make_user: MakeUser, api_client: APIClient
) -> None:
    make_user("grace", password=PASSWORD, is_active=False)

    wrong_password = log_in(api_client, "ada", "wrong password")
    unknown_user = log_in(api_client, "nobody", PASSWORD)
    inactive_user = log_in(api_client, "grace", PASSWORD)

    assert wrong_password.json() == unknown_user.json() == inactive_user.json()


def test_missing_credentials_are_400_keyed_by_field(api_client: APIClient) -> None:
    response = api_client.post(LOGIN_URL, {})

    assert response.status_code == 400
    assert set(response.json()) == {"username", "password"}


def test_a_form_post_is_refused(user: User, api_client: APIClient) -> None:
    """A cross-site HTML form can't send JSON, so it can't log anyone in (ADR 0014)."""
    response = api_client.post(
        LOGIN_URL, {"username": "ada", "password": PASSWORD}, format="multipart"
    )

    assert response.status_code == 415
    assert COOKIE not in response.cookies


def test_logging_in_is_limited_to_5_attempts_a_minute(user: User, api_client: APIClient) -> None:
    for _ in range(5):
        assert log_in(api_client, password="wrong password").status_code == 401

    response = log_in(api_client)

    assert response.status_code == 429
    assert int(response["Retry-After"]) > 0
    assert COOKIE not in response.cookies
