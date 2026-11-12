from drf_spectacular.openapi import AutoSchema
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.settings import api_settings
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle, UserRateThrottle
from rest_framework_simplejwt.authentication import JWTAuthentication


def test_endpoints_require_a_jwt_by_default() -> None:
    authentication = api_settings.DEFAULT_AUTHENTICATION_CLASSES
    permissions = api_settings.DEFAULT_PERMISSION_CLASSES

    assert authentication == [JWTAuthentication]
    assert permissions == [IsAuthenticated]


def test_schema_is_generated_by_drf_spectacular() -> None:
    assert api_settings.DEFAULT_SCHEMA_CLASS is AutoSchema


def test_the_api_reads_and_writes_json_only() -> None:
    """No browsable API, and no form parsers for a cross-site form to post to (ADR 0014)."""
    renderers = api_settings.DEFAULT_RENDERER_CLASSES
    parsers = api_settings.DEFAULT_PARSER_CLASSES

    assert renderers == [JSONRenderer]
    assert parsers == [JSONParser]


def test_every_endpoint_is_throttled_at_the_rates_in_spec_section_7() -> None:
    throttles = api_settings.DEFAULT_THROTTLE_CLASSES
    rates = api_settings.DEFAULT_THROTTLE_RATES

    assert throttles == [AnonRateThrottle, UserRateThrottle, ScopedRateThrottle]
    assert rates == {
        "anon": "30/min",
        "user": "120/min",
        "auth": "5/min",
    }
