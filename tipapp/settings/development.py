"""
Development settings for tipapp project.
"""

from .base import *  # noqa: F403, F401

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# Use console email backend for development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Development-specific settings
INTERNAL_IPS = [
    "127.0.0.1",
]
