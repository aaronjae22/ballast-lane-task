"""UserLookup on the user table: only an existing, active user counts (spec section 3)."""

import pytest
from django.db.models import Max

from accounts.models import User
from tasks.infrastructure.users import DjangoUserLookup
from tests.conftest import MakeUser

pytestmark = pytest.mark.django_db


def test_an_active_user_is_active(owner: User) -> None:
    assert DjangoUserLookup().is_active_user(owner.pk) is True


def test_an_inactive_user_is_not(make_user: MakeUser) -> None:
    deactivated = make_user("deactivated", is_active=False)

    assert DjangoUserLookup().is_active_user(deactivated.pk) is False


def test_an_unknown_id_is_not(owner: User) -> None:
    unknown_id = User.objects.aggregate(highest=Max("pk"))["highest"] + 1

    assert DjangoUserLookup().is_active_user(unknown_id) is False
