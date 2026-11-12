"""The task endpoints (spec section 5).

Reads go through visible_tasks(user), so a task outside the user's visibility is 404, the same
answer as for a missing one (ADR 0003). Writes go through tasks/api/wiring.py, one use case
per endpoint, and arrive in later commits.
"""

from django.db.models import BooleanField, ExpressionWrapper, QuerySet
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.request import Request
from rest_framework.response import Response

from config.openapi import error_responses
from tasks.api.filters import TaskFilter
from tasks.api.pagination import TaskPagination
from tasks.api.serializers import TaskSerializer
from tasks.domain.errors import TaskNotFound
from tasks.infrastructure.clock import DjangoClock
from tasks.models import Task
from tasks.selectors import overdue, visible_tasks


class TaskViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = TaskSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = TaskFilter
    pagination_class = TaskPagination
    # <int:pk>: an id that isn't a number, or is too long to be one, matches no route.
    lookup_value_converter = "int"

    def get_queryset(self) -> QuerySet[Task]:
        """The tasks this user may see, each with is_overdue judged on today's date."""
        if getattr(self, "swagger_fake_view", False):
            # Schema generation has no signed-in user; it only needs the model.
            return Task.objects.none()
        is_overdue = ExpressionWrapper(overdue(DjangoClock().today()), output_field=BooleanField())
        return visible_tasks(self.request.user).annotate(is_overdue=is_overdue)

    def get_object(self) -> Task:
        """The task, if this user may see it. The list's filters don't apply here.

        Missing and not visible raise the same TaskNotFound as the write use cases, so every
        404 for a task has the same body.
        """
        task_id = self.kwargs["pk"]
        task = self.get_queryset().filter(pk=task_id).first()
        if task is None:
            raise TaskNotFound(task_id)
        return task

    @extend_schema(
        summary="List tasks",
        description="The tasks you own or are assigned to (every task, for an admin), a page "
        "at a time, filtered and ordered by the query parameters.",
        responses={200: TaskSerializer(many=True), **error_responses(400, 401, 404, 429)},
    )
    def list(self, request: Request) -> Response:
        return super().list(request)

    @extend_schema(
        summary="Show a task",
        responses={200: TaskSerializer, **error_responses(401, 404, 429)},
    )
    def retrieve(self, request: Request, pk: int) -> Response:
        return Response(self.get_serializer(self.get_object()).data)
