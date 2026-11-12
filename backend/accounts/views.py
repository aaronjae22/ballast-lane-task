"""The users endpoints (spec section 5): GET /api/users/ and GET /api/users/me/."""

from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from accounts.models import User
from accounts.serializers import CurrentUserSerializer, UserSummarySerializer
from config.openapi import error_responses


class UserViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Users, for any signed-in user."""

    queryset = User.objects.filter(is_active=True).order_by("username")
    serializer_class = UserSummarySerializer
    # The assignee picker needs every active user of a small team at once (ADR 0014).
    pagination_class = None

    @extend_schema(
        summary="List the active users",
        description="Every active user, by username, for the assignee picker. Not paginated.",
        responses={200: UserSummarySerializer(many=True), **error_responses(401, 429)},
    )
    def list(self, request: Request) -> Response:
        return super().list(request)

    @extend_schema(
        summary="Show the signed-in user",
        responses={200: CurrentUserSerializer, **error_responses(401, 429)},
    )
    @action(detail=False)
    def me(self, request: Request) -> Response:
        return Response(CurrentUserSerializer(request.user).data)
