"""How users appear in the API (ADR 0014): always by display_name, the one definition."""

from rest_framework import serializers

from accounts.models import User


class UserSummarySerializer(serializers.ModelSerializer):
    """A user as others see them: in the assignee picker, and as a task's owner or assignee."""

    name = serializers.CharField(source="display_name", read_only=True)

    class Meta:
        model = User
        fields = ("id", "name")


class CurrentUserSerializer(serializers.ModelSerializer):
    """The signed-in user. is_admin lets the frontend show admin actions; the API still checks."""

    name = serializers.CharField(source="display_name", read_only=True)
    is_admin = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "name", "is_admin")
        read_only_fields = fields
