"""manage.py seed_demo: demo users and tasks, idempotent (spec section 7, ADR 0015).

The backend's entrypoint runs it when SEED_DEMO=true, which only compose sets. Passwords come
from SEED_DEMO_PASSWORD, or the local default in the README.
"""

from typing import Any

from django.core.management.base import BaseCommand

from accounts.seed import seed_demo
from tasks.infrastructure.clock import DjangoClock


class Command(BaseCommand):
    help = "Create the demo users and tasks, unless they exist. Changes nothing that does."

    def handle(self, *args: Any, **options: Any) -> None:
        result = seed_demo(DjangoClock())
        self.stdout.write(f"Created {result.users_created} users and {result.tasks_created} tasks.")
