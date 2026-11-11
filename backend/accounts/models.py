from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """The project's user.

    A custom model from the first migration, so fields can be added later
    without swapping AUTH_USER_MODEL on a live database.
    """
