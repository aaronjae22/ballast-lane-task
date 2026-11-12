"""Logging in, refreshing and logging out (spec section 6, ADRs 0006 and 0014).

The access token travels in the response body, for the frontend to keep in memory. The
refresh token travels only in an httpOnly, SameSite=Strict cookie scoped to /api/auth/, so
JavaScript never sees it and the browser sends it nowhere else. These views read no access
token (simplejwt's views have no authentication classes), so an expired one can't block them.
"""

from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.views import TokenObtainPairView

from config.openapi import error_responses


class AccessTokenSerializer(serializers.Serializer):
    access = serializers.CharField(help_text="A JWT valid for 5 minutes. Keep it in memory only.")


_COOKIE_NOTE = (
    "The refresh token is set as the httpOnly refresh_token cookie (Path=/api/auth/), "
    "never returned in the body."
)


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    """Put the refresh token in its cookie, which lasts as long as the token does."""
    response.set_cookie(
        settings.REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=int(jwt_settings.REFRESH_TOKEN_LIFETIME.total_seconds()),
        path=settings.REFRESH_COOKIE_PATH,
        secure=settings.REFRESH_COOKIE_SECURE,
        httponly=True,
        samesite="Strict",
    )


class LoginView(TokenObtainPairView):
    """POST /api/auth/token/, limited to 5 attempts a minute (the auth throttle scope)."""

    throttle_scope = "auth"

    @extend_schema(
        summary="Log in",
        description=(
            "Exchange a username and password for an access token. " + _COOKIE_NOTE + " A "
            "wrong password, an unknown user and an inactive user all get the same 401."
        ),
        request=inline_serializer(
            "LoginRequest",
            {
                "username": serializers.CharField(),
                "password": serializers.CharField(style={"input_type": "password"}),
            },
        ),
        responses={
            200: OpenApiResponse(AccessTokenSerializer, description=_COOKIE_NOTE),
            **error_responses(400, 401, 429),
        },
    )
    def post(self, request: Request) -> Response:
        # Bad credentials raise AuthenticationFailed (401) and missing fields a ValidationError
        # (400). Making a token for a user who passed can't fail, unlike reading one.
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response = Response({"access": serializer.validated_data["access"]})
        set_refresh_cookie(response, serializer.validated_data["refresh"])
        return response
