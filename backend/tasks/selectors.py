"""Read queries returning QuerySets. Every task read applies visible_tasks(user) (ADR 0002)."""

from django.db.models import Q, QuerySet

from accounts.models import User
from tasks.models import Task


def visible_tasks(user: User) -> QuerySet[Task]:
    """The tasks this user may see: every task for an admin, else those they own or are assigned.

    The read-side twin of tasks.domain.permissions.can_view() (ADR 0003); both are tested
    against the same permission-matrix row. Owner and assignee are joined in, so listing
    tasks with them takes one query.
    """
    tasks = Task.objects.select_related("owner", "assignee")
    if user.is_admin:
        return tasks.all()
    return tasks.filter(Q(owner=user) | Q(assignee=user))
