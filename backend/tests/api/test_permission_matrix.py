"""The permission matrix (spec section 3) through HTTP: its third level.

The same rows as tests/unit/permission_matrix.py, which already drive the domain rule, the
use cases and visible_tasks. Here each cell is a request by a real user with a real token.
So a view wired to the wrong use case, or reading the wrong queryset, fails here.
"""

from collections.abc import Callable

import pytest
from rest_framework.response import Response
from rest_framework.test import APIClient

from accounts.models import User
from tasks import models
from tasks.domain.status import Status
from tests.api.conftest import ClientFor
from tests.conftest import StoreTask
from tests.unit.builders import EARLIER
from tests.unit.permission_matrix import ALLOWED, MATRIX, NOT_ALLOWED, NOT_FOUND, ROLES

pytestmark = pytest.mark.django_db

type Send = Callable[[APIClient, int, dict[str, User]], Response]

# Matrix action -> its endpoints: (name, status the task starts in, the request, success code).
ENDPOINTS: dict[str, list[tuple[str, Status, Send, int]]] = {
    "view": [("detail", Status.TO_DO, lambda c, i, u: c.get(f"/api/tasks/{i}/"), 200)],
    "edit": [
        ("edit", Status.TO_DO, lambda c, i, u: c.patch(f"/api/tasks/{i}/", {"title": "New"}), 200)
    ],
    "assign": [
        (
            "assign",
            Status.TO_DO,
            lambda c, i, u: c.post(f"/api/tasks/{i}/assign/", {"assignee_id": u["admin"].pk}),
            200,
        )
    ],
    "delete": [("delete", Status.TO_DO, lambda c, i, u: c.delete(f"/api/tasks/{i}/"), 204)],
}
DENIED = {NOT_ALLOWED: 403, NOT_FOUND: 404}

CASES = [
    pytest.param(send, status, success, role, outcome, id=f"{name}-{role}-{outcome}")
    for action, outcomes in MATRIX.items()
    if action in ENDPOINTS
    for name, status, send, success in ENDPOINTS[action]
    for role, outcome in zip(ROLES, outcomes, strict=True)
]


@pytest.mark.parametrize(("send", "status", "success", "role", "outcome"), CASES)
def test_permission_matrix_through_http(
    users_by_role: dict[str, User],
    store_task: StoreTask,
    client_for: ClientFor,
    send: Send,
    status: Status,
    success: int,
    role: str,
    outcome: str,
) -> None:
    completed_at = EARLIER if status is Status.DONE else None
    task = store_task(
        users_by_role["owner"], users_by_role["assignee"], status=status, completed_at=completed_at
    )
    assert task.id is not None
    before = models.Task.objects.filter(pk=task.id).values().get()

    response = send(client_for(users_by_role[role]), task.id, users_by_role)

    assert response.status_code == (success if outcome == ALLOWED else DENIED[outcome])
    if outcome != ALLOWED:
        assert models.Task.objects.filter(pk=task.id).values().get() == before


@pytest.mark.parametrize(
    ("role", "outcome"), list(zip(ROLES, MATRIX["view"], strict=True)), ids=list(ROLES)
)
def test_the_list_follows_the_view_row(
    users_by_role: dict[str, User],
    store_task: StoreTask,
    client_for: ClientFor,
    role: str,
    outcome: str,
) -> None:
    task = store_task(users_by_role["owner"], users_by_role["assignee"])

    response = client_for(users_by_role[role]).get("/api/tasks/")

    listed = [item["id"] for item in response.json()["results"]]
    assert (task.id in listed) is (outcome == ALLOWED)
