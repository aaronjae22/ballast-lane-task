"""The task endpoints (spec section 5).

Reads go through visible_tasks(user), so a task outside the user's visibility is 404, the same
answer as for a missing one (ADR 0003). Each write checks the body's shape, calls one use case
through tasks/api/wiring.py, and returns the task read back through visible_tasks, so writes
and reads return the same shape (ADR 0014).
"""

from typing import Any

from django.db.models import BooleanField, ExpressionWrapper, QuerySet
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.request import Request
from rest_framework.response import Response

from config.openapi import error_responses
from tasks.api import wiring
from tasks.api.filters import TaskFilter
from tasks.api.pagination import TaskPagination
from tasks.api.serializers import TaskCreateSerializer, TaskSerializer, TaskUpdateSerializer
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
        return self._visible_task(self.kwargs["pk"])

    def _visible_task(self, task_id: int) -> Task:
        task = self.get_queryset().filter(pk=task_id).first()
        if task is None:
            raise TaskNotFound(task_id)
        return task

    def _read_back(self, task_id: int | None) -> dict[str, Any]:
        """The task after a write, as a read returns it. The writer can always still see it."""
        assert task_id is not None, "a stored task has an id"
        return self.get_serializer(self._visible_task(task_id)).data

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

    @extend_schema(
        summary="Create a task",
        description="Any signed-in user can create a task, and becomes its owner. Assigning "
        "someone else notifies them.",
        request=TaskCreateSerializer,
        responses={201: TaskSerializer, **error_responses(400, 401, 429)},
    )
    def create(self, request: Request) -> Response:
        body = TaskCreateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        task = wiring.create_task(request.user, **body.validated_data)
        return Response(self._read_back(task.id), status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Edit a task",
        description="Change the title, description or due date; fields left out keep their "
        "value. The owner or an admin only. Status and assignee have their own endpoints.",
        request=TaskUpdateSerializer,
        responses={200: TaskSerializer, **error_responses(400, 401, 403, 404, 429)},
    )
    def partial_update(self, request: Request, pk: int) -> Response:
        body = TaskUpdateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        task = wiring.update_task(request.user, pk, **body.validated_data)
        return Response(self._read_back(task.id))

    @extend_schema(
        summary="Delete a task",
        description="The owner or an admin only. It's gone for good: there's no archive.",
        responses={
            204: OpenApiResponse(description="Deleted."),
            **error_responses(401, 403, 404, 429),
        },
    )
    def destroy(self, request: Request, pk: int) -> Response:
        wiring.delete_task(request.user, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)
