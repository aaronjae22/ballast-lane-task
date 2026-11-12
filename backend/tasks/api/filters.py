"""The task list filters (spec section 5), applied to the queryset from visible_tasks(user).

Filters only narrow the queryset they're given, so they can't widen what a user sees. An
invalid value is a form error (a 400) and an empty value leaves a filter off (ADR 0013).
Ordering is a filter too, so an unknown ordering is a 400 like any other (ADR 0014).
"""

from collections.abc import Sequence

from django import forms
from django.db.models import Case, F, IntegerField, QuerySet, Value, When
from django.db.models.expressions import OrderBy
from django.http import HttpRequest, QueryDict
from django_filters import fields
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema_field

from tasks.application.ports import Clock
from tasks.domain.status import Status
from tasks.infrastructure.clock import DjangoClock
from tasks.models import STATUS_CHOICES, Task
from tasks.selectors import overdue

ME = "me"
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


# Status in workflow order, which is Status's declaration order: to_do, in_progress, done.
_STATUS_RANK = Case(
    *(When(status=status.value, then=Value(rank)) for rank, status in enumerate(Status)),
    output_field=IntegerField(),
)
_DEFAULT_ORDERING = ("due_date",)


class _TaskOrdering(filters.OrderingFilter):
    """Orders by the given fields, then by id, so every order is total and pages never overlap.

    Tasks without a due date come last in both directions: Postgres would put them first when
    descending. With no value, the soonest due date comes first.
    """

    def filter(self, qs: QuerySet[Task], value: Sequence[str] | None) -> QuerySet[Task]:
        params = [param for param in value or () if param] or _DEFAULT_ORDERING
        return qs.order_by(*(self._order_by(param) for param in params), "id")

    @staticmethod
    def _order_by(param: str) -> OrderBy:
        name = param.removeprefix("-")
        expression = _STATUS_RANK if name == "status" else F(name)
        if param.startswith("-"):
            return expression.desc(nulls_last=True)
        return expression.asc(nulls_last=True)


_OVERDUE_HELP = "true: due before today and not done. false: everything else."
_OVERDUE_SCHEMA = {"type": "string", "enum": ["false", "true"], "description": _OVERDUE_HELP}


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
        help_text=_OVERDUE_HELP,
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
    ordering = _TaskOrdering(
        fields=("due_date", "created_at", "status"),
        help_text=(
            "due_date, created_at or status; prefix - for descending, and separate several "
            "with commas: ?ordering=status,-due_date. Tasks without a due date come last, "
            "status sorts as to_do, in_progress, done, and ties go to the oldest task. "
            "Default: due_date."
        ),
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

    # The query string carries "true" or "false". Without this, the schema would take the type
    # from value's hint (bool) and pair it with string choices. An override replaces the enum
    # and the description too, so it repeats them.
    @extend_schema_field(_OVERDUE_SCHEMA)
    def filter_overdue(self, queryset: QuerySet[Task], name: str, value: bool) -> QuerySet[Task]:
        """Task.is_overdue() as a query: due before today and not done. Tested on the same cases."""
        condition = overdue(self._clock.today())
        return queryset.filter(condition) if value else queryset.exclude(condition)

    def filter_assignee(
        self, queryset: QuerySet[Task], name: str, value: str | int
    ) -> QuerySet[Task]:
        """Tasks assigned to the user making the request ("me"), or to the user with this id."""
        if value == ME:
            # "me" is whoever made the request; the view always passes it.
            assert self.request is not None
            value = self.request.user.pk
        return queryset.filter(assignee_id=value)
