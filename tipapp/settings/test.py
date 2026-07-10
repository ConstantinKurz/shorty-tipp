"""
Test settings for tipapp project.
Uses SQLite for faster test execution without Docker dependency.
"""

from .base import *  # noqa: F403, F401

# Use SQLite for tests - faster and doesn't require PostgreSQL
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Disable password hashing for faster tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

#  Email backend for testing
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Debug settings for tests
DEBUG = True
