"""Test settings: the base settings plus a test-only secret key and an in-process cache.

Django's test runner always runs with DEBUG off, and the base settings refuse
the built-in insecure key when DEBUG is off, so tests supply their own key.
Tests empty the cache to reset the throttles, so they never use Redis: that
would flush a developer's real cache (ADR 0014).
"""

import os

# Long enough for HS256 (32+ bytes): simplejwt signs tokens with the secret key.
os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-not-a-secret-but-long-enough-for-hs256")

from config.settings import *  # noqa: F403
from config.settings import CACHE_BACKENDS, REST_FRAMEWORK

CACHES = {"default": CACHE_BACKENDS["locmem"]}
# The API parses JSON only, so the test client sends JSON unless told otherwise.
REST_FRAMEWORK = {**REST_FRAMEWORK, "TEST_REQUEST_DEFAULT_FORMAT": "json"}
