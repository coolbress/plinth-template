"""Run a rendered project's `image` job steps, for the base-image watch (#266).

The pinned base images in `template/Dockerfile.jinja` age, and a new
project's `image` job fails once a high or critical fix is more than 14 days
older than the image. The weekly watch runs that render's own `image` job
steps in order, the verdict included, with its grace shortened; this module
runs them and writes the issue body that says what to raise.

The verdict logic is never copied here: the steps are read from the rendered
`.github/workflows/ci.yml`, and only the one `GRACE_DAYS` value changes. The
runner knows the few things those steps use (a checkout, `run:` in bash or
Python, `continue-on-error`, `$GITHUB_PATH`, three expressions); anything else
stops it, because a step run differently from GitHub would pass or fail for a
reason the instance does not have.
"""

from __future__ import annotations

import copy
import datetime
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: Where the rendered job's steps come from, relative to the rendered project.
CI = Path(".github") / "workflows" / "ci.yml"
JOB = "image"
GRACE_KEY = "GRACE_DAYS"
CHECKOUT = "actions/checkout@"
JOB_KEYS = frozenset({"name", "runs-on", "timeout-minutes", "permissions", "steps"})
KNOWN_KEYS = frozenset({"name", "id", "run", "shell", "env", "continue-on-error", "uses", "with"})
EXPRESSION = re.compile(r"\$\{\{\s*(.*?)\s*\}\}")
STEP_OUTCOME = re.compile(r"steps\.([A-Za-z_][\w-]*)\.outcome")
#: One finding as the verdict names it: `apt 3.0.3 (fixed in 3.0.4, since
#: 2026-11-04: CVE-2026-109518)`, after `: ` or `; `.
FINDING = re.compile(
    r"(?:: |; )(?P<finding>\S+ \S+ \(fixed in [^,()]*, since (?P<since>\d{4}-\d{2}-\d{2}): [^)]*\))"
)
#: Every annotation the steps print, kept for the issue.
ANNOTATION = re.compile(r"^::(error|warning)::(.*)$")


class UnsupportedStepError(Exception):
    """A step this runner would not run the way GitHub does."""


@dataclass
class JobRun:
    """One archetype's `image` job, as the watch ran it."""

    #: The step that failed and stopped the job; None when every step ran.
    failed_step: str | None
    #: `continue-on-error` steps that failed: the scan that did not finish.
    soft_failed: list[str]
    errors: list[str]
    warnings: list[str]
    output: str
    #: The grace the rendered project has, which the issue counts days to.
    project_grace: int = 0

    @property
    def ok(self) -> bool:
        return self.failed_step is None and not self.soft_failed


def image_steps(rendered: Path) -> list[dict[str, Any]]:
    import yaml  # type: ignore[import-untyped]  # comes with copier, no stubs

    ci = yaml.safe_load((rendered / CI).read_text(encoding="utf-8"))
    job = ci["jobs"][JOB]
    # What a step inherits from its job or workflow (a default shell, a
    # working directory, an env, a container) would change how it runs.
    inherited = sorted({"defaults", "env"} & set(ci)) + sorted(set(job) - JOB_KEYS)
    if inherited:
        raise UnsupportedStepError(
            f"the `{JOB}` job inherits {inherited}, which the watch does not run"
        )
    steps: list[dict[str, Any]] = job["steps"]
    return steps


def _label(step: dict[str, Any]) -> str:
    return str(step.get("name") or step.get("id") or step.get("uses") or step.get("run", "")[:60])


