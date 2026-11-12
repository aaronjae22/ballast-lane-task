"""Edit a task's title, description or due date (spec section 5: PATCH)."""

from datetime import date

from tasks.application.access import get_task_for
from tasks.application.ports import Clock, TaskRepository
from tasks.domain.actor import Actor
from tasks.domain.permissions import Action
from tasks.domain.task import UNSET, Task, Unset


class UpdateTask:
    """Owner or admin only. Status and assignee have their own use cases (ADR 0004)."""

    def __init__(self, tasks: TaskRepository, clock: Clock) -> None:
        self._tasks = tasks
        self._clock = clock

    def execute(
        self,
        actor: Actor,
        task_id: int,
        *,
        title: str | Unset = UNSET,
        description: str | Unset = UNSET,
        due_date: date | Unset | None = UNSET,
    ) -> Task:
        task = get_task_for(self._tasks, actor, task_id, Action.EDIT)
        task.edit(
            title=title,
            description=description,
            due_date=due_date,
            today=self._clock.today(),
            now=self._clock.now(),
        )
        self._tasks.save(task)
        return task
