"""GET /api/users/ and /api/users/me/ (spec section 5, ADR 0014), and JWT authentication.

These are the first endpoints that need a token, so they also pin how a missing, expired or
deactivated user's token is refused, and the signed-in user's rate limit.
"""

from datetime import timedelta

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import User
from tests.api.conftest import ClientFor
from tests.conftest import MakeUser

pytestmark = pytest.mark.django_db

USERS_URL = "/api/users/"
ME_URL = "/api/users/me/"


def test_the_users_list_has_every_active_user_by_username(
    owner: User, assignee: User, admin: User, make_user: MakeUser, client_for: ClientFor
) -> None:
    named = make_user("beth", first_name="Beth", last_name="Smith")
    make_user("deactivated", is_active=False)

    response = client_for(owner).get(USERS_URL)

    assert response.status_code == 200
    assert response.json() == [
        {"id": admin.pk, "name": "admin"},
        {"id": assignee.pk, "name": "assignee"},
        {"id": named.pk, "name": "Beth Smith"},
        {"id": owner.pk, "name": "owner"},
    ]


@pytest.mark.parametrize("role", ["owner", "admin"])
def test_me_is_the_signed_in_user(
    users_by_role: dict[str, User], client_for: ClientFor, role: str
) -> None:
    user = users_by_role[role]

    response = client_for(user).get(ME_URL)

    assert response.status_code == 200
    assert response.json() == {
        "id": user.pk,
        "username": user.username,
        "name": user.display_name,
        "is_admin": role == "admin",
    }


@pytest.mark.parametrize("url", [USERS_URL, ME_URL])
def test_the_users_endpoints_need_a_token(api_client: APIClient, url: str) -> None:
    response = api_client.get(url)

    assert response.status_code == 401
    assert response["WWW-Authenticate"].startswith("Bearer")


def test_an_expired_access_token_is_refused(owner: User, api_client: APIClient) -> None:
    token = AccessToken.for_user(owner)
    token.set_exp(from_time=token.current_time - timedelta(minutes=10))
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    response = api_client.get(ME_URL)

    assert response.status_code == 401
    assert response.json()["code"] == "token_not_valid"


def test_a_deactivated_users_token_is_refused(owner: User, client_for: ClientFor) -> None:
    client = client_for(owner)
    owner.is_active = False
    owner.save()

    assert client.get(ME_URL).status_code == 401


def test_an_access_token_lives_five_minutes(owner: User) -> None:
    token = AccessToken.for_user(owner)

    assert token["exp"] - token["iat"] == 5 * 60


def test_a_signed_in_user_is_limited_to_120_requests_a_minute(
    owner: User, client_for: ClientFor
) -> None:
    client = client_for(owner)
    for _ in range(120):
        assert client.get(ME_URL).status_code == 200

    response = client.get(ME_URL)

    assert response.status_code == 429
    assert int(response["Retry-After"]) > 0
