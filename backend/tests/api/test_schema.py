"""The OpenAPI schema and Swagger UI (ADRs 0005 and 0014).

The schema is a contract: iteration 5 generates the frontend's types from it. So it must
validate with no warnings, not just render: a warning means part of the API is missing from
the schema or typed wrong, and the generated client would be wrong in the same place.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from django.core.management import call_command
from django.test import Client
from drf_spectacular.drainage import GENERATOR_STATS
from drf_spectacular.settings import spectacular_settings

SCHEMA_URL = "/api/schema/"
DOCS_URL = "/api/docs/"


@pytest.fixture(autouse=True)
def no_earlier_warnings() -> Iterator[None]:
    """drf-spectacular counts warnings in a class-level cache that nothing else clears."""
    GENERATOR_STATS.reset()
    yield
    GENERATOR_STATS.reset()


def schema(client: Client) -> dict:
    response = client.get(SCHEMA_URL, {"format": "json"})
    assert response.status_code == 200
    return response.json()


def test_the_schema_validates_with_no_warnings(tmp_path: Path) -> None:
    call_command(
        "spectacular", "--validate", "--fail-on-warn", "--file", str(tmp_path / "schema.yml")
    )


def test_the_schema_is_public_openapi_3(client: Client) -> None:
    assert schema(client)["openapi"].startswith("3.")


def test_swagger_ui_is_public_and_pinned_to_one_version(client: Client) -> None:
    response = client.get(DOCS_URL)

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/html")
    assert "swagger-ui-dist@5." in response.content.decode()
    assert "@latest" not in response.content.decode()


def test_swagger_ui_keeps_the_token_out_of_local_storage() -> None:
    assert not spectacular_settings.SWAGGER_UI_SETTINGS.get("persistAuthorization")


def test_health_is_documented_with_both_answers(client: Client) -> None:
    responses = schema(client)["paths"]["/api/health/"]["get"]["responses"]

    assert set(responses) == {"200", "503"}


@pytest.mark.parametrize("url", [SCHEMA_URL, DOCS_URL])
def test_the_schema_and_docs_are_throttled_as_anonymous(client: Client, url: str) -> None:
    anonymous_limit = 30
    for _ in range(anonymous_limit):
        assert client.get(url).status_code == 200

    response = client.get(url)

    assert response.status_code == 429
    assert int(response["Retry-After"]) > 0