def check_supported(steps: list[dict[str, Any]]) -> None:
    """Raise for any step this runner would not run as GitHub does."""
    for step in steps:
        label = _label(step)
        extra = set(step) - KNOWN_KEYS
        if extra:
            raise UnsupportedStepError(
                f"step {label!r} has {sorted(extra)}, which the watch does not run"
            )
        if "uses" in step:
            if not str(step["uses"]).startswith(CHECKOUT) or "run" in step:
                raise UnsupportedStepError(
                    f"step {label!r} uses {step['uses']!r}; only a checkout is known"
                )
            continue
        if "run" not in step:
            raise UnsupportedStepError(f"step {label!r} has neither `run:` nor a checkout")
        if step.get("shell") not in (None, "bash", "python"):
            raise UnsupportedStepError(f"step {label!r} runs in {step['shell']!r}")
        if "${{" in str(step["run"]):
            raise UnsupportedStepError(f"step {label!r} has an expression in `run:`")
        # Only a literal boolean: an expression or a string would be read as
        # the job stopping, where GitHub may let it go on.
        if not isinstance(step.get("continue-on-error", False), bool):
            raise UnsupportedStepError(
                f"step {label!r} sets `continue-on-error:` to {step['continue-on-error']!r}"
            )
        for value in (step.get("env") or {}).values():
            for expr in EXPRESSION.findall(str(value)):
                if expr not in ("github.token", "runner.temp") and not STEP_OUTCOME.fullmatch(expr):
                    raise UnsupportedStepError(f"step {label!r} reads ${{{{ {expr} }}}}")


def set_grace(steps: list[dict[str, Any]], days: int) -> tuple[list[dict[str, Any]], int]:
    """A copy of `steps` whose one `GRACE_DAYS` is `days`, and the rendered value."""
    changed = copy.deepcopy(steps)
    graced = [s for s in changed if GRACE_KEY in (s.get("env") or {})]
    if len(graced) != 1:
        raise UnsupportedStepError(
            f"the rendered `{JOB}` job sets {GRACE_KEY} in {len(graced)} steps, not one"
        )
    rendered = int(graced[0]["env"][GRACE_KEY])
    graced[0]["env"][GRACE_KEY] = str(days)
    return changed, rendered


def _resolve(value: Any, context: dict[str, str]) -> str:
    def one(m: re.Match[str]) -> str:
        expr = m.group(1)
        if expr in context:
            return context[expr]
        outcome = STEP_OUTCOME.fullmatch(expr)
        if outcome:
            # An outcome of a step that has not run is empty, as on GitHub.
            return context.get(f"outcome:{outcome.group(1)}", "")
        raise UnsupportedStepError(f"${{{{ {expr} }}}} is not known to the watch")

    return EXPRESSION.sub(one, str(value))


def run_steps(steps: list[dict[str, Any]], *, cwd: Path, token: str, temp: Path) -> JobRun:
    """Run `steps` in order in `cwd`, as a GitHub runner would run this job."""
    check_supported(steps)
    temp.mkdir(parents=True, exist_ok=True)
    context = {"github.token": token, "runner.temp": str(temp)}
    files = {k: temp / f"watch-{k.lower()}" for k in ("GITHUB_PATH", "GITHUB_ENV", "GITHUB_OUTPUT")}
    for f in files.values():
        f.write_text("", encoding="utf-8")
    added_path: list[str] = []
    errors: list[str] = []
    warnings: list[str] = []
    soft_failed: list[str] = []
    output: list[str] = []
    failed_step: str | None = None
    for n, step in enumerate(steps):
        if "uses" in step:
            continue  # the checkout: the render is the working tree already
        label = _label(step)
        env = dict(os.environ)
        env.update({k: str(v) for k, v in files.items()})
        env["RUNNER_TEMP"] = str(temp)
        env["PATH"] = os.pathsep.join([*reversed(added_path), env.get("PATH", "")])
        env.update({k: _resolve(v, context) for k, v in (step.get("env") or {}).items()})
        script = temp / f"step-{n}"
        script.write_text(str(step["run"]), encoding="utf-8")
        shell = step.get("shell")
        if shell == "python":
            argv = [sys.executable, str(script)]
        elif shell == "bash":
            argv = ["bash", "--noprofile", "--norc", "-eo", "pipefail", str(script)]
        else:
            argv = ["bash", "-e", str(script)]
        print(f"::group::{label}", flush=True)
        with subprocess.Popen(  # noqa: S603
            argv, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        ) as proc:
            for line in proc.stdout or ():
                print(line, end="", flush=True)
                output.append(line)
                m = ANNOTATION.match(line.rstrip("\n"))
                if m:
                    (errors if m.group(1) == "error" else warnings).append(m.group(2))
            code = proc.wait()
        print("::endgroup::", flush=True)
        added_path += [p for p in files["GITHUB_PATH"].read_text("utf-8").splitlines() if p]
        files["GITHUB_PATH"].write_text("", encoding="utf-8")
        if files["GITHUB_ENV"].read_text("utf-8").strip():
            raise UnsupportedStepError(
                f"step {label!r} writes GITHUB_ENV, which the watch does not carry"
            )
        outcome = "success" if code == 0 else "failure"
        if "id" in step:
            context[f"outcome:{step['id']}"] = outcome
        if code != 0:
            if step.get("continue-on-error") is True:
                soft_failed.append(label)
                continue
            failed_step = label
            break
    return JobRun(failed_step, soft_failed, errors, warnings, "".join(output))


