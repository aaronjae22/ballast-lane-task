"""DELETE /api/tasks/{id}/: delete a task through DeleteTask (spec sections 3 and 5).

The owner or an admin only (the HTTP matrix covers who). A hard delete: the spec has no
archive. 204 with no body, after which the task is 404 like any other missing one.
"""

import pytest
from rest_framework.test import APIClient

from accounts.models import User
from tasks import models
from tests.api.conftest import ClientFor
from tests.conftest import StoreTask

pytestmark = pytest.mark.django_db


def test_deleting_a_task_is_204_and_it_is_gone(
    owner: User, store_task: StoreTask, client_for: ClientFor
) -> None:
    task = store_task(owner)
    kept = store_task(owner)
    client = client_for(owner)

    response = client.delete(f"/api/tasks/{task.id}/")

    assert response.status_code == 204
    assert response.content == b""
    assert not models.Task.objects.filter(pk=task.id).exists()
    assert models.Task.objects.filter(pk=kept.id).exists()
    assert client.get(f"/api/tasks/{task.id}/").status_code == 404


def test_deleting_it_again_is_404(
    owner: User, store_task: StoreTask, client_for: ClientFor
) -> None:
    task = store_task(owner)
    client = client_for(owner)
    client.delete(f"/api/tasks/{task.id}/")

    response = client.delete(f"/api/tasks/{task.id}/")

    assert response.status_code == 404
    assert response.json() == {"detail": f"Task {task.id} not found."}


def test_deleting_needs_a_token(owner: User, store_task: StoreTask, api_client: APIClient) -> None:
    task = store_task(owner)

    assert api_client.delete(f"/api/tasks/{task.id}/").status_code == 401
    assert models.Task.objects.filter(pk=task.id).exists()
