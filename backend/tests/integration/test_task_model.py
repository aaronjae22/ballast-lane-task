"""The Task model: columns, indexes and foreign keys (spec sections 3 and 13, ADRs 0012, 0013)."""

import pytest
from django.db import connection
from django.db.models import ProtectedError

from accounts.models import User
from tasks.domain.status import Status
from tasks.domain.task import TITLE_MAX_LENGTH
from tasks.models import Task
from tests.unit.builders import EARLIER

pytestmark = pytest.mark.django_db


def create_row(owner: User, **fields: object) -> Task:
    """A row written straight to the model, as only these tests do (writes use the repository)."""
    return Task.objects.create(
        title="Write the spec", owner=owner, created_at=EARLIER, updated_at=EARLIER, **fields
    )


def indexed_columns() -> list[list[str]]:
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, Task._meta.db_table)
    return [constraint["columns"] for constraint in constraints.values() if constraint["index"]]


@pytest.mark.parametrize(
    "columns",
    [["status", "due_date"], ["owner_id"], ["assignee_id"]],
    ids=["status-due-date", "owner", "assignee"],
)
def test_the_filter_and_visibility_columns_are_indexed(columns: list[str]) -> None:
    assert columns in indexed_columns()


def test_a_user_who_owns_a_task_cannot_be_deleted(owner: User) -> None:
    create_row(owner)

    with pytest.raises(ProtectedError):
        owner.delete()


def test_a_user_assigned_a_task_cannot_be_deleted(owner: User, assignee: User) -> None:
    create_row(owner, assignee=assignee)

    with pytest.raises(ProtectedError):
        assignee.delete()


def test_timestamps_are_stored_as_given_and_left_alone_on_a_later_save(owner: User) -> None:
    row = create_row(owner)
    row.title = "Changed"
    row.save()

    row.refresh_from_db()
    assert (row.created_at, row.updated_at) == (EARLIER, EARLIER)


def test_a_new_row_is_to_do_with_an_empty_description_and_no_optional_values(
    owner: User,
) -> None:
    row = create_row(owner)

    row.refresh_from_db()
    assert row.status == Status.TO_DO
    assert row.description == ""
    assert (row.due_date, row.assignee, row.completed_at) == (None, None, None)


def test_the_status_choices_are_the_domain_statuses() -> None:
    choices = Task._meta.get_field("status").choices

    assert [value for value, _label in choices] == [status.value for status in Status]


def test_the_title_length_limit_is_the_domains() -> None:
    assert Task._meta.get_field("title").max_length == TITLE_MAX_LENGTH
