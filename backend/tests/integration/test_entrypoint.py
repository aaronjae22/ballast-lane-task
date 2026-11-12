"""The container entrypoint: migrate, then seed_demo on request, then the command.

Backend, worker and beat share the image, so only the backend migrates and seeds
(ADR 0015): MIGRATE_ON_START=false turns migrate off, and SEED_DEMO=true turns the
seed on. entrypoint.sh runs under sh with a fake `python` first on PATH, which
records its arguments and exits with a chosen code per subcommand, so no database
or Docker is needed. The compose smoke test in CI covers the same script for real.
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
case "$*" in
  *seed_demo*) exit "${SEED_EXIT:-0}" ;;
  *) exit "${MIGRATE_EXIT:-0}" ;;
esac
"""

MIGRATE = "python manage.py migrate --noinput"
SEED = "python manage.py seed_demo"

RECORD_COMMAND = ["sh", "-c", 'echo "command ran" >> "$CALLS"']


@dataclass
class Run:
    pid: int
    returncode: int
    stderr: str
    calls: list[str]


def run_entrypoint(
    tmp_path: Path, command: list[str], migrate_exit: int = 0, **switches: str
) -> Run:
    """Run the script with only the given switches (SEED_DEMO, MIGRATE_ON_START, SEED_EXIT)."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_python = bin_dir / "python"
    fake_python.write_text(FAKE_PYTHON)
    fake_python.chmod(0o755)
    calls = tmp_path / "calls.log"
    calls.touch()

    inherited = {
        name: value
        for name, value in os.environ.items()
        if name not in {"SEED_DEMO", "MIGRATE_ON_START"}
    }
    env = {
        **inherited,
        **switches,
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
    assert run.calls == [MIGRATE, "command ran"]


@pytest.mark.parametrize("migrate_exit", [1, 3])
def test_a_failed_migration_stops_the_command_from_starting(
    tmp_path: Path, migrate_exit: int
) -> None:
    run = run_entrypoint(tmp_path, RECORD_COMMAND, migrate_exit=migrate_exit)

    assert run.returncode == migrate_exit
    assert run.calls == [MIGRATE]


def test_seed_demo_runs_after_migrate_when_asked(tmp_path: Path) -> None:
    run = run_entrypoint(tmp_path, RECORD_COMMAND, SEED_DEMO="true")

    assert run.returncode == 0, run.stderr
    assert run.calls == [MIGRATE, SEED, "command ran"]


@pytest.mark.parametrize("value", ["false", "", "1", "yes"])
def test_only_the_literal_true_turns_the_seed_on(tmp_path: Path, value: str) -> None:
    run = run_entrypoint(tmp_path, RECORD_COMMAND, SEED_DEMO=value)

    assert run.calls == [MIGRATE, "command ran"]


def test_a_failed_seed_stops_the_command_from_starting(tmp_path: Path) -> None:
    run = run_entrypoint(tmp_path, RECORD_COMMAND, SEED_DEMO="true", SEED_EXIT="4")

    assert run.returncode == 4
    assert run.calls == [MIGRATE, SEED]


def test_worker_and_beat_skip_migrate(tmp_path: Path) -> None:
    """Only the backend migrates; the others start after it's healthy (ADR 0015)."""
    run = run_entrypoint(tmp_path, RECORD_COMMAND, MIGRATE_ON_START="false")

    assert run.returncode == 0, run.stderr
    assert run.calls == ["command ran"]


def test_the_command_replaces_the_shell(tmp_path: Path) -> None:
    # exec makes the server PID 1 in the container, so docker stop's SIGTERM
    # reaches it directly: the command must run in the entrypoint's own process.
    run = run_entrypoint(tmp_path, ["sh", "-c", 'echo "pid $$" >> "$CALLS"; exit 7'])

    assert run.calls[-1] == f"pid {run.pid}"
    assert run.returncode == 7


def test_the_entrypoint_is_executable() -> None:
    # The Dockerfile's ENTRYPOINT runs the file directly, so it needs the exec bit.
    assert ENTRYPOINT.stat().st_mode & stat.S_IXUSR
