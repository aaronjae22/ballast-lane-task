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


def reminder_recipients(day: date) -> QuerySet[User]:
    """Who gets a due-tomorrow digest for this day: one row per user, in id order.

    Active users with an email address who are assigned a task due on the day that isn't
    done. Self-assigned tasks count. A system read for the Beat job, made on no user's behalf,
    so it doesn't go through visible_tasks (ADR 0015): it reads across users, and it returns
    users, not tasks. Each digest reads its tasks through due_on_for_assignee(), which does.
    """
    # One filter() call, so the due date and the status apply to the same task.
    return (
        User.objects.filter(
            is_active=True, assigned_tasks__due_date=day, assigned_tasks__status__in=_NOT_DONE
        )
        .exclude(email="")
        .distinct()
        .order_by("pk")
    )


def due_on_for_assignee(user: User, day: date) -> QuerySet[Task]:
    """The user's digest: tasks assigned to them, due on the day and not done, by title.

    A read on the user's behalf, so it starts from visible_tasks(user), which also joins the
    owner the email shows.
    """
    return (
        visible_tasks(user)
        .filter(assignee=user, due_date=day, status__in=_NOT_DONE)
        .order_by("title", "pk")
    )
