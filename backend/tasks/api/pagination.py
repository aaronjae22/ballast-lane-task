"""Pagination for the task list (spec section 2, ADR 0014)."""

from rest_framework.pagination import PageNumberPagination


class TaskPagination(PageNumberPagination):
    """20 tasks a page, ?page_size= up to 50.

    DRF's own behaviour stands: an invalid page_size falls back to 20, a larger one is capped
    at 50, and a page past the end is 404. The order comes from TaskFilter's ordering, which
    always ends with id, so pages never overlap.
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 50
