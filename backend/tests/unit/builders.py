"""Shared values for unit tests: fixed dates and user ids, so no test reads a clock."""

from datetime import UTC, date, datetime, timedelta

TODAY = date(2026, 11, 11)
YESTERDAY = TODAY - timedelta(days=1)
TOMORROW = TODAY + timedelta(days=1)
NOW = datetime(2026, 11, 11, 15, 30, tzinfo=UTC)

OWNER_ID = 1
ASSIGNEE_ID = 2
