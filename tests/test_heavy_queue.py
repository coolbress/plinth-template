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
import shutil
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


def test_a_queue_directory_that_is_a_link_is_refused(start: Start, tmp_path: Path) -> None:
    """On a shared machine another user can make the queue's path first and
    fill it with links to the caller's files, which the entry's write would
    then overwrite. The script writes only into a directory it owns that is
    not a link; a link stands in for another user's directory here."""
    env = _env(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir(mode=0o700)
    (tmp_path / "tmp" / f"plinth-heavy-{os.getuid()}").symlink_to(elsewhere)
    ran = tmp_path / "ran"
    refused = start(env, f"touch {ran}")
    _, err = refused.communicate(timeout=30)
    assert refused.returncode == 2, err
    assert "plinth-heavy" in err, err
    assert not ran.exists()
    assert not any(elsewhere.iterdir()), "an entry was written through the link"


def test_without_ps_it_says_so_instead_of_running_unqueued(start: Start, tmp_path: Path) -> None:
    """Every entry, the caller's own included, would read as gone, and the
    command would run with no limit and no word."""
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    for tool in ("id", "mkdir", "rm", "tr", "grep", "sleep", "sh", "touch"):
        found = shutil.which(tool)
        assert found, tool
        (bin_ / tool).symlink_to(found)
    env = {**_env(tmp_path), "PATH": str(bin_)}
    ran = tmp_path / "ran"
    refused = start(env, f"touch {ran}")
    _, err = refused.communicate(timeout=30)
    assert refused.returncode == 2, err
    assert "ps" in err, err
    assert not ran.exists()


def _queue(tmp_path: Path) -> Path:
    return tmp_path / "tmp" / f"plinth-heavy-{os.getuid()}"


def _tickets(tmp_path: Path) -> list[Path]:
    found = _queue(tmp_path) / ".tickets"
    return sorted(p for p in found.glob("[0-9]*")) if found.is_dir() else []


def _wait_for_tickets(tmp_path: Path, count: int, seconds: float = 10) -> None:
    deadline = time.monotonic() + seconds
    while len(_tickets(tmp_path)) < count:
        assert time.monotonic() < deadline, f"{len(_tickets(tmp_path))} of {count} tickets"
        time.sleep(0.05)


def test_six_waiters_on_one_slot_run_in_the_order_they_started(
    start: Start, tmp_path: Path
) -> None:
    """A poll at random, as before, gives a waiter of a second the same chance
    at the next free slot as one of nineteen minutes. Each waiter here starts
    once the one before it holds its ticket."""
    env = _env(tmp_path, PLINTH_HEAVY_SLOTS="1")
    log, started, go = tmp_path / "log", tmp_path / "started", tmp_path / "go"
    holder = start(env, f"touch {started}; while [ ! -e {go} ]; do sleep 0.05; done")
    _wait_for(started)
    # A pid-named entry too, for an older heavy.sh, which counts only those.
    assert (_queue(tmp_path) / str(holder.pid)).is_file()
    waiters = []
    for n in range(1, 7):
        waiters.append(start(env, f"echo {n} >> {log}"))
        _wait_for_tickets(tmp_path, n + 1)
    go.touch()
    holder.communicate(timeout=60)
    errors = [w.communicate(timeout=90)[1] for w in waiters]
    assert [w.returncode for w in waiters] == [0] * 6, errors
    assert log.read_text().split() == [str(n) for n in range(1, 7)], errors
    # Each says where it is: the third has two waiting ahead of it.
    assert "2 ahead, 1 running" in errors[2], errors[2]


def test_a_waiter_killed_with_kill_9_does_not_hold_the_queue(start: Start, tmp_path: Path) -> None:
    env = _env(tmp_path, PLINTH_HEAVY_SLOTS="1")
    log, started, go = tmp_path / "log", tmp_path / "started", tmp_path / "go"
    holder = start(env, f"touch {started}; while [ ! -e {go} ]; do sleep 0.05; done")
    _wait_for(started)
    killed = start(env, f"echo killed >> {log}")
    _wait_for_tickets(tmp_path, 2)
    behind = start(env, f"echo behind >> {log}")
    _wait_for_tickets(tmp_path, 3)
    killed.send_signal(signal.SIGKILL)  # no chance to give its ticket back
    killed.communicate(timeout=10)
    go.touch()
    holder.communicate(timeout=60)
    _, err = behind.communicate(timeout=60)
    assert behind.returncode == 0, err
    assert log.read_text().split() == ["behind"], err
    holders = [t.read_text().split()[0] for t in _tickets(tmp_path)]
    assert str(killed.pid) not in holders, "the killed waiter's ticket stayed"


def test_a_wait_it_can_estimate_past_the_limit_exits_at_once(start: Start, tmp_path: Path) -> None:
    """The shortest of the last runs took an hour and one is running now, so
    a five-minute limit cannot be met: it says so at once instead of waiting
    the five minutes out."""
    env = _env(tmp_path, PLINTH_HEAVY_SLOTS="1", PLINTH_HEAVY_WAIT="5")
    started, ran = tmp_path / "started", tmp_path / "ran"
    start(env, f"touch {started}; exec sleep 60")
    _wait_for(started)
    (_queue(tmp_path) / ".tickets" / ".took").write_text("3600\n4000\n")
    began = time.monotonic()
    refused = start(env, f"touch {ran}")
    _, err = refused.communicate(timeout=30)
    assert refused.returncode == BUSY, err
    assert time.monotonic() - began < 15, "it waited instead of exiting at once"
    assert "did not run" in err, err
    assert re.search(r"at least (59|60) min", err), err  # 3600 s less the holder's age
    assert not ran.exists()


def test_a_short_history_waits_and_says_how_long(start: Start, tmp_path: Path) -> None:
    """The last run took 2 s, so a limit of 20 minutes can be met: it waits,
    and its wait line gives the running command's age and the estimate."""
    env = _env(tmp_path, PLINTH_HEAVY_SLOTS="1")
    started, go, ran = tmp_path / "started", tmp_path / "go", tmp_path / "ran"
    holder = start(env, f"touch {started}; while [ ! -e {go} ]; do sleep 0.05; done")
    _wait_for(started)
    (_queue(tmp_path) / ".tickets" / ".took").write_text("2\n")
    waiter = start(env, f"touch {ran}")
    _wait_for_tickets(tmp_path, 2)
    time.sleep(1)
    go.touch()
    holder.communicate(timeout=60)
    _, err = waiter.communicate(timeout=60)
    assert waiter.returncode == 0, err
    assert ran.exists()
    assert re.search(rf"0 ahead, 1 running \(pid {holder.pid} for 0 min\)", err), err
    assert "about 0 min more" in err, err


def test_a_run_a_waiter_watched_end_is_remembered(start: Start, tmp_path: Path) -> None:
    env = _env(tmp_path, PLINTH_HEAVY_SLOTS="1")
    started = tmp_path / "started"
    holder = start(env, f"touch {started}; sleep 3")
    _wait_for(started)
    waiter = start(env, "true")
    _wait_for_tickets(tmp_path, 2)
    holder.communicate(timeout=30)
    _, err = waiter.communicate(timeout=30)
    assert waiter.returncode == 0, err
    took = (_queue(tmp_path) / ".tickets" / ".took").read_text().split()
    assert len(took) == 1, took
    assert 3 <= int(took[0]) <= 6, took


def test_a_run_that_ended_unwatched_leaves_no_time(start: Start, tmp_path: Path) -> None:
    """The time since it started is the gap between calls (3 s), not its run (0 s)."""
    env = _env(tmp_path, PLINTH_HEAVY_SLOTS="1")
    first = start(env, "true")
    first.communicate(timeout=30)
    time.sleep(3)
    second = start(env, "true")
    _, err = second.communicate(timeout=30)
    assert second.returncode == 0, err
    took = _queue(tmp_path) / ".tickets" / ".took"
    assert not took.exists() or not took.read_text().split(), took.read_text()


def test_a_stray_name_in_the_tickets_does_not_stop_a_ticket(start: Start, tmp_path: Path) -> None:
    """A name that starts with a digit and is not all digits, and a dangling
    link with a ticket's name, made the next number's search loop forever."""
    env = _env(tmp_path, PLINTH_HEAVY_SLOTS="1")
    tickets = _queue(tmp_path) / ".tickets"
    tickets.mkdir(parents=True, mode=0o700)
    (tickets / "0000000003.bak").write_text("x\n")
    (tickets / "0000000004").symlink_to(tmp_path / "nowhere")
    ran = tmp_path / "ran"
    run = start(env, f"touch {ran}")
    _, err = run.communicate(timeout=30)
    assert run.returncode == 0, err
    assert ran.exists()


def test_a_new_ticket_holder_the_caller_cannot_signal_keeps_its_slot(
    start: Start, tmp_path: Path
) -> None:
    """The ticket form of the pid-1 case below."""
    env = _env(tmp_path, PLINTH_HEAVY_SLOTS="1", PLINTH_HEAVY_WAIT="0")
    tickets = _queue(tmp_path) / ".tickets"
    tickets.mkdir(parents=True, mode=0o700)
    now = int(time.time())
    (tickets / "0000000001").write_text(f"1 {now} {now}\n")
    ran = tmp_path / "ran"
    refused = start(env, f"touch {ran}")
    _, err = refused.communicate(timeout=30)
    assert refused.returncode == BUSY, err
    assert not ran.exists(), "pid 1's ticket was taken as a dead one's"
    assert (tickets / "0000000001").exists()


def test_a_waiter_stopped_after_losing_the_race_leaves_the_winner_s_ticket(
    start: Start, tmp_path: Path
) -> None:
    """A fake `ln` loses the race: another waiter makes the name, then it fails."""
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    tried = tmp_path / "tried"
    winner = subprocess.Popen(["sleep", "60"])  # noqa: S607 - a stand-in live pid
    try:
        fake = bin_ / "ln"
        fake.write_text(
            f'#!/bin/sh\nprintf "%s 0\\n" {winner.pid} > "$2"\ntouch {tried}\nsleep 1\nexit 1\n'
        )
        fake.chmod(0o755)
        env = {**_env(tmp_path), "PATH": f"{bin_}:{os.environ['PATH']}"}
        waiter = start(env, "true")
        _wait_for(tried)
        waiter.send_signal(signal.SIGTERM)
        _, err = waiter.communicate(timeout=30)
        assert waiter.returncode == 143, err
        holders = [p.read_text().split()[0] for p in _tickets(tmp_path)]
        assert str(winner.pid) in holders, "the winner's ticket was removed"
    finally:
        winner.kill()
        winner.wait()
