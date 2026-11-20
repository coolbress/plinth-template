"""The weekly base-image watch's step runner (#266): it runs a rendered
instance's own `image` job steps as a GitHub runner would.

These tests need no docker: they run made-up steps, and check that the
current template's job is one the runner can run. The watch's build and scan
run on GitHub only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from template_render import render
from template_render.image_watch import (
    UnsupportedStepError,
    check_supported,
    image_steps,
    run_steps,
)


@pytest.mark.parametrize("archetype", ["backend", "web"])
def test_the_rendered_image_job_is_one_the_watch_can_run(tmp_path: Path, archetype: str) -> None:
    """A step the runner does not know (an `if:`, another action, a new
    expression) fails here, in this repository's CI, not first in the weekly
    run."""
    steps = image_steps(render(tmp_path, archetype=archetype, owner="someone"))
    check_supported(steps)


def test_steps_share_path_and_outcomes_like_a_runner(tmp_path: Path) -> None:
    """`$GITHUB_PATH` reaches the next step, a failed `continue-on-error` step
    goes on with its outcome readable, and annotations are collected."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    tool = bin_dir / "made-up-tool"
    tool.write_text("#!/bin/sh\necho tool-ran\n", encoding="utf-8")
    tool.chmod(0o755)
    steps: list[dict[str, Any]] = [
        {"uses": "actions/checkout@0123", "with": {"persist-credentials": False}},
        {"name": "put", "env": {"D": str(bin_dir)}, "run": 'echo "$D" >> "$GITHUB_PATH"'},
        {"name": "use", "run": "made-up-tool"},
        {"name": "soft", "id": "scan", "continue-on-error": True, "run": "exit 3"},
        {
            "name": "read",
            "shell": "python",
            "env": {"SCAN": "${{ steps.scan.outcome }}", "T": "${{ runner.temp }}"},
            "run": "import os\nprint('::warning::scan was ' + os.environ['SCAN'])\n"
            "print('temp ok' if os.path.isdir(os.environ['T']) else 'no temp')",
        },
    ]
    run = run_steps(steps, cwd=tmp_path, token="", temp=tmp_path / "t")
    assert run.failed_step is None
    assert run.soft_failed == ["soft"]
    assert run.warnings == ["scan was failure"]
    assert not run.ok, "a scan that did not finish passed the watch"
    assert "tool-ran" in run.output
    assert "temp ok" in run.output


def test_a_failed_step_stops_the_job(tmp_path: Path) -> None:
    steps: list[dict[str, Any]] = [
        {"name": "build", "run": "echo '::error::no build'; exit 1"},
        {"name": "never", "run": "echo reached"},
    ]
    run = run_steps(steps, cwd=tmp_path, token="", temp=tmp_path / "t")
    assert run.failed_step == "build"
    assert run.errors == ["no build"]
    assert "reached" not in run.output
    assert not run.ok


def test_the_default_shell_stops_at_the_first_failing_command(tmp_path: Path) -> None:
    """GitHub runs an unnamed shell as `bash -e`."""
    run = run_steps(
        [{"name": "two", "run": "false\necho after"}], cwd=tmp_path, token="", temp=tmp_path / "t"
    )
    assert run.failed_step == "two"
    assert "after" not in run.output


@pytest.mark.parametrize(
    "step",
    [
        {"name": "x", "if": "always()", "run": "true"},
        {"name": "x", "uses": "actions/cache@0123"},
        {"name": "x", "run": "echo ${{ github.event.pull_request.title }}"},
        {"name": "x", "env": {"A": "${{ secrets.X }}"}, "run": "true"},
        {"name": "x", "shell": "pwsh", "run": "true"},
        {"name": "x", "working-directory": "sub", "run": "true"},
        {"name": "x", "continue-on-error": "${{ true }}", "run": "exit 1"},
        {"name": "x", "continue-on-error": "true", "run": "exit 1"},
    ],
)
def test_what_the_runner_does_not_know_stops_it(tmp_path: Path, step: dict[str, Any]) -> None:
    """Never guessed: a step run differently from GitHub would pass or fail
    for a reason the instance does not have."""
    with pytest.raises(UnsupportedStepError):
        check_supported([step])
    with pytest.raises(UnsupportedStepError):
        run_steps([step], cwd=tmp_path, token="", temp=tmp_path / "t")


def test_a_step_that_sets_job_env_stops_the_runner(tmp_path: Path) -> None:
    steps: list[dict[str, Any]] = [{"name": "env", "run": 'echo "A=1" >> "$GITHUB_ENV"'}]
    with pytest.raises(UnsupportedStepError, match="GITHUB_ENV"):
        run_steps(steps, cwd=tmp_path, token="", temp=tmp_path / "t")


@pytest.mark.parametrize(
    "extra",
    [
        {"jobs": {"image": {"defaults": {"run": {"shell": "bash"}}}}},
        {"jobs": {"image": {"env": {"A": "1"}}}},
        {"jobs": {"image": {"container": "debian"}}},
        {"env": {"A": "1"}},
        {"defaults": {"run": {"working-directory": "sub"}}},
    ],
)
def test_what_a_step_inherits_stops_the_runner(tmp_path: Path, extra: dict[str, Any]) -> None:
    """A job- or workflow-level default changes how every step runs."""
    import yaml  # type: ignore[import-untyped]

    ci: dict[str, Any] = {
        "jobs": {"image": {"runs-on": "ubuntu-latest", "steps": [{"run": "true"}]}}
    }
    for key, value in extra.items():
        if key == "jobs":
            ci["jobs"]["image"].update(value["image"])
        else:
            ci[key] = value
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text(yaml.safe_dump(ci), "utf-8")
    with pytest.raises(UnsupportedStepError, match="inherits"):
        image_steps(tmp_path)
