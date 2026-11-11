"""Test settings: the base settings plus a test-only secret key.

Django's test runner always runs with DEBUG off, and the base settings refuse
the built-in insecure key when DEBUG is off, so tests supply their own key.
"""

import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-not-a-secret")

from config.settings import *  # noqa: F403
