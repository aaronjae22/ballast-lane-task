"""Shared parts of the OpenAPI schema: what an error response looks like (ADR 0014).

Every error except a 400 is {"detail": "..."}, the shape DRF's exception handler gives.
"""

from drf_spectacular.utils import OpenApiResponse
from rest_framework import serializers


class ErrorSerializer(serializers.Serializer):
    detail = serializers.CharField(help_text="What went wrong, for a person to read.")


_DESCRIPTIONS = {
    401: "No access token, or one that has expired or is otherwise invalid.",
    403: "You can see the task but may not do this to it.",
    404: "No such task, or one you can't see.",
    409: "The task's status doesn't allow this action.",
    429: "Too many requests. The Retry-After header says how many seconds to wait.",
}


def error_responses(*codes: int) -> dict[int, OpenApiResponse]:
    """The documented error responses for an endpoint, by status code."""
    return {
        code: OpenApiResponse(ErrorSerializer, description=_DESCRIPTIONS[code]) for code in codes
    }
