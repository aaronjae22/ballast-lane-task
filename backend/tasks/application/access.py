"""Loading a task for a write, with the permission check every write use case needs."""

from tasks.application.ports import TaskRepository
from tasks.domain.actor import Actor
from tasks.domain.errors import TaskNotFound
from tasks.domain.permissions import Action, check_permission
from tasks.domain.task import Task


def get_task_for(tasks: TaskRepository, actor: Actor, task_id: int, action: Action) -> Task:
    """The task, if the actor may take this action on it.

    Writes load through the repository and check visibility with the domain's can_view (via
    check_permission), which is the same rule the visible_tasks selector applies to reads
    (ADR 0003). A missing task and a task the actor can't see both raise TaskNotFound, so the
    API answers 404 either way. A visible task the actor may not change raises NotAllowed.
    """
    task = tasks.get(task_id)
    if task is None:
        raise TaskNotFound(task_id)
    check_permission(actor, task, action)
    return task
