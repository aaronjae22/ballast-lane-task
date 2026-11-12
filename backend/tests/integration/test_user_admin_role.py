"""Who counts as an admin on the task board: a staff user (ADR 0013)."""

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
