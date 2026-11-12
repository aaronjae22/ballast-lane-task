"""The container entrypoint migrates first and only then starts the command.

entrypoint.sh runs under sh with a fake `python` first on PATH, which records
its arguments and exits with a chosen code, so no database or Docker is needed.
The compose smoke test in CI covers the same script against real Postgres.
"""

import os
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

ENTRYPOINT = Path(__file__).resolve().parents[2] / "entrypoint.sh"

FAKE_PYTHON = """#!/bin/sh
echo "python $*" >> "$CALLS"
exit "${MIGRATE_EXIT:-0}"
"""

RECORD_COMMAND = ["sh", "-c", 'echo "command ran" >> "$CALLS"']


@dataclass
class Run:
    pid: int
    returncode: int
    stderr: str
    calls: list[str]


def run_entrypoint(tmp_path: Path, command: list[str], migrate_exit: int = 0) -> Run:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_python = bin_dir / "python"
    fake_python.write_text(FAKE_PYTHON)
    fake_python.chmod(0o755)
    calls = tmp_path / "calls.log"
    calls.touch()

    env = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "CALLS": str(calls),
        "MIGRATE_EXIT": str(migrate_exit),
    }
    process = subprocess.Popen(
        ["sh", str(ENTRYPOINT), *command],
        cwd=tmp_path,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    _, stderr = process.communicate(timeout=30)
    return Run(process.pid, process.returncode, stderr, calls.read_text().splitlines())


def test_migrations_run_before_the_command(tmp_path: Path) -> None:
    run = run_entrypoint(tmp_path, RECORD_COMMAND)

    assert run.returncode == 0, run.stderr
    assert run.calls == ["python manage.py migrate --noinput", "command ran"]


@pytest.mark.parametrize("migrate_exit", [1, 3])
def test_a_failed_migration_stops_the_command_from_starting(
    tmp_path: Path, migrate_exit: int
) -> None:
    run = run_entrypoint(tmp_path, RECORD_COMMAND, migrate_exit=migrate_exit)

    assert run.returncode == migrate_exit
    assert run.calls == ["python manage.py migrate --noinput"]


def test_the_command_replaces_the_shell(tmp_path: Path) -> None:
    # exec makes the server PID 1 in the container, so docker stop's SIGTERM
    # reaches it directly: the command must run in the entrypoint's own process.
    run = run_entrypoint(tmp_path, ["sh", "-c", 'echo "pid $$" >> "$CALLS"; exit 7'])

    assert run.calls[-1] == f"pid {run.pid}"
    assert run.returncode == 7


def test_the_entrypoint_is_executable() -> None:
    # The Dockerfile's ENTRYPOINT runs the file directly, so it needs the exec bit.
    assert ENTRYPOINT.stat().st_mode & stat.S_IXUSR
