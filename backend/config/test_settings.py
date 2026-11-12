"""Test settings: the base settings plus a test-only secret key and an in-process cache.

Django's test runner always runs with DEBUG off, and the base settings refuse
the built-in insecure key when DEBUG is off, so tests supply their own key.
Tests empty the cache to reset the throttles, so they never use Redis: that
would flush a developer's real cache (ADR 0014).
"""

import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-not-a-secret")

from config.settings import *  # noqa: F403
from config.settings import CACHE_BACKENDS

CACHES = {"default": CACHE_BACKENDS["locmem"]}
