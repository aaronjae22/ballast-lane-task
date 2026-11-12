"""Overdue and editing a task's title, description and due date (spec section 3)."""

from dataclasses import replace
from datetime import date

import pytest

from tasks.domain.errors import DomainValidationError
from tasks.domain.status import Status
from tasks.domain.task import TITLE_MAX_LENGTH
from tests.unit.builders import (
    ASSIGNEE_ID,
    EARLIER,
    LAST_WEEK,
    NOW,
    OWNER_ID,
    TODAY,
    TOMORROW,
    YESTERDAY,
    make_task,
)
from tests.unit.overdue_cases import OVERDUE_CASES


@pytest.mark.parametrize(
    ("status", "due_date", "overdue"), list(OVERDUE_CASES.values()), ids=list(OVERDUE_CASES)
)
def test_a_task_is_overdue_when_its_due_date_has_passed_and_it_isnt_done(
    status: Status, due_date: date | None, overdue: bool
) -> None:
    assert make_task(status=status, due_date=due_date).is_overdue(TODAY) is overdue


def test_editing_changes_only_the_fields_given() -> None:
    task = make_task(title="Old title", description="Old notes", due_date=TOMORROW)

    task.edit(title="New title", today=TODAY, now=NOW)

    assert (task.title, task.description, task.due_date) == ("New title", "Old notes", TOMORROW)


def test_editing_the_description_and_the_due_date() -> None:
    task = make_task(description="Old notes", due_date=TOMORROW)

    task.edit(description="", due_date=TODAY, today=TODAY, now=NOW)

    assert (task.description, task.due_date) == ("", TODAY)


def test_editing_can_clear_the_due_date() -> None:
    task = make_task(due_date=TOMORROW)

    task.edit(due_date=None, today=TODAY, now=NOW)

    assert task.due_date is None


@pytest.mark.parametrize(
    "title",
    ["", "   ", "x" * (TITLE_MAX_LENGTH + 1)],
    ids=["empty", "whitespace-only", "201-characters"],
)
def test_editing_applies_the_title_rules(title: str) -> None:
    with pytest.raises(DomainValidationError) as error:
        make_task().edit(title=title, today=TODAY, now=NOW)

    assert error.value.field == "title"


def test_editing_strips_the_title() -> None:
    task = make_task()

    task.edit(title="  New title  ", today=TODAY, now=NOW)

    assert task.title == "New title"


def test_editing_rejects_a_due_date_in_the_past() -> None:
    with pytest.raises(DomainValidationError) as error:
        make_task(due_date=TOMORROW).edit(due_date=YESTERDAY, today=TODAY, now=NOW)

    assert error.value.field == "due_date"


def test_a_task_that_is_already_overdue_can_still_be_edited() -> None:
    task = make_task(due_date=LAST_WEEK)

    task.edit(title="New title", description="More notes", today=TODAY, now=NOW)

    assert (task.title, task.description, task.due_date) == ("New title", "More notes", LAST_WEEK)


def test_resending_the_current_past_due_date_is_not_setting_a_new_one() -> None:
    task = make_task(due_date=LAST_WEEK)

    task.edit(title="New title", due_date=LAST_WEEK, today=TODAY, now=NOW)

    assert task.due_date == LAST_WEEK


def test_moving_a_past_due_date_to_another_past_date_is_rejected() -> None:
    with pytest.raises(DomainValidationError):
        make_task(due_date=LAST_WEEK).edit(due_date=YESTERDAY, today=TODAY, now=NOW)


def test_a_failed_edit_changes_nothing() -> None:
    task = make_task(title="Old title", due_date=TOMORROW)
    before = replace(task)

    with pytest.raises(DomainValidationError):
        task.edit(title="New title", due_date=YESTERDAY, today=TODAY, now=NOW)

    assert task == before


def test_editing_sets_updated_at_and_keeps_everything_else() -> None:
    task = make_task(status=Status.IN_PROGRESS, assignee_id=ASSIGNEE_ID)

    task.edit(title="New title", today=TODAY, now=NOW)

    assert task.updated_at == NOW
    assert task.created_at == EARLIER
    assert (task.owner_id, task.assignee_id, task.status) == (
        OWNER_ID,
        ASSIGNEE_ID,
        Status.IN_PROGRESS,
    )


def test_an_edit_with_no_fields_still_counts_as_a_write() -> None:
    task = make_task()

    task.edit(today=TODAY, now=NOW)

    assert task.updated_at == NOW


def test_a_done_task_can_be_edited() -> None:
    task = make_task(status=Status.DONE, completed_at=EARLIER)

    task.edit(title="New title", today=TODAY, now=NOW)

    assert (task.title, task.status) == ("New title", Status.DONE)
