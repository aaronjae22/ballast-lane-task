"""POST /api/auth/logout/: blacklist the refresh token and clear its cookie (ADR 0014).

The client wants to be signed out whatever state its cookie is in, so logout always answers
204 and clears the cookie. It needs no access token: the cookie is what it revokes.
"""

from datetime import timedelta

import pytest
from rest_framework.response import Response
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from accounts.models import User

pytestmark = pytest.mark.django_db

LOGOUT_URL = "/api/auth/logout/"
REFRESH_URL = "/api/auth/token/refresh/"
COOKIE = "refresh_token"


def assert_cookie_cleared(response: Response) -> None:
    cookie = response.cookies[COOKIE]
    assert cookie.value == ""
    assert cookie["max-age"] == 0
    # A browser deletes a cookie only when the path matches the one it was set with.
    assert cookie["path"] == "/api/auth/"


def test_logging_out_is_204_and_clears_the_cookie(owner: User, api_client: APIClient) -> None:
    api_client.cookies[COOKIE] = str(RefreshToken.for_user(owner))

    response = api_client.post(LOGOUT_URL)

    assert response.status_code == 204
    assert response.content == b""
    assert_cookie_cleared(response)


def test_a_logged_out_token_can_no_longer_refresh(owner: User, api_client: APIClient) -> None:
    token = str(RefreshToken.for_user(owner))
    api_client.cookies[COOKIE] = token
    api_client.post(LOGOUT_URL)

    api_client.cookies[COOKIE] = token
    response = api_client.post(REFRESH_URL)

    assert response.status_code == 401


@pytest.mark.parametrize("cookie", [None, "", "not-a-token"], ids=["absent", "empty", "garbage"])
def test_logging_out_without_a_valid_cookie_still_signs_out(
    api_client: APIClient, cookie: str | None
) -> None:
    if cookie is not None:
        api_client.cookies[COOKIE] = cookie

    response = api_client.post(LOGOUT_URL)

    assert response.status_code == 204
    assert_cookie_cleared(response)


def test_logging_out_twice_is_fine(owner: User, api_client: APIClient) -> None:
    token = str(RefreshToken.for_user(owner))
    for _ in range(2):
        api_client.cookies[COOKIE] = token

        response = api_client.post(LOGOUT_URL)

        assert response.status_code == 204
        assert_cookie_cleared(response)


def test_an_expired_access_token_in_the_header_doesnt_block_logging_out(
    owner: User, api_client: APIClient
) -> None:
    expired = AccessToken.for_user(owner)
    expired.set_exp(from_time=expired.current_time - timedelta(minutes=10))
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {expired}")
    api_client.cookies[COOKIE] = str(RefreshToken.for_user(owner))

    assert api_client.post(LOGOUT_URL).status_code == 204


def test_a_form_post_is_refused_and_signs_no_one_out(owner: User, api_client: APIClient) -> None:
    token = str(RefreshToken.for_user(owner))
    api_client.cookies[COOKIE] = token

    response = api_client.post(LOGOUT_URL, {"x": "y"}, format="multipart")

    assert response.status_code == 415
    assert COOKIE not in response.cookies
    api_client.cookies[COOKIE] = token
    assert api_client.post(REFRESH_URL).status_code == 200
