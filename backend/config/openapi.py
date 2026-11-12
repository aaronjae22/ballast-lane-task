"""Shared parts of the OpenAPI schema: what an error response looks like (ADR 0014).

A 400 maps each field to its messages, whether the input had the wrong shape or broke a
domain rule. Every other error is {"detail": "..."}. Both are what DRF's exception handler
gives.
"""

from drf_spectacular.utils import OpenApiResponse
from rest_framework import serializers


class ErrorSerializer(serializers.Serializer):
    detail = serializers.CharField(help_text="What went wrong, for a person to read.")


# {"field": ["message", ...]}. A raw schema, because a serializer can't say "any field name".
FIELD_ERRORS = {
    "type": "object",
    "additionalProperties": {"type": "array", "items": {"type": "string"}},
}

_DESCRIPTIONS = {
    400: "The input is invalid. Each field maps to its messages.",
    401: "No access token, or one that has expired or is otherwise invalid.",
    403: "You can see the task but may not do this to it.",
    404: "No such task, or one you can't see.",
    409: "The task's status doesn't allow this action.",
    415: "The body isn't JSON. The API reads JSON only, so an HTML form can't post to it.",
    429: "Too many requests. The Retry-After header says how many seconds to wait.",
}


def error_responses(*codes: int) -> dict[int, OpenApiResponse]:
    """The documented error responses for an endpoint, by status code."""
    return {
        code: OpenApiResponse(
            FIELD_ERRORS if code == 400 else ErrorSerializer, description=_DESCRIPTIONS[code]
        )
        for code in codes
    }
