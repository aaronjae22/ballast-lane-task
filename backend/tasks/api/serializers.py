"""How tasks appear in the API, and what the write endpoints accept (ADRs 0012 and 0014).

The write serializers check only the input's shape: types, required fields, unknown fields.
The rules (title length after trimming, no past due date, an active assignee) are the
domain's. The use cases raise them as DomainValidationError, a 400 keyed by the same field
names, so the two kinds of error look alike and there's only one copy of each rule.
"""

from collections.abc import Mapping
from typing import Any

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


class RejectUnknownFields(serializers.Serializer):
    """A field the endpoint doesn't take is a 400, not silently dropped (ADR 0014).

    Otherwise PATCH {"status": "done"} would answer 200 and change nothing.
    """

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        if isinstance(data, Mapping) and (unknown := set(data) - set(self.fields)):
            errors = {name: ["Unknown field."] for name in sorted(unknown)}
            raise serializers.ValidationError(errors)
        return super().to_internal_value(data)


class TaskCreateSerializer(RejectUnknownFields):
    """POST /api/tasks/. Fields left out get CreateTask's defaults."""

    # No trimming or length limit here: the domain trims and then checks 1 to 200 (ADR 0012).
    title = serializers.CharField(
        trim_whitespace=False,
        allow_blank=True,
        help_text="1 to 200 characters. Surrounding spaces are removed first.",
    )
    description = serializers.CharField(required=False, trim_whitespace=False, allow_blank=True)
    due_date = serializers.DateField(
        required=False, allow_null=True, help_text="Today or later. null or left out: none."
    )
    assignee_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="An active user's id, from /api/users/. null or left out: unassigned.",
    )


class TaskUpdateSerializer(RejectUnknownFields):
    """PATCH /api/tasks/{id}/: only the title, description and due date (ADR 0004).

    Every field is optional. One left out never reaches validated_data, so UpdateTask gets
    UNSET for it and keeps its value; an explicit null due date clears it.
    """

    title = serializers.CharField(
        required=False,
        trim_whitespace=False,
        allow_blank=True,
        help_text="1 to 200 characters. Surrounding spaces are removed first.",
    )
    description = serializers.CharField(required=False, trim_whitespace=False, allow_blank=True)
    due_date = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="null clears it. A new date can't be in the past; re-sending the current "
        "one is always fine, so an overdue task stays editable.",
    )


class AssignSerializer(RejectUnknownFields):
    """POST /api/tasks/{id}/assign/. The key is required, so an empty body isn't an unassign."""

    assignee_id = serializers.IntegerField(
        allow_null=True,
        help_text="An active user's id, from /api/users/, or null to unassign.",
    )


class NoBodySerializer(RejectUnknownFields):
    """start, complete and reopen take no body: any field sent is a 400, not ignored."""
