"""URLs of the task endpoints, under /api/."""

from rest_framework.routers import SimpleRouter

from tasks.api.views import TaskViewSet

# use_regex_path=False, so the viewset's lookup_value_converter ("int") applies.
router = SimpleRouter(use_regex_path=False)
router.register("tasks", TaskViewSet, basename="task")

urlpatterns = router.urls
