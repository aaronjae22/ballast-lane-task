"""Read queries returning QuerySets. Every task read applies visible_tasks(user) (ADR 0002)."""

from datetime import date

from django.db.models import Q, QuerySet

from accounts.models import User
from tasks.domain.status import Status
from tasks.models import Task

# "Not done", spelled as the statuses it covers so the (status, due_date) index can serve it.
_NOT_DONE = [status.value for status in Status if status is not Status.DONE]


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


def overdue(today: date) -> Q:
    """Task.is_overdue() as a query condition: due before today and not done.

    The overdue filter and the task list's is_overdue both use it, and both are tested on the
    domain's own cases, so the rule and its read-side copy can't drift. The explicit
    IS NOT NULL keeps it false, never NULL, for a task without a due date.
    """
    return Q(due_date__isnull=False, due_date__lt=today, status__in=_NOT_DONE)
