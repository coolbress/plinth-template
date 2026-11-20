"""The weekly base-image watch (#266): it runs a rendered instance's own
`image` job at a shorter grace, so it fails while new projects still pass.

These tests need no docker: they run made-up steps, and the rendered verdict
step on a made-up report. The watch's build and scan run on GitHub only.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

import pytest

from template_render import render
from template_render.image_watch import (
    JobRun,
    UnsupportedStepError,
    check_supported,
    findings_due,
    image_steps,
    issue_body,
    run_steps,
    set_grace,
)

TODAY = datetime.datetime.now(datetime.UTC).date()


@pytest.fixture(scope="module")
def backend_steps(tmp_path_factory: pytest.TempPathFactory) -> list[dict[str, Any]]:
    out = render(tmp_path_factory.mktemp("watch-backend"), archetype="backend", owner="someone")
    return image_steps(out)


@pytest.mark.parametrize("archetype", ["backend", "web"])
def test_the_rendered_image_job_is_one_the_watch_can_run(tmp_path: Path, archetype: str) -> None:
    """A step the runner does not know (an `if:`, another action, a new
    expression) fails here, in this repository's CI, not first in the weekly
    run."""
    steps = image_steps(render(tmp_path, archetype=archetype, owner="someone"))
    check_supported(steps)
    _, rendered = set_grace(steps, 7)
    assert rendered == 14


def test_set_grace_changes_only_the_verdict_step(backend_steps: list[dict[str, Any]]) -> None:
    changed, rendered = set_grace(backend_steps, 7)
    assert rendered == 14
    graced = [s for s in changed if "GRACE_DAYS" in (s.get("env") or {})]
    assert len(graced) == 1
    assert graced[0]["env"]["GRACE_DAYS"] == "7"
    (original,) = [s for s in backend_steps if "GRACE_DAYS" in (s.get("env") or {})]
    assert graced[0]["run"] == original["run"], "the verdict itself was changed"
    assert [s.get("name") for s in changed] == [s.get("name") for s in backend_steps]
    assert original["env"]["GRACE_DAYS"] == "14", "the rendered steps were changed in place"


def test_set_grace_refuses_a_job_without_one() -> None:
    with pytest.raises(UnsupportedStepError, match="GRACE_DAYS"):
        set_grace([{"run": "true"}], 7)


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


def _report(tmp_path: Path, days_ago: int) -> Path:
    since = (TODAY - datetime.timedelta(days=days_ago)).isoformat()
    match = {
        "vulnerability": {
            "id": "CVE-2026-109518",
            "severity": "High",
            "fix": {
                "versions": ["3.0.4"],
                "state": "fixed",
                "available": [{"version": "3.0.4", "date": since, "kind": "advisory"}],
            },
        },
        "artifact": {"name": "apt", "version": "3.0.3", "type": "deb"},
    }
    descriptor = {"version": "0.121.0", "db": {"status": {"built": "2026-11-18T06:00:00Z"}}}
    path = tmp_path / "fixture.json"
    path.write_text(json.dumps({"matches": [match], "descriptor": descriptor}), "utf-8")
    return path


def _verdict_job(steps: list[dict[str, Any]], report: Path) -> list[dict[str, Any]]:
    """The rendered verdict step, after a made-up scan that copies `report`."""
    (verdict,) = [s for s in steps if "GRACE_DAYS" in (s.get("env") or {})]
    scan = {"name": "scan", "id": "scan", "run": f'cp "{report}" "$RUNNER_TEMP/scan.json"'}
    return [scan, verdict]


@pytest.mark.parametrize(("grace", "fails"), [(7, True), (14, False)])
def test_the_rendered_verdict_fails_earlier_at_the_watch_grace(
    tmp_path: Path, backend_steps: list[dict[str, Any]], grace: int, fails: bool
) -> None:
    """A fix ten days old: a warning in a new project, a failure in the watch."""
    steps, _ = set_grace(backend_steps, grace)
    run = run_steps(
        _verdict_job(steps, _report(tmp_path, 10)), cwd=tmp_path, token="", temp=tmp_path / "t"
    )
    assert (run.failed_step is not None) is fails
    if fails:
        assert len(run.errors) == 1
        assert "apt 3.0.3 (fixed in 3.0.4, since" in run.errors[0]
    else:
        assert run.errors == []
        assert len(run.warnings) == 1


def test_findings_due_counts_days_to_the_projects_grace(
    tmp_path: Path, backend_steps: list[dict[str, Any]]
) -> None:
    steps, _ = set_grace(backend_steps, 7)
    run = run_steps(
        _verdict_job(steps, _report(tmp_path, 10)), cwd=tmp_path, token="", temp=tmp_path / "t"
    )
    due = findings_due(run.errors, project_grace=14, today=TODAY)
    assert len(due) == 1
    finding, fail_day = due[0]
    assert finding.startswith("apt 3.0.3 (fixed in 3.0.4, since ")
    assert "CVE-2026-109518" in finding
    assert fail_day == TODAY + datetime.timedelta(days=5)


def _failed(errors: list[str], **kw: Any) -> JobRun:
    return JobRun(
        failed_step=kw.get("failed_step", "Read the scan, and fail on a fix older than 14 days"),
        soft_failed=kw.get("soft_failed", []),
        errors=errors,
        warnings=[],
        output="",
        project_grace=14,
    )


def test_issue_body_names_finding_days_left_and_steps() -> None:
    since = (TODAY - datetime.timedelta(days=10)).isoformat()
    late = (TODAY - datetime.timedelta(days=20)).isoformat()
    line = (
        "fail: image scan, 2 high or critical vulnerabilities have had a fix for more than"
        f" 7 days: apt 3.0.3 (fixed in 3.0.4, since {since}: CVE-2026-109518); libapt-pkg7.0"
        f" 3.0.3 (fixed in 3.0.4, since {late}: CVE-2026-109518); a Debian package ... "
        "(grype 0.121.0, database built 2026-11-18)"
    )
    body = issue_body(
        {"backend": _failed([line]), "web": JobRun(None, [], [], [], "", 14)},
        ref="v1.46.0",
        run_url="https://example.invalid/run/1",
        watch_grace=7,
        today=TODAY,
    )
    assert "v1.46.0" in body
    assert "https://example.invalid/run/1" in body
    assert "apt 3.0.3 (fixed in 3.0.4" in body
    assert "5 days left" in body
    assert "libapt-pkg7.0 3.0.3" in body
    assert "new projects fail on it now" in body
    assert "`template/Dockerfile.jinja`" in body
    assert "release" in body.lower()
    assert "coolbress/plinth" in body
    assert "### web" not in body, "a passing archetype is reported as a failure"


def test_issue_body_says_so_when_it_cannot_read_a_date() -> None:
    """A failure the body cannot parse is still reported, with where to look."""
    body = issue_body(
        {"web": _failed([], failed_step="docker build", soft_failed=[])},
        ref="v9.9.9",
        run_url="https://example.invalid/run/2",
        watch_grace=7,
        today=TODAY,
    )
    assert "docker build" in body
    assert "https://example.invalid/run/2" in body


def test_issue_body_reports_a_scan_that_did_not_finish() -> None:
    body = issue_body(
        {"backend": _failed([], failed_step=None, soft_failed=["Scan the image"])},
        ref="v9.9.9",
        run_url="https://example.invalid/run/3",
        watch_grace=7,
        today=TODAY,
    )
    assert "Scan the image" in body
    assert "did not finish" in body


def test_the_steps_to_raise_are_given_only_for_a_named_finding() -> None:
    """A watch that broke for another reason must not send someone to raise a
    digest that may be fine."""
    body = issue_body(
        {"web": _failed([], failed_step="docker build")},
        ref="v9.9.9",
        run_url="https://example.invalid/run/4",
        watch_grace=7,
        today=TODAY,
    )
    assert "`template/Dockerfile.jinja`" not in body
    assert "No finding is named above" in body


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