def findings_due(
    errors: list[str], *, project_grace: int, today: datetime.date
) -> list[tuple[str, datetime.date]]:
    """Each finding the verdict named, with the first day a new project fails on it."""
    due = []
    for line in errors:
        for m in FINDING.finditer(line):
            since = datetime.date.fromisoformat(m.group("since"))
            due.append((m.group("finding"), since + datetime.timedelta(days=project_grace + 1)))
    return due


def issue_body(
    runs: dict[str, JobRun], *, ref: str, run_url: str, watch_grace: int, today: datetime.date
) -> str:
    grace = next((r.project_grace for r in runs.values() if r.project_grace), 14)
    out = [
        f"The weekly base-image watch failed: {run_url}",
        "",
        f"It rendered plinth-template `{ref}` and ran each instance's own `image` job with a"
        f" grace of {watch_grace} days. A new project's job fails at {grace}.",
    ]
    named = False
    for archetype, run in runs.items():
        if run.ok:
            continue
        out += ["", f"### {archetype}", ""]
        due = findings_due(run.errors, project_grace=run.project_grace or grace, today=today)
        named = named or bool(due)
        for finding, day in due:
            left = (day - today).days
            when = (
                "new projects fail on it now"
                if left <= 0
                else f"{left} days left: new projects fail on it from {day.isoformat()}"
            )
            out.append(f"- {finding}: {when}")
        if run.failed_step and not due:
            out.append(f"- The job stopped at `{run.failed_step}`; the run's log says why.")
        for step in run.soft_failed:
            out.append(
                f"- `{step}` did not finish, so nothing was scanned; the run's log says why."
                " A later run that finishes confirms the image."
            )
        if run.errors and not due:
            out += [f"- {line}" for line in run.errors]
    out += ["", "### What to do", ""]
    if named:
        out += [
            "1. Raise the digest in `template/Dockerfile.jinja`: merge Dependabot's `docker`"
            " pull request for `/template` if one is open, or raise it by hand. A Python package"
            " is raised in `template/uv.lock.jinja` instead.",
            "2. Release the template (CONTRIBUTING.md, Cut a release).",
            "3. Raise coolbress/plinth's template pin and release plinth, so that"
            " `/plinth:new-project` renders the new tag.",
        ]
    else:
        out.append(
            "No finding is named above, so nothing says yet whether the image needs raising:"
            " read the run's log. When the rendered `image` job changed shape, the watch"
            " (`src/template_render/image_watch.py`) changes with it."
        )
    out += [
        "",
        "Close this issue once a run of the watch passes. While it is open, a later failure"
        " comments here instead of opening another.",
    ]
    return "\n".join(out) + "\n"
