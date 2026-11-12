"""The Clock port on Django's time zone support (ADR 0012)."""

from datetime import date, datetime

from django.utils import timezone


class DjangoClock:
    """The real clock. The domain never reads one; use cases ask this and pass the values in."""

    def now(self) -> datetime:
        """The current moment, timezone-aware (USE_TZ)."""
        return timezone.now()

    def today(self) -> date:
        """Today in settings.TIME_ZONE. Never now().date(), which is the UTC date."""
        return timezone.localdate()
