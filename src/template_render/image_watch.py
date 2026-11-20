"""Run a rendered project's `image` job steps, for the base-image watch (#266).

The pinned base images in `template/Dockerfile.jinja` age, and a new
project's `image` job fails once a high or critical fix is more than 14 days
older than the image. The weekly watch runs that render's own `image` job
steps in order, the verdict included; this module is the part that runs
them.

The verdict logic is never copied here: the steps are read from the rendered
`.github/workflows/ci.yml`. The runner knows the few things those steps use
(a checkout, `run:` in bash or Python, `continue-on-error`, `$GITHUB_PATH`,
three expressions); anything else stops it, because a step run differently
from GitHub would pass or fail for a reason the instance does not have.
"""

from __future__ import annotations

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
CHECKOUT = "actions/checkout@"
JOB_KEYS = frozenset({"name", "runs-on", "timeout-minutes", "permissions", "steps"})
KNOWN_KEYS = frozenset({"name", "id", "run", "shell", "env", "continue-on-error", "uses", "with"})
EXPRESSION = re.compile(r"\$\{\{\s*(.*?)\s*\}\}")
STEP_OUTCOME = re.compile(r"steps\.([A-Za-z_][\w-]*)\.outcome")
#: Every annotation the steps print.
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
