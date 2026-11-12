"""Delete a task (spec section 5: DELETE /api/tasks/{id}/)."""

from tasks.application.access import get_task_for
from tasks.application.ports import TaskRepository
from tasks.domain.actor import Actor
from tasks.domain.permissions import Action


class DeleteTask:
    """Owner or admin only. A hard delete: the spec has no archive or soft delete."""

    def __init__(self, tasks: TaskRepository) -> None:
        self._tasks = tasks

    def execute(self, actor: Actor, task_id: int) -> None:
        get_task_for(self._tasks, actor, task_id, Action.DELETE)
        self._tasks.delete(task_id)
