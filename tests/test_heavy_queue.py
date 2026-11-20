"""The rendered `scripts/heavy.sh` (#284): a machine-wide queue for the full
suite, so the sessions on one machine share its slots instead of running
eleven suites at once.

Each test runs the rendered script with `/bin/bash`, which is bash 3.2 on
macOS, and a `TMPDIR` of its own, so the queue it sees is the test's alone.
Neither macOS nor this script has `flock`.
"""

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from template_render import render

#: The script's exit status when its command did not run because the slots
#: stayed busy: EX_TEMPFAIL, distinct from any status pytest returns.
BUSY = 75


@pytest.fixture(scope="module")
def heavy(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return render(tmp_path_factory.mktemp("heavy")) / "scripts" / "heavy.sh"


def _env(tmp_path: Path, **settings: str) -> dict[str, str]:
    queue = tmp_path / "tmp"
    queue.mkdir(exist_ok=True)
    return {**os.environ, "TMPDIR": str(queue), **settings}


Start = Callable[[dict[str, str], str], subprocess.Popen[str]]


@pytest.fixture
def start(heavy: Path) -> Iterator[Start]:
    """Runs `heavy.sh sh -c <command>`; whatever is still running when the test
    ends, failed or not, is killed and reaped."""
    started: list[subprocess.Popen[str]] = []

    def run(env: dict[str, str], command: str) -> subprocess.Popen[str]:
        proc = subprocess.Popen(  # noqa: S603 - the rendered script and a literal command
            ["/bin/bash", str(heavy), "sh", "-c", command],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        started.append(proc)
        return proc

    yield run
    for proc in started:
        proc.kill()
        proc.communicate()


def _wait_for(path: Path, seconds: float = 10) -> None:
    deadline = time.monotonic() + seconds
    while not path.exists():
        assert time.monotonic() < deadline, f"{path.name} never appeared"
        time.sleep(0.05)


@pytest.mark.parametrize("archetype", ["cli", "library", "backend", "data-ml", "web"])
def test_every_archetype_renders_the_script_executable(tmp_path: Path, archetype: str) -> None:
    script = render(tmp_path, archetype=archetype) / "scripts" / "heavy.sh"
    assert script.is_file(), f"{archetype} has no scripts/heavy.sh"
    assert os.access(script, os.X_OK), "scripts/heavy.sh is not executable"


def test_with_one_slot_a_second_call_waits_until_the_first_ends(
    start: Start, tmp_path: Path
) -> None:
    env = _env(tmp_path, PLINTH_HEAVY_SLOTS="1")
    log, started = tmp_path / "log", tmp_path / "started"
    first = start(env, f"touch {started}; sleep 2; echo first >> {log}")
    _wait_for(started)
    second = start(env, f"echo second >> {log}")
    # Reaped first: until its parent reaps it, an ended process is a zombie,
    # which `kill -0` still finds, and its slot stays taken.
    first.communicate(timeout=60)
    _, waited = second.communicate(timeout=60)
    assert (first.returncode, second.returncode) == (0, 0), waited
    assert log.read_text().split() == ["first", "second"], "the second did not wait"
    # The wait line names how many run and their pids.
    assert "1 running" in waited, waited
    assert str(first.pid) in waited, waited


def test_a_slot_whose_pid_is_gone_is_taken_back(start: Start, tmp_path: Path) -> None:
    env = _env(tmp_path, PLINTH_HEAVY_SLOTS="1", PLINTH_HEAVY_WAIT="0")
    started = tmp_path / "started"
    holder = start(env, f"touch {started}; exec sleep 60")
    _wait_for(started)
    holder.send_signal(signal.SIGKILL)  # no chance to give its slot back
    holder.communicate(timeout=10)
    ran = tmp_path / "ran"
    after = start(env, f"touch {ran}")
    _, err = after.communicate(timeout=30)
    assert after.returncode == 0, err
    assert ran.exists(), "the command did not run in the dead holder's slot"


def test_a_wait_limit_of_0_gives_up_on_a_busy_slot(start: Start, tmp_path: Path) -> None:
    env = _env(tmp_path, PLINTH_HEAVY_SLOTS="1", PLINTH_HEAVY_WAIT="0")
    started, ran = tmp_path / "started", tmp_path / "ran"
    start(env, f"touch {started}; exec sleep 60")
    _wait_for(started)
    refused = start(env, f"touch {ran}")
    _, err = refused.communicate(timeout=30)
    assert refused.returncode == BUSY, err
    assert "did not run" in err, err
    assert not ran.exists(), "the command ran on a busy slot"


@pytest.mark.parametrize("host", ["github", "gitlab"])
def test_agents_md_runs_the_whole_suite_through_the_queue(tmp_path: Path, host: str) -> None:
    """The block's `pytest` waits for a slot, with no prompt; the narrow run of
    the touched tests does not queue. CI never reads `AGENTS.md`."""
    out = render(tmp_path, host=host)
    agents = (out / "AGENTS.md").read_text(encoding="utf-8")
    block = agents.split("```bash\n", 1)[1].split("```", 1)[0]
    assert re.search(r"^scripts/heavy\.sh uv run pytest(?=\s)", block, re.M), block
    assert not re.search(r"^uv run pytest", block, re.M), "the block runs pytest unqueued"
    assert "(`uv run pytest tests/test_<module>.py`, or `-k`)" in agents
    settings = json.loads((out / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert "Bash(scripts/heavy.sh uv run pytest:*)" in settings["permissions"]["allow"]
    assert not any(a.startswith("Bash(scripts/heavy.sh:") for a in settings["permissions"]["allow"])
    skill = " ".join((out / ".claude/skills/verify/SKILL.md").read_text(encoding="utf-8").split())
    assert "without `scripts/heavy.sh`" in skill, "verify queues a single test file"


def test_a_live_holder_the_caller_cannot_signal_keeps_its_slot(
    start: Start, tmp_path: Path
) -> None:
    """`kill -0` fails on a live process it may not signal, as a sandbox can
    make every other session's be; read as gone, its slot would be taken and
    the slots overrun. Pid 1 is always alive and never the caller's to signal."""
    env = _env(tmp_path, PLINTH_HEAVY_SLOTS="1", PLINTH_HEAVY_WAIT="0")
    queue = tmp_path / "tmp" / f"plinth-heavy-{os.getuid()}"
    queue.mkdir(mode=0o700)
    (queue / "1").write_text("1\n")
    ran = tmp_path / "ran"
    refused = start(env, f"touch {ran}")
    _, err = refused.communicate(timeout=30)
    assert refused.returncode == BUSY, err
    assert not ran.exists(), "pid 1's slot was taken as a dead one's"
