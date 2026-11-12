"""The UserLookup port on the Django user model."""

from django.contrib.auth import get_user_model


class DjangoUserLookup:
    """Answers what the rules need to know about users, in one query each."""

    def is_active_user(self, user_id: int) -> bool:
        """True only if a user with this id exists and is active."""
        return get_user_model().objects.filter(pk=user_id, is_active=True).exists()
