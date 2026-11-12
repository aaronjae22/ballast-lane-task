"""The project's LOGGING: the tasks loggers reach stderr at INFO.

The jobs log every email they skip at INFO (ADR 0015). Without the project's LOGGING, those
lines would fall to Python's last-resort handler, which drops everything below WARNING.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("settings_module", ["config.settings", "config.test_settings"])
def test_the_jobs_info_lines_reach_stderr(settings_module: str) -> None:
    """A subprocess and no caplog: caplog would lower the level itself and hide a gap."""
    script = (
        "import django; django.setup()\n"
        "import logging\n"
        "logging.getLogger('tasks.infrastructure.jobs').info('No assignment email for task 7.')\n"
    )
    env = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": settings_module,
        "DJANGO_SECRET_KEY": "test-only-not-a-secret",
    }

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "INFO tasks.infrastructure.jobs: No assignment email for task 7." in result.stderr
