"""
Settings package initialization.
Default to development settings if not explicitly set.
"""

import os

# Only import default settings if DJANGO_SETTINGS_MODULE is not set
# This allows pytest and other tools to override the settings module
settings_module = os.environ.get("DJANGO_SETTINGS_MODULE")
if not settings_module or settings_module == "tipapp.settings":
    # Default to development if not explicitly set
    from .development import *  # noqa: F403, F401
