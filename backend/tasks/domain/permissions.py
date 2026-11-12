"""Who may do what to a task: the permission matrix in spec section 3 (ADR 0003)."""

from enum import StrEnum

from tasks.domain.actor import Actor
from tasks.domain.errors import NotAllowed, TaskNotFound
from tasks.domain.task import Task


class Action(StrEnum):
    """The rows of the permission matrix. Start, complete and reopen share one rule."""

    VIEW = "view"
    EDIT = "edit"
    ASSIGN = "assign"
    CHANGE_STATUS = "change_status"
    DELETE = "delete"


# The owner and admins may take every action; the assignee only these.
_ASSIGNEE_ACTIONS = frozenset({Action.VIEW, Action.CHANGE_STATUS})


def can_view(actor: Actor, task: Task) -> bool:
    """The owner, the assignee and admins see a task; nobody else does.

    The visible_tasks selector applies the same rule to reads (iteration 2).
    """
    return actor.is_admin or actor.id in (task.owner_id, task.assignee_id)


def check_permission(actor: Actor, task: Task, action: Action) -> None:
    """Return if the actor may take the action, else raise.

    A task the actor can't see raises TaskNotFound for every action, so the API answers 404
    without revealing that the task exists. A visible task they may not change raises
    NotAllowed (403).
    """
    if not can_view(actor, task):
        raise TaskNotFound(task.id)
    if actor.is_admin or actor.id == task.owner_id:
        return
    if action not in _ASSIGNEE_ACTIONS:
        raise NotAllowed(f"Only the task's owner or an admin can {action.value.replace('_', ' ')}.")
