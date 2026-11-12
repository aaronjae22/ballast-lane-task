"""Logging in, refreshing and logging out (spec section 6, ADRs 0006 and 0014).

The access token travels in the response body, for the frontend to keep in memory. The
refresh token travels only in an httpOnly, SameSite=Strict cookie scoped to /api/auth/, so
JavaScript never sees it and the browser sends it nowhere else. These views read no access
token (simplejwt's views have no authentication classes), so an expired one can't block them.
"""

from contextlib import suppress
from typing import Any

from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import exceptions, serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from accounts.models import User
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


class _ParsesTheBodyFirst:
    """Parse the request body before the view runs, even if the view never reads it.

    So a cross-site form post is 415 on the views that read only the cookie too (ADR 0014).
    A request with no body parses to nothing and passes.
    """

    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None:
        super().initial(request, *args, **kwargs)  # type: ignore[misc]
        _ = request.data


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
            # Split request components add "Request": the schema calls it LoginRequest.
            "Login",
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


class RefreshView(_ParsesTheBodyFirst, TokenRefreshView):
    """POST /api/auth/token/refresh/: rotates the cookie and blacklists the old token.

    A failed refresh is 401 and leaves the cookie alone (ADR 0014). Two refreshes sent with
    the same cookie race: the first rotates it, the second fails on the now-blacklisted
    token. If the failure cleared the cookie and arrived last, it would delete the new one.
    """

    @extend_schema(
        summary="Refresh the access token",
        description=(
            "Reads the refresh_token cookie, which the browser sends by itself, and rotates it: "
            "the old token stops working. " + _COOKIE_NOTE + " A failed refresh leaves the "
            "cookie as it was. No request body."
        ),
        request=None,
        responses={
            200: OpenApiResponse(AccessTokenSerializer, description=_COOKIE_NOTE),
            **error_responses(401, 415, 429),
        },
    )
    def post(self, request: Request) -> Response:
        token = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if not token:
            raise exceptions.NotAuthenticated("No refresh token cookie.")
        serializer = self.get_serializer(data={"refresh": token})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as error:
            # Expired, malformed, the wrong type, or already rotated (blacklisted).
            raise InvalidToken(error.args[0]) from error
        except User.DoesNotExist as error:
            # simplejwt looks up the token's user without catching this; the user was deleted.
            raise exceptions.AuthenticationFailed(
                TokenRefreshSerializer.default_error_messages["no_active_account"],
                "no_active_account",
            ) from error
        response = Response({"access": serializer.validated_data["access"]})
        set_refresh_cookie(response, serializer.validated_data["refresh"])
        return response


class LogoutView(_ParsesTheBodyFirst, APIView):
    """POST /api/auth/logout/: blacklists the cookie's refresh token and clears the cookie.

    The client wants to be signed out whatever state its cookie is in, so this always answers
    204 and clears it (ADR 0014). It reads no access token: the cookie is what it revokes.
    The access token isn't revoked; it expires within 5 minutes, and the frontend drops it.
    """

    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        summary="Log out",
        description=(
            "Revokes the refresh token in the refresh_token cookie and clears the cookie. "
            "Always 204, even without a valid cookie. No request body."
        ),
        request=None,
        responses={204: OpenApiResponse(description="Signed out."), **error_responses(415, 429)},
    )
    def post(self, request: Request) -> Response:
        token = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        # Expired, malformed or already revoked: there's nothing left to revoke.
        if token:
            with suppress(TokenError):
                RefreshToken(token).blacklist()
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(
            settings.REFRESH_COOKIE_NAME, path=settings.REFRESH_COOKIE_PATH, samesite="Strict"
        )
        return response
