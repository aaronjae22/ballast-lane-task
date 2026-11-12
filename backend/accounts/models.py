from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """The project's user.

    A custom model from the first migration, so fields can be added later
    without swapping AUTH_USER_MODEL on a live database.
    """

    @property
    def is_admin(self) -> bool:
        """An admin of the task board, who sees and manages every task: a staff user.

        The one definition (ADR 0013): visible_tasks reads it, and so does the mapping from a
        user to the domain's Actor. Staff, as for Django admin access and DRF's IsAdminUser.
        """
        return self.is_staff
