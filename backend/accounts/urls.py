"""URLs of the accounts app, under /api/."""

from django.urls import path
from rest_framework.routers import SimpleRouter

from accounts.auth_views import LoginView, LogoutView, RefreshView
from accounts.views import UserViewSet

# SimpleRouter, not DefaultRouter: no API root view, and the tasks routes share the prefix.
router = SimpleRouter(use_regex_path=False)
router.register("users", UserViewSet, basename="user")

urlpatterns = [
    path("auth/token/", LoginView.as_view(), name="login"),
    path("auth/token/refresh/", RefreshView.as_view(), name="refresh"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    *router.urls,
]
