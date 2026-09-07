"""Nothing that must not be in the tree actually is.

`.gitignore` prevents, it does not guarantee: `git add -f` goes past it, and a
file tracked before the rule was written stays tracked after. So the tracked
files are read from git and checked for real.

Only tracked files count. A `dist/` or `.venv/` lying around locally is normal;
the problem is when it is committed.
"""

from __future__ import annotations

import subprocess

import pytest

#: Paths under these prefixes are build output or an environment.
FORBIDDEN_PREFIX = ("dist/", "build/", ".venv/", "site-packages/")

#: Files with these endings are build output.
FORBIDDEN_SUFFIX = (".pyc", ".pyo", ".pyd", ".so", ".whl", ".tar.gz", ".egg-info")

#: Build output wherever it sits in the path.
FORBIDDEN_PART = ("__pycache__/", ".mypy_cache/", ".pytest_cache/", ".ruff_cache/")


def tracked() -> list[str]:
    """The tracked files, from git rather than the file system."""
    # The arguments are literals, so only S607 (partial path) applies, and an
    # absolute path would be worse: git lives in different places on CI and on
    # a laptop.
    done = subprocess.run(
        ["git", "ls-files"],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode != 0:
        # Narrow skip: the template's own tests run pytest in a freshly
        # rendered directory that is not a git repository yet. Only that case
        # skips; any other failure is raised, because a check that turns green
        # for no reason is worse than none.
        if "not a git repository" in done.stderr.lower():
            pytest.skip("not a git repository (a fresh render): nothing is tracked yet")
        raise AssertionError(f"`git ls-files` failed: {done.stderr.strip()}")
    return [line for line in done.stdout.splitlines() if line]


def test_no_real_dotenv_is_tracked() -> None:
    """`.env.example` is committed. A `.env` with real values never is."""
    leaked = [
        p
        for p in tracked()
        if (name := p.rsplit("/", 1)[-1]) == ".env"
        or (name.startswith(".env.") and name != ".env.example")
    ]
    assert not leaked, (
        f".env files are committed: {leaked}\n"
        "`git add -f` and commits older than the ignore rule get past .gitignore. "
        "If the file held real values they are in the history: rotate the keys."
    )


def test_no_build_artifact_is_tracked() -> None:
    junk = [
        p
        for p in tracked()
        if p.startswith(FORBIDDEN_PREFIX)
        or p.endswith(FORBIDDEN_SUFFIX)
        or any(part in p for part in FORBIDDEN_PART)
    ]
    assert not junk, (
        f"build output is committed: {junk}\n"
        "Build output is made by the build; committed, it inflates diffs and buries review."
    )


def test_personal_claude_settings_are_not_tracked() -> None:
    """`.claude/settings.json` belongs to the team; `settings.local.json` to one person.

    Claude Code adds the local file to the global git excludes of one machine.
    That protects the machine, not the repository: another machine or another
    contributor is not covered. Committed, one person's permission approvals
    become everyone's.
    """
    personal = [p for p in tracked() if p.endswith(".claude/settings.local.json")]
    assert not personal, (
        f"personal settings are tracked: {personal}\n"
        "One person's approvals reach everyone. Add it to .gitignore and `git rm --cached` it."
    )
