"""Assign, reassign or unassign a task (spec section 5: POST /api/tasks/{id}/assign/)."""

from tasks.application.access import get_task_for
from tasks.application.ports import Clock, Notifier, TaskRepository, UserLookup
from tasks.domain.actor import Actor
from tasks.domain.assignment import assignment_email_due
from tasks.domain.permissions import Action
from tasks.domain.task import Task


class AssignTask:
    """Owner or admin only. The new assignee gets the email when the domain rule says so."""

    def __init__(
        self, tasks: TaskRepository, users: UserLookup, notifier: Notifier, clock: Clock
    ) -> None:
        self._tasks = tasks
        self._users = users
        self._notifier = notifier
        self._clock = clock

    def execute(self, actor: Actor, task_id: int, assignee_id: int | None) -> Task:
        task = get_task_for(self._tasks, actor, task_id, Action.ASSIGN)
        previous_assignee_id = task.assignee_id
        task.assign(
            assignee_id,
            assignee_is_active=assignee_id is not None and self._users.is_active_user(assignee_id),
            now=self._clock.now(),
        )
        self._tasks.save(task)
        # The None check only narrows the type for task_assigned; the domain rule decides.
        if assignee_id is not None and assignment_email_due(
            previous_assignee_id=previous_assignee_id,
            new_assignee_id=assignee_id,
            changed_by_id=actor.id,
        ):
            self._notifier.task_assigned(task_id=task_id, assignee_id=assignee_id)
        return task
