"""How tasks appear in the API (ADR 0014).

Read side only for now: the write serializers, which check the input's shape and nothing
else, arrive with the write endpoints.
"""

from rest_framework import serializers

from accounts.serializers import UserSummarySerializer
from tasks.models import Task


class TaskSerializer(serializers.ModelSerializer):
    """A task as every endpoint returns it, reads and writes alike."""

    owner = UserSummarySerializer(read_only=True)
    assignee = UserSummarySerializer(read_only=True, allow_null=True)
    is_overdue = serializers.BooleanField(
        read_only=True,
        help_text="Due before today (in the server's time zone) and not done. Never stored.",
    )

    class Meta:
        model = Task
        fields = (
            "id",
            "title",
            "description",
            "status",
            "due_date",
            "is_overdue",
            "owner",
            "assignee",
            "completed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
