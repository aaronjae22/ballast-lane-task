"""The task list filters (spec section 5), applied to the queryset from visible_tasks(user).

Filters only narrow the queryset they're given, so they can't widen what a user sees. An
invalid value is a form error (400 from iteration 3) and an empty value leaves a filter off
(ADR 0013). Ordering and pagination come with the view in iteration 3.
"""

from collections.abc import Sequence

from django import forms
from django.db.models import Q, QuerySet
from django.http import HttpRequest, QueryDict
from django_filters import fields
from django_filters import rest_framework as filters

from tasks.application.ports import Clock
from tasks.domain.status import Status
from tasks.infrastructure.clock import DjangoClock
from tasks.models import STATUS_CHOICES, Task

ME = "me"
# Overdue's "not done", spelled as the statuses it covers so (status, due_date) can serve it.
_NOT_DONE = [status.value for status in Status if status is not Status.DONE]
# User ids are BigAutoField. Checking the length first keeps a huge string away from int(),
# which refuses more than 4,300 digits with a ValueError instead of a form error.
_LARGEST_USER_ID = 2**63 - 1
_MAX_ID_DIGITS = len(str(_LARGEST_USER_ID))


class _MultipleChoiceIgnoringBlanks(fields.MultipleChoiceField):
    """Drops blank values first, so ?status= means no filter rather than an invalid choice."""

    def clean(self, value: Sequence[str] | None) -> list[str]:
        return super().clean([item for item in value or () if item])


class _StatusFilter(filters.MultipleChoiceFilter):
    field_class = _MultipleChoiceIgnoringBlanks


class _AssigneeField(forms.CharField):
    """Exactly "me", or an int that can be a user id. Empty means no filter."""

    def to_python(self, value: str | None) -> str | int | None:
        text = super().to_python(value)
        if text in self.empty_values:
            return None
        if text == ME:
            return ME
        if (
            text.isascii()
            and text.isdigit()
            and len(text) <= _MAX_ID_DIGITS
            and 0 < int(text) <= _LARGEST_USER_ID
        ):
            return int(text)
        raise forms.ValidationError('Use "me" or a user id.', code="invalid")


class _AssigneeFilter(filters.CharFilter):
    field_class = _AssigneeField


class TaskFilter(filters.FilterSet):
    status = _StatusFilter(
        choices=STATUS_CHOICES,
        help_text="One or more statuses, as repeated parameters: ?status=to_do&status=done.",
    )
    due_after = filters.DateFilter(
        field_name="due_date",
        lookup_expr="gte",
        help_text="Due on or after this date (YYYY-MM-DD). Tasks without a due date never match.",
    )
    due_before = filters.DateFilter(
        field_name="due_date",
        lookup_expr="lte",
        help_text="Due on or before this date (YYYY-MM-DD). Tasks without a due date never match.",
    )
    # A strict two-value choice: BooleanFilter would silently ignore ?overdue=yes (ADR 0013).
    overdue = filters.TypedChoiceFilter(
        choices=(("true", "true"), ("false", "false")),
        coerce=lambda value: value == "true",
        method="filter_overdue",
        help_text="true: due before today and not done. false: everything else.",
    )
    assignee = _AssigneeFilter(
        method="filter_assignee",
        help_text='"me" for your own tasks, or a user id.',
    )
    search = filters.CharFilter(
        field_name="title",
        lookup_expr="icontains",
        help_text="Part of the title, ignoring case.",
    )

    class Meta:
        model = Task
        fields = ()

    def __init__(
        self,
        data: QueryDict | None = None,
        queryset: QuerySet[Task] | None = None,
        *,
        request: HttpRequest | None = None,
        prefix: str | None = None,
        clock: Clock | None = None,
    ) -> None:
        """As django-filter's FilterSet, plus the clock that says what "today" is for overdue.

        The view passes none and gets the real clock; tests pass a fixed one.
        """
        super().__init__(data, queryset, request=request, prefix=prefix)
        self._clock = clock or DjangoClock()

    def filter_overdue(self, queryset: QuerySet[Task], name: str, value: bool) -> QuerySet[Task]:
        """Task.is_overdue() as a query: due before today and not done. Tested on the same cases."""
        overdue = Q(due_date__lt=self._clock.today(), status__in=_NOT_DONE)
        return queryset.filter(overdue) if value else queryset.exclude(overdue)

    def filter_assignee(
        self, queryset: QuerySet[Task], name: str, value: str | int
    ) -> QuerySet[Task]:
        """Tasks assigned to the user making the request ("me"), or to the user with this id."""
        if value == ME:
            # "me" is whoever made the request; the view always passes it.
            assert self.request is not None
            value = self.request.user.pk
        return queryset.filter(assignee_id=value)
