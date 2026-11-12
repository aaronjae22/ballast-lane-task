"""Start, complete and reopen a task (spec section 5: POST .../start/, /complete/, /reopen/)."""

from abc import ABC, abstractmethod
from datetime import datetime

from tasks.application.access import get_task_for
from tasks.application.ports import Clock, TaskRepository
from tasks.domain.actor import Actor
from tasks.domain.permissions import Action
from tasks.domain.task import Task


class _StatusChange(ABC):
    """Owner, assignee or admin. Access is checked before the transition (404 before 409)."""

    def __init__(self, tasks: TaskRepository, clock: Clock) -> None:
        self._tasks = tasks
        self._clock = clock

    def execute(self, actor: Actor, task_id: int) -> Task:
        task = get_task_for(self._tasks, actor, task_id, Action.CHANGE_STATUS)
        self._apply(task, self._clock.now())
        self._tasks.save(task)
        return task

    @abstractmethod
    def _apply(self, task: Task, now: datetime) -> None:
        """Run this use case's transition on the task."""


class StartTask(_StatusChange):
    """to_do -> in_progress."""

    def _apply(self, task: Task, now: datetime) -> None:
        task.start(now=now)


class CompleteTask(_StatusChange):
    """to_do or in_progress -> done; sets completed_at."""

    def _apply(self, task: Task, now: datetime) -> None:
        task.complete(now=now)


class ReopenTask(_StatusChange):
    """done -> to_do; clears completed_at."""

    def _apply(self, task: Task, now: datetime) -> None:
        task.reopen(now=now)
