"""Assigning a task, and when the assignee gets an email (spec section 3)."""

from dataclasses import replace

import pytest

from tasks.domain.assignment import assignment_email_due
from tasks.domain.errors import DomainValidationError
from tests.unit.builders import ADMIN_ID, ASSIGNEE_ID, NOW, OTHER_USER_ID, OWNER_ID, make_task


@pytest.mark.parametrize(
    ("current", "new"),
    [(None, ASSIGNEE_ID), (ASSIGNEE_ID, OTHER_USER_ID), (None, OWNER_ID)],
    ids=["assign", "reassign", "assign-self"],
)
def test_a_task_can_be_assigned_to_an_active_user(current: int | None, new: int) -> None:
    task = make_task(assignee_id=current)

    task.assign(new, assignee_is_active=True, now=NOW)

    assert (task.assignee_id, task.updated_at) == (new, NOW)


def test_unassigning_needs_no_active_user() -> None:
    task = make_task(assignee_id=ASSIGNEE_ID)

    task.assign(None, assignee_is_active=False, now=NOW)

    assert (task.assignee_id, task.updated_at) == (None, NOW)


def test_assigning_a_user_who_isnt_active_is_rejected_and_changes_nothing() -> None:
    task = make_task(assignee_id=None)
    before = replace(task)

    with pytest.raises(DomainValidationError) as error:
        task.assign(ASSIGNEE_ID, assignee_is_active=False, now=NOW)

    assert error.value.field == "assignee_id"
    assert task == before


def test_reassigning_to_the_current_assignee_is_allowed_even_if_they_are_no_longer_active() -> None:
    task = make_task(assignee_id=ASSIGNEE_ID)

    task.assign(ASSIGNEE_ID, assignee_is_active=False, now=NOW)

    assert (task.assignee_id, task.updated_at) == (ASSIGNEE_ID, NOW)


@pytest.mark.parametrize(
    ("previous", "new", "changed_by", "email"),
    [
        (None, ASSIGNEE_ID, OWNER_ID, True),
        (ASSIGNEE_ID, OTHER_USER_ID, OWNER_ID, True),
        (None, OWNER_ID, ADMIN_ID, True),
        (None, OWNER_ID, OWNER_ID, False),
        (ASSIGNEE_ID, OWNER_ID, OWNER_ID, False),
        (ASSIGNEE_ID, None, OWNER_ID, False),
        (ASSIGNEE_ID, ASSIGNEE_ID, OWNER_ID, False),
    ],
    ids=[
        "assign-someone-else",
        "reassign-to-someone-else",
        "admin-assigns-the-owner",
        "self-assign",
        "reassign-to-self",
        "unassign",
        "same-person-again",
    ],
)
def test_an_email_is_due_only_when_the_assignee_changes_to_someone_else(
    previous: int | None, new: int | None, changed_by: int, email: bool
) -> None:
    due = assignment_email_due(
        previous_assignee_id=previous, new_assignee_id=new, changed_by_id=changed_by
    )

    assert due is email
