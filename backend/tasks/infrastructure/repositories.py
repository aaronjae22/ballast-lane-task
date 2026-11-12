"""The ORM TaskRepository: domain Tasks stored in the Task table (ADRs 0002, 0012 and 0013)."""

from dataclasses import replace

from tasks import models
from tasks.domain.errors import TaskNotFound
from tasks.domain.status import Status
from tasks.domain.task import Task


class DjangoTaskRepository:
    """The TaskRepository port on the Django ORM.

    It stores the domain's values exactly as given, timestamps included: the model has no
    auto_now. Misuse that the port leaves open is answered as ADR 0013 decides.
    """

    def get(self, task_id: int) -> Task | None:
        """The task with this id, with its row locked until the caller's transaction ends.

        Only the write use cases call get() (reads go through selectors), and each one loads a
        task, changes it and saves it. select_for_update() makes a concurrent write to the same
        task wait for this transaction instead of overwriting its change. So get() must run
        inside a transaction, which the caller holds (ADR 0013): outside one, Django raises
        TransactionManagementError.
        """
        row = models.Task.objects.select_for_update().filter(pk=task_id).first()
        return None if row is None else _to_domain(row)

    def add(self, task: Task) -> Task:
        """Store a new task and return it with its id. A task that has an id isn't new."""
        if task.id is not None:
            raise ValueError(f"add() is for new tasks; this one already has an id ({task.id}).")
        row = models.Task.objects.create(**_to_columns(task))
        return replace(task, id=row.pk)

    def save(self, task: Task) -> None:
        """Store the changes to an existing task.

        An UPDATE, never an INSERT, so a task deleted in the meantime doesn't come back.
        """
        if not models.Task.objects.filter(pk=task.id).update(**_to_columns(task)):
            raise TaskNotFound(task.id)

    def delete(self, task_id: int) -> None:
        """Remove the task with this id. A missing id is left as it is: there's nothing to do."""
        models.Task.objects.filter(pk=task_id).delete()


# The mapping between the model and the domain Task, in one place.


def _to_domain(row: models.Task) -> Task:
    return Task(
        id=row.pk,
        title=row.title,
        description=row.description,
        status=Status(row.status),
        due_date=row.due_date,
        owner_id=row.owner_id,
        assignee_id=row.assignee_id,
        completed_at=row.completed_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_columns(task: Task) -> dict[str, object]:
    """Every stored column except the id, which the database assigns."""
    return {
        "title": task.title,
        "description": task.description,
        "status": task.status.value,
        "due_date": task.due_date,
        "owner_id": task.owner_id,
        "assignee_id": task.assignee_id,
        "completed_at": task.completed_at,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }
