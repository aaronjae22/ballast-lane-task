"""URLs of the accounts app, under /api/."""

from rest_framework.routers import SimpleRouter

from accounts.views import UserViewSet

# SimpleRouter, not DefaultRouter: no API root view, and the tasks routes share the prefix.
router = SimpleRouter(use_regex_path=False)
router.register("users", UserViewSet, basename="user")

urlpatterns = router.urls
