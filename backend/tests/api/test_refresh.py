"""POST /api/auth/token/refresh/: a new access token from the refresh cookie (ADRs 0006, 0014).

Every refresh rotates the cookie and blacklists the old token. A failed refresh is 401 and
leaves the cookie alone: two refreshes sent with the same cookie race, and if the loser's
response cleared the cookie after the winner set a new one, the user would be signed out.
"""

from datetime import timedelta

import pytest
from rest_framework.response import Response
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from accounts.models import User

pytestmark = pytest.mark.django_db

REFRESH_URL = "/api/auth/token/refresh/"
ME_URL = "/api/users/me/"
COOKIE = "refresh_token"
ONE_DAY = 24 * 60 * 60


def refresh_with(client: APIClient, token: str) -> Response:
    client.cookies[COOKIE] = token
    return client.post(REFRESH_URL)


def assert_cookie_untouched(response: Response) -> None:
    assert COOKIE not in response.cookies


def test_a_refresh_returns_a_new_access_token_and_rotates_the_cookie(
    owner: User, api_client: APIClient
) -> None:
    old = str(RefreshToken.for_user(owner))

    response = refresh_with(api_client, old)

    assert response.status_code == 200
    assert set(response.json()) == {"access"}
    cookie = response.cookies[COOKIE]
    assert cookie.value not in ("", old)
    assert cookie.value not in response.content.decode()
    assert (cookie["httponly"], cookie["samesite"], cookie["secure"]) == (True, "Strict", True)
    assert (cookie["path"], cookie["max-age"]) == ("/api/auth/", ONE_DAY)


def test_the_new_access_token_signs_the_user_in(owner: User, api_client: APIClient) -> None:
    access = refresh_with(api_client, str(RefreshToken.for_user(owner))).json()["access"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    assert api_client.get(ME_URL).json()["id"] == owner.pk


def test_the_rotated_cookie_refreshes_again(owner: User, api_client: APIClient) -> None:
    first = refresh_with(api_client, str(RefreshToken.for_user(owner)))

    second = refresh_with(api_client, first.cookies[COOKIE].value)

    assert second.status_code == 200


def test_a_token_already_rotated_is_refused_and_the_new_cookie_survives(
    owner: User, api_client: APIClient
) -> None:
    """The race in ADR 0014: the loser's 401 must not delete the cookie the winner set."""
    old = str(RefreshToken.for_user(owner))
    winner = refresh_with(api_client, old)
    assert winner.status_code == 200

    loser = refresh_with(api_client, old)

    assert loser.status_code == 401
    assert_cookie_untouched(loser)


def test_without_a_cookie_a_refresh_is_401(api_client: APIClient) -> None:
    response = api_client.post(REFRESH_URL)

    assert response.status_code == 401
    assert response["WWW-Authenticate"].startswith("Bearer")
    assert_cookie_untouched(response)


def test_a_cookie_that_isnt_a_valid_refresh_token_is_401(
    owner: User, api_client: APIClient
) -> None:
    expired = RefreshToken.for_user(owner)
    expired.set_exp(from_time=expired.current_time - timedelta(days=2))
    tokens = ["not-a-token", str(AccessToken.for_user(owner)), str(expired)]

    for token in tokens:
        response = refresh_with(api_client, token)

        assert response.status_code == 401, token
        assert_cookie_untouched(response)


def test_an_inactive_users_token_is_401(owner: User, api_client: APIClient) -> None:
    token = str(RefreshToken.for_user(owner))
    owner.is_active = False
    owner.save()

    response = refresh_with(api_client, token)

    assert response.status_code == 401
    assert_cookie_untouched(response)


def test_a_deleted_users_token_is_401_not_a_server_error(
    owner: User, api_client: APIClient
) -> None:
    """simplejwt's serializer raises User.DoesNotExist here, which would be a 500."""
    token = str(RefreshToken.for_user(owner))
    owner.delete()

    response = refresh_with(api_client, token)

    assert response.status_code == 401
    assert_cookie_untouched(response)


def test_an_expired_access_token_in_the_header_doesnt_block_a_refresh(
    owner: User, api_client: APIClient
) -> None:
    """The frontend refreshes because its access token expired, and may still send it."""
    expired = AccessToken.for_user(owner)
    expired.set_exp(from_time=expired.current_time - timedelta(minutes=10))
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {expired}")

    response = refresh_with(api_client, str(RefreshToken.for_user(owner)))

    assert response.status_code == 200


def test_a_form_post_is_refused(owner: User, api_client: APIClient) -> None:
    """A cross-site form can't send JSON (ADR 0014), even to a view that reads only the cookie."""
    api_client.cookies[COOKIE] = str(RefreshToken.for_user(owner))

    response = api_client.post(REFRESH_URL, {"x": "y"}, format="multipart")

    assert response.status_code == 415
    assert_cookie_untouched(response)


def test_refreshing_is_limited_like_any_anonymous_request(api_client: APIClient) -> None:
    for _ in range(30):
        assert api_client.post(REFRESH_URL).status_code == 401

    response = api_client.post(REFRESH_URL)

    assert response.status_code == 429
    assert int(response["Retry-After"]) > 0
