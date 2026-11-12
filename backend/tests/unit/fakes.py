"""In-memory fakes for the application ports, for unit tests (no database)."""

from collections.abc import Iterable
from dataclasses import replace
from datetime import date, datetime

from tasks.domain.task import Task


class InMemoryTaskRepository:
    """A TaskRepository in a dict.

    It stores and returns copies, so a change a use case makes without calling save() is
    lost, as it would be with the real database.
    """

    def __init__(self, *tasks: Task) -> None:
        self._tasks: dict[int, Task] = {}
        for task in tasks:
            assert task.id is not None, "seed tasks need an id"
            self._tasks[task.id] = replace(task)
        self._next_id = max(self._tasks, default=0) + 1

    def get(self, task_id: int) -> Task | None:
        task = self._tasks.get(task_id)
        return None if task is None else replace(task)

    def add(self, task: Task) -> Task:
        assert task.id is None, "add() is for new tasks"
        stored = replace(task, id=self._next_id)
        self._tasks[self._next_id] = stored
        self._next_id += 1
        return replace(stored)

    def save(self, task: Task) -> None:
        assert task.id in self._tasks, "save() is for stored tasks"
        self._tasks[task.id] = replace(task)

    def delete(self, task_id: int) -> None:
        del self._tasks[task_id]

    def all(self) -> list[Task]:
        """Every stored task, for assertions."""
        return [replace(task) for task in self._tasks.values()]


class FakeUserLookup:
    """A UserLookup where only the given ids are active users."""

    def __init__(self, active_user_ids: Iterable[int]) -> None:
        self._active = frozenset(active_user_ids)

    def is_active_user(self, user_id: int) -> bool:
        return user_id in self._active


class RecordingNotifier:
    """A Notifier that records each assignment as (task_id, assignee_id)."""

    def __init__(self) -> None:
        self.assignments: list[tuple[int, int]] = []

    def task_assigned(self, *, task_id: int, assignee_id: int) -> None:
        self.assignments.append((task_id, assignee_id))


class FixedClock:
    """A Clock stopped at the given moment and date."""

    def __init__(self, *, now: datetime, today: date) -> None:
        self._now = now
        self._today = today

    def now(self) -> datetime:
        return self._now

    def today(self) -> date:
        return self._today
