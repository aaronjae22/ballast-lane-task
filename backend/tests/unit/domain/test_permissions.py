"""The permission rules and visibility (spec section 3, ADR 0003)."""

import pytest

from tasks.domain import errors
from tasks.domain.actor import Actor
from tasks.domain.permissions import Action, can_view, check_permission
from tests.unit.builders import ADMIN_ID, ASSIGNEE_ID, OTHER_USER_ID, OWNER_ID, make_task
from tests.unit.permission_matrix import (
    ALLOWED,
    MATRIX,
    NOT_ALLOWED,
    NOT_FOUND,
    ROLES,
    matrix_cases,
)

ACTORS = {
    "owner": Actor(id=OWNER_ID),
    "assignee": Actor(id=ASSIGNEE_ID),
    "admin": Actor(id=ADMIN_ID, is_admin=True),
    "anyone else": Actor(id=OTHER_USER_ID),
}
ERRORS: dict[str, type[errors.DomainError]] = {
    NOT_ALLOWED: errors.NotAllowed,
    NOT_FOUND: errors.TaskNotFound,
}


@pytest.mark.parametrize(
    ("action", "role", "outcome"),
    matrix_cases(),
    ids=[f"{action}-{role}-{outcome}" for action, role, outcome in matrix_cases()],
)
def test_permission_matrix(action: str, role: str, outcome: str) -> None:
    task = make_task(owner_id=OWNER_ID, assignee_id=ASSIGNEE_ID)

    if outcome == ALLOWED:
        check_permission(ACTORS[role], task, Action(action))
    else:
        with pytest.raises(ERRORS[outcome]):
            check_permission(ACTORS[role], task, Action(action))


def test_every_action_in_the_matrix_is_a_domain_action() -> None:
    assert set(MATRIX) == {action.value for action in Action}


@pytest.mark.parametrize(
    ("role", "outcome"), zip(ROLES, MATRIX["view"], strict=True), ids=list(ROLES)
)
def test_can_view_matches_the_view_row(role: str, outcome: str) -> None:
    task = make_task(owner_id=OWNER_ID, assignee_id=ASSIGNEE_ID)

    assert can_view(ACTORS[role], task) is (outcome == ALLOWED)


def test_an_unassigned_task_is_visible_only_to_its_owner_and_admins() -> None:
    task = make_task(owner_id=OWNER_ID, assignee_id=None)

    assert [can_view(ACTORS[role], task) for role in ROLES] == [True, False, True, False]


def test_a_task_you_cant_see_is_not_found_whatever_the_action() -> None:
    task = make_task(id=7, owner_id=OWNER_ID, assignee_id=ASSIGNEE_ID)

    with pytest.raises(errors.TaskNotFound) as error:
        check_permission(ACTORS["anyone else"], task, Action.EDIT)

    assert error.value.task_id == 7
