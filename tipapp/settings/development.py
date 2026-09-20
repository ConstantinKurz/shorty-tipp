"""
Development settings for tipapp project.
"""

import os

from .base import *  # noqa: F403, F401

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# Console backend by default; set EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend to send real emails
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")

# Development-specific settings
INTERNAL_IPS = [
    "127.0.0.1",
]
