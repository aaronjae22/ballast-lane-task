from drf_spectacular.openapi import AutoSchema
from rest_framework.permissions import IsAuthenticated
from rest_framework.settings import api_settings
from rest_framework_simplejwt.authentication import JWTAuthentication


def test_endpoints_require_a_jwt_by_default() -> None:
    authentication = api_settings.DEFAULT_AUTHENTICATION_CLASSES
    permissions = api_settings.DEFAULT_PERMISSION_CLASSES

    assert authentication == [JWTAuthentication]
    assert permissions == [IsAuthenticated]


def test_schema_is_generated_by_drf_spectacular() -> None:
    assert api_settings.DEFAULT_SCHEMA_CLASS is AutoSchema
