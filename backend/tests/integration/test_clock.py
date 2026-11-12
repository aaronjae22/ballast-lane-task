"""The Clock adapter: "today" is the date in the configured TIME_ZONE (ADR 0012)."""

from datetime import UTC, date, datetime
from unittest import mock

import pytest
from pytest_django import Settings

from tasks.infrastructure.clock import DjangoClock


def test_now_is_timezone_aware() -> None:
    now = DjangoClock().now()

    assert now.tzinfo is not None
    assert now.utcoffset() is not None


@pytest.mark.parametrize(
    ("time_zone", "instant", "local_today"),
    [
        # UTC+14: already the next day here.
        ("Pacific/Kiritimati", datetime(2026, 11, 11, 20, 0, tzinfo=UTC), date(2026, 11, 12)),
        # UTC-8 in November: still the previous day here.
        ("America/Los_Angeles", datetime(2026, 11, 12, 3, 0, tzinfo=UTC), date(2026, 11, 11)),
    ],
    ids=["ahead-of-utc", "behind-utc"],
)
def test_today_is_the_date_in_the_configured_time_zone_not_in_utc(
    settings: Settings, time_zone: str, instant: datetime, local_today: date
) -> None:
    settings.TIME_ZONE = time_zone
    clock = DjangoClock()

    with mock.patch("django.utils.timezone.now", return_value=instant):
        assert clock.now() == instant
        assert clock.today() == local_today
        assert clock.today() != clock.now().date()
