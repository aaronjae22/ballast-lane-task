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


def test_endpoints_that_need_a_token_use_the_jwt_bearer_scheme(client: Client) -> None:
    """So a token pasted into Swagger's Authorize is sent as Authorization: Bearer."""
    api = schema(client)

    assert api["components"]["securitySchemes"]["jwtAuth"] == {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    for path in ("/api/users/", "/api/users/me/"):
        assert api["paths"][path]["get"]["security"] == [{"jwtAuth": []}]


@pytest.mark.parametrize("path", ["/api/users/", "/api/users/me/"])
def test_the_users_endpoints_document_their_errors(client: Client, path: str) -> None:
    responses = schema(client)["paths"][path]["get"]["responses"]

    assert set(responses) == {"200", "401", "429"}
    assert responses["401"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/Error"
    }


def test_login_documents_its_body_its_answers_and_no_token(client: Client) -> None:
    api = schema(client)
    login = api["paths"]["/api/auth/token/"]["post"]
    body = login["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]

    assert set(login["responses"]) == {"200", "400", "401", "429"}
    # The refresh token goes into the cookie, never into the documented body.
    assert set(api["components"]["schemas"][body.rsplit("/", 1)[1]]["properties"]) == {"access"}
    assert {"jwtAuth": []} not in login.get("security", [])


def test_refresh_documents_an_access_only_body_and_no_token(client: Client) -> None:
    api = schema(client)
    refresh = api["paths"]["/api/auth/token/refresh/"]["post"]
    body = refresh["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]

    assert set(refresh["responses"]) == {"200", "401", "415", "429"}
    assert "requestBody" not in refresh
    assert set(api["components"]["schemas"][body.rsplit("/", 1)[1]]["properties"]) == {"access"}
    assert {"jwtAuth": []} not in refresh.get("security", [])


def test_logout_documents_its_empty_answer_and_no_token(client: Client) -> None:
    logout = schema(client)["paths"]["/api/auth/logout/"]["post"]

    assert set(logout["responses"]) == {"204", "415", "429"}
    assert "content" not in logout["responses"]["204"]
    assert "requestBody" not in logout
    assert {"jwtAuth": []} not in logout.get("security", [])


def list_parameters(client: Client) -> dict[str, dict]:
    parameters = schema(client)["paths"]["/api/tasks/"]["get"]["parameters"]
    return {parameter["name"]: parameter for parameter in parameters}


def test_every_list_filter_is_documented_with_its_help_text(client: Client) -> None:
    from tasks.api.filters import TaskFilter

    parameters = list_parameters(client)

    for name, task_filter in TaskFilter.base_filters.items():
        # drf-spectacular appends the list of choices to a choice filter's description.
        assert parameters[name]["description"].startswith(task_filter.extra["help_text"]), name


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        (
            "status",
            {
                "type": "array",
                "items": {"type": "string", "enum": ["done", "in_progress", "to_do"]},
            },
        ),
        ("due_after", {"type": "string", "format": "date"}),
        ("due_before", {"type": "string", "format": "date"}),
        # The query string carries "true" or "false"; anything else is a 400 (ADR 0013).
        ("overdue", {"type": "string", "enum": ["false", "true"]}),
        ("assignee", {"type": "string"}),
        ("search", {"type": "string"}),
        ("page", {"type": "integer"}),
        ("page_size", {"type": "integer"}),
    ],
)
def test_each_list_parameter_has_the_type_it_takes(
    client: Client, name: str, expected: dict
) -> None:
    assert list_parameters(client)[name]["schema"] == expected


def test_ordering_lists_every_choice_in_both_directions(client: Client) -> None:
    ordering = list_parameters(client)["ordering"]

    assert ordering["schema"]["type"] == "array"
    assert set(ordering["schema"]["items"]["enum"]) == {
        "due_date",
        "-due_date",
        "created_at",
        "-created_at",
        "status",
        "-status",
    }
    # Comma-separated, as one parameter: ?ordering=status,-due_date
    assert ordering["explode"] is False


def test_the_login_body_has_a_plain_component_name(client: Client) -> None:
    """The frontend's generated types are named after the components (iteration 5)."""
    login = schema(client)["paths"]["/api/auth/token/"]["post"]

    body = login["requestBody"]["content"]["application/json"]["schema"]

    assert body == {"$ref": "#/components/schemas/LoginRequest"}


def test_create_documents_its_own_body_and_answers(client: Client) -> None:
    api = schema(client)
    create = api["paths"]["/api/tasks/"]["post"]
    body = create["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    component = api["components"]["schemas"][body.rsplit("/", 1)[1]]

    assert set(create["responses"]) == {"201", "400", "401", "429"}
    assert set(component["properties"]) == {"title", "description", "due_date", "assignee_id"}
    assert component["required"] == ["title"]


def test_edit_documents_its_own_body_and_answers_and_there_is_no_put(client: Client) -> None:
    api = schema(client)
    task = api["paths"]["/api/tasks/{id}/"]
    body = task["patch"]["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    component = api["components"]["schemas"][body.rsplit("/", 1)[1]]

    assert "put" not in task
    assert set(task["patch"]["responses"]) == {"200", "400", "401", "403", "404", "429"}
    assert set(component["properties"]) == {"title", "description", "due_date"}
    assert "required" not in component
