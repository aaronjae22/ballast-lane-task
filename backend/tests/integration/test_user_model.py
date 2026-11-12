"""The task board's user: who counts as an admin (ADR 0013), and how a user is named (ADR 0014).

The users aren't saved: both rules read only the user's own fields.
"""

import pytest

from accounts.models import User


@pytest.mark.parametrize(
    ("flags", "is_admin"),
    [
        ({"is_staff": True}, True),
        ({"is_staff": True, "is_superuser": True}, True),
        ({"is_superuser": True}, False),
        ({}, False),
    ],
    ids=["staff", "staff-superuser", "superuser-without-staff", "plain-user"],
)
def test_an_admin_is_a_staff_user(flags: dict[str, bool], is_admin: bool) -> None:
    assert User(username="someone", **flags).is_admin is is_admin


@pytest.mark.parametrize(
    ("names", "display_name"),
    [
        ({"first_name": "Ada", "last_name": "Lovelace"}, "Ada Lovelace"),
        ({"first_name": "Ada"}, "Ada"),
        ({"last_name": "Lovelace"}, "Lovelace"),
        ({}, "ada"),
        ({"first_name": "  ", "last_name": " "}, "ada"),
    ],
    ids=["full-name", "first-name-only", "last-name-only", "no-name", "blank-names"],
)
def test_a_user_is_shown_by_full_name_or_else_username(
    names: dict[str, str], display_name: str
) -> None:
    assert User(username="ada", **names).display_name == display_name
