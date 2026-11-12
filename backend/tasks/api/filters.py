"""The task list filters (spec section 5), applied to the queryset from visible_tasks(user).

Filters only narrow the queryset they're given, so they can't widen what a user sees. An
invalid value is a form error (400 from iteration 3) and an empty value leaves a filter off
(ADR 0013). Ordering and pagination come with the view in iteration 3.
"""

from collections.abc import Sequence

from django_filters import fields
from django_filters import rest_framework as filters

from tasks.models import STATUS_CHOICES, Task


class _MultipleChoiceIgnoringBlanks(fields.MultipleChoiceField):
    """Drops blank values first, so ?status= means no filter rather than an invalid choice."""

    def clean(self, value: Sequence[str] | None) -> list[str]:
        return super().clean([item for item in value or () if item])


class _StatusFilter(filters.MultipleChoiceFilter):
    field_class = _MultipleChoiceIgnoringBlanks


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
    search = filters.CharFilter(
        field_name="title",
        lookup_expr="icontains",
        help_text="Part of the title, ignoring case.",
    )

    class Meta:
        model = Task
        fields = ()
