"""Tasks in Django admin, read-only and scoped by visible_tasks.

The admin saves straight to the model, which would skip every rule in tasks/domain/; writes go
through the use cases (ADR 0002). So it lists, searches and filters, and never adds, changes or
deletes. Without delete permission, the bulk-delete action disappears too. Like every task read,
it goes through visible_tasks(user), so it follows the one definition of who sees what.
"""

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from tasks.models import Task
from tasks.selectors import visible_tasks


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "status", "due_date", "owner", "assignee", "updated_at")
    list_filter = ("status", "due_date")
    search_fields = ("title", "owner__username", "assignee__username")

    def get_queryset(self, request: HttpRequest) -> QuerySet[Task]:
        """The tasks this user may see. The selector also joins in owner and assignee."""
        return visible_tasks(request.user)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Task | None = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Task | None = None) -> bool:
        return False
