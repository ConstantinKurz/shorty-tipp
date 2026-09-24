"""Guard tests ensuring service modules import cleanly in isolation."""

import os
import subprocess
import sys

import pytest

MODULE_NAMES = [
    "notifications.services",
    "scoring.match_scoring",
    "scoring.champion_scoring",
    "scoring.ranking_service",
    "scoring.exports",
    "users.signals",
]


@pytest.mark.parametrize("module_name", MODULE_NAMES)
def test_module_imports_in_isolation(module_name: str) -> None:
    """Each module imports in a fresh interpreter, proving no import-order dependency."""
    # A subprocess is used so that importing never re-registers signal receivers in this run.
    env = {**os.environ, "DJANGO_SETTINGS_MODULE": "tipapp.settings.test"}
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import django; django.setup(); "
            f"import importlib; importlib.import_module({module_name!r})",
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode == 0, result.stderr
