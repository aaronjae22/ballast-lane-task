"""Creating a task: the field rules in spec section 3."""

from datetime import date

import pytest
from tasks.domain.errors import DomainValidationError
from tasks.domain.status import Status
from tasks.domain.task import TITLE_MAX_LENGTH, Task

from tests.unit.builders import ASSIGNEE_ID, NOW, OWNER_ID, TODAY, TOMORROW, YESTERDAY


def create(**overrides: object) -> Task:
    fields: dict[str, object] = {
        "title": "Write the spec",
        "owner_id": OWNER_ID,
        "today": TODAY,
        "now": NOW,
    }
    return Task.create(**(fields | overrides))


def test_the_statuses_are_the_ones_the_spec_names() -> None:
    assert [status.value for status in Status] == ["to_do", "in_progress", "done"]


def test_a_new_task_is_to_do_owned_by_its_creator_and_not_yet_saved() -> None:
    task = create()

    assert task.id is None
    assert task.title == "Write the spec"
    assert task.description == ""
    assert task.status is Status.TO_DO
    assert task.due_date is None
    assert task.owner_id == OWNER_ID
    assert task.assignee_id is None
    assert task.completed_at is None
    assert task.created_at == NOW
    assert task.updated_at == NOW


def test_a_new_task_keeps_its_description() -> None:
    assert create(description="Sections 3 and 4").description == "Sections 3 and 4"


@pytest.mark.parametrize("length", [1, TITLE_MAX_LENGTH])
def test_a_title_of_1_to_200_characters_is_accepted(length: int) -> None:
    assert create(title="x" * length).title == "x" * length


@pytest.mark.parametrize(
    "title",
    ["", "   ", "x" * (TITLE_MAX_LENGTH + 1)],
    ids=["empty", "whitespace-only", "201-characters"],
)
def test_an_empty_blank_or_too_long_title_is_rejected(title: str) -> None:
    with pytest.raises(DomainValidationError) as error:
        create(title=title)

    assert error.value.field == "title"


def test_the_title_is_stripped_before_its_length_is_checked() -> None:
    task = create(title="  " + "x" * TITLE_MAX_LENGTH + "\n")

    assert task.title == "x" * TITLE_MAX_LENGTH


@pytest.mark.parametrize("due_date", [TODAY, TOMORROW, None], ids=["today", "tomorrow", "none"])
def test_a_due_date_of_today_or_later_or_none_is_accepted(due_date: date | None) -> None:
    assert create(due_date=due_date).due_date == due_date


def test_a_due_date_in_the_past_is_rejected() -> None:
    with pytest.raises(DomainValidationError) as error:
        create(due_date=YESTERDAY)

    assert error.value.field == "due_date"


@pytest.mark.parametrize("assignee_id", [ASSIGNEE_ID, OWNER_ID], ids=["someone-else", "self"])
def test_a_new_task_can_have_an_active_assignee(assignee_id: int) -> None:
    task = create(assignee_id=assignee_id, assignee_is_active=True)

    assert task.assignee_id == assignee_id


def test_an_assignee_who_isnt_an_active_user_is_rejected() -> None:
    with pytest.raises(DomainValidationError) as error:
        create(assignee_id=ASSIGNEE_ID, assignee_is_active=False)

    assert error.value.field == "assignee_id"
