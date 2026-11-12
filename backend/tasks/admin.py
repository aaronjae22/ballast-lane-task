"""Tasks in Django admin, read-only.

The admin saves straight to the model, which would skip every rule in tasks/domain/; writes go
through the use cases (ADR 0002). So it lists, searches and filters, and never adds, changes or
deletes. Without delete permission, the bulk-delete action disappears too.
"""

from django.contrib import admin
from django.http import HttpRequest

from tasks.models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "status", "due_date", "owner", "assignee", "updated_at")
    list_filter = ("status", "due_date")
    list_select_related = ("owner", "assignee")
    search_fields = ("title", "owner__username", "assignee__username")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Task | None = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Task | None = None) -> bool:
        return False
