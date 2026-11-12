"""The Task table. Storage only: the rules live in tasks/domain/ (ADR 0002).

Writes go through the use cases and the ORM repository, which maps this model to the domain
Task. created_at and updated_at have no auto_now: the domain sets them (ADR 0012).
"""

from django.conf import settings
from django.db import models

from tasks.domain.status import Status
from tasks.domain.task import TITLE_MAX_LENGTH

STATUS_CHOICES = [(status.value, status.value.replace("_", " ").capitalize()) for status in Status]


class Task(models.Model):
    title = models.CharField(max_length=TITLE_MAX_LENGTH)
    description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=Status.TO_DO.value)
    due_date = models.DateField(null=True, blank=True)
    # PROTECT: users are deactivated, not deleted, so tasks only change through use cases
    # (ADR 0013). Django indexes every foreign key, so these two need no Meta index.
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="owned_tasks"
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="assigned_tasks",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        # For the status, due-date and overdue filters (spec section 13).
        indexes = (models.Index(fields=["status", "due_date"], name="tasks_task_status_due_idx"),)

    def __str__(self) -> str:
        return self.title
