"""Create a task (spec section 3: any signed-in user, with or without an assignee)."""

from datetime import date

from tasks.application.ports import Clock, Notifier, TaskRepository, UserLookup
from tasks.domain.actor import Actor
from tasks.domain.assignment import assignment_email_due
from tasks.domain.task import Task


class CreateTask:
    """The actor becomes the owner. A different assignee gets the assignment email."""

    def __init__(
        self, tasks: TaskRepository, users: UserLookup, notifier: Notifier, clock: Clock
    ) -> None:
        self._tasks = tasks
        self._users = users
        self._notifier = notifier
        self._clock = clock

    def execute(
        self,
        actor: Actor,
        *,
        title: str,
        description: str = "",
        due_date: date | None = None,
        assignee_id: int | None = None,
    ) -> Task:
        new_task = Task.create(
            title=title,
            description=description,
            due_date=due_date,
            owner_id=actor.id,
            assignee_id=assignee_id,
            assignee_is_active=assignee_id is not None and self._users.is_active_user(assignee_id),
            today=self._clock.today(),
            now=self._clock.now(),
        )
        task = self._tasks.add(new_task)
        assert task.id is not None, "TaskRepository.add() returns the task with its id"
        # The None check only narrows the type for task_assigned; the domain rule decides.
        if assignee_id is not None and assignment_email_due(
            previous_assignee_id=None, new_assignee_id=assignee_id, changed_by_id=actor.id
        ):
            self._notifier.task_assigned(task_id=task.id, assignee_id=assignee_id)
        return task
