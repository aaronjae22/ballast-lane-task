"""Project-level views that don't belong to a feature app."""

from django.db import DatabaseError, connection
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def health(request: Request) -> Response:
    """Liveness for Docker and Cloud Run: 200 if the database answers, else 503."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DatabaseError:
        return Response({"status": "unavailable"}, status=503)
    return Response({"status": "ok"})
