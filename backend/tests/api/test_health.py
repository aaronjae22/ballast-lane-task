from unittest import mock

import pytest
from django.db import OperationalError
from django.test import Client

HEALTH_URL = "/api/health/"


@pytest.mark.django_db
def test_health_is_ok_when_the_database_is_up(client: Client) -> None:
    response = client.get(HEALTH_URL)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_health_is_public_and_ignores_a_bad_token(client: Client) -> None:
    response = client.get(HEALTH_URL, headers={"Authorization": "Bearer not-a-real-token"})

    assert response.status_code == 200


def test_health_is_503_when_the_database_check_fails(client: Client) -> None:
    broken = mock.MagicMock()
    broken.cursor.side_effect = OperationalError("connection refused")

    with mock.patch("config.views.connection", broken):
        response = client.get(HEALTH_URL)

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
