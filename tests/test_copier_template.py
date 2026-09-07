"""Render the template for real and check the result.

Reading copier.yml and checking that it looks right is not the same as
rendering it. Two defects got past the reading kind of test, both with a
successful render: the answers file template was missing, so `copier update`
could never run, and `_preserve_symlinks` was off, so `CLAUDE.md` became a
copy. `template_render.render()` is the harness that renders.

This file never reaches an instance: `_subdirectory: template` makes
`template/` the only thing rendered.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from template_render import TEMPLATE_ROOT, render

CONFIG = TEMPLATE_ROOT / "copier.yml"
SUBDIR = TEMPLATE_ROOT / "template"


@pytest.fixture(scope="module")
def rendered(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return render(tmp_path_factory.mktemp("cli"))


@pytest.fixture(scope="module")
def backend(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return render(tmp_path_factory.mktemp("backend"), archetype="backend", owner="someone")


# ── the configuration itself ──────────────────────────────────────────────


def test_render_target_is_the_subdirectory() -> None:
    """Without `_subdirectory` the root (the template's own CI, tests, copier.yml) is copied."""
    assert "_subdirectory: template" in CONFIG.read_text(encoding="utf-8")
    assert SUBDIR.is_dir()


def test_answers_file_template_exists() -> None:
    """Without it the instance gets no `.copier-answers.yml` and `copier update` cannot run."""
    template = SUBDIR / "{{ _copier_conf.answers_file }}.jinja"
    assert template.is_file(), "`{{ _copier_conf.answers_file }}.jinja` is missing"
    assert "_copier_answers" in template.read_text(encoding="utf-8"), "the answers are not written"


def test_archetype_question_exists_with_the_narrow_default() -> None:
    cfg = CONFIG.read_text(encoding="utf-8")
    assert "archetype:" in cfg, "no archetype question: the conditional files have no input"
    assert "default: cli" in cfg, (
        "the default is not the narrowest archetype. Widening adds files; narrowing "
        "deletes files nobody uses, which leaves stubs behind."
    )


def test_the_four_questions_are_kept() -> None:
    """`/plinth:new-project` passes project_name, license and archetype and derives the rest."""
    cfg = CONFIG.read_text(encoding="utf-8")
    for question in ("project_name:", "package_name:", "license:", "archetype:"):
        assert re.search(rf"^{question}", cfg, re.M), f"question {question} is gone"


# ── the render ────────────────────────────────────────────────────────────


def test_answers_file_is_actually_written(rendered: Path) -> None:
    answers = rendered / ".copier-answers.yml"
    assert answers.is_file(), "configured but not written: a failure only a render shows"
    assert "_src_path:" in answers.read_text(encoding="utf-8"), (
        "the instance does not record its template"
    )


def test_claude_md_stays_a_symlink(rendered: Path) -> None:
    """A copy drifts; the link is the reason it is a link."""
    link = rendered / "CLAUDE.md"
    assert link.is_symlink(), "CLAUDE.md is not a symbolic link (check _preserve_symlinks)"
    assert link.readlink().name == "AGENTS.md"


def test_template_internals_do_not_ship(rendered: Path) -> None:
    for leaked in ("copier.yml", "tests/test_copier_template.py", "src/template_render"):
        assert not (rendered / leaked).exists(), f"{leaked} leaked into the instance"


def test_cli_archetype_omits_service_only_files(rendered: Path) -> None:
    """`.env.example` and the image belong to a running service. Not deleted: never written."""
    for name in (".env.example", "Dockerfile", ".dockerignore", "src/probe/__main__.py"):
        assert not (rendered / name).exists(), f"{name} rendered for the cli archetype"


@pytest.mark.parametrize("archetype", ["backend", "data-ml"])
def test_service_archetypes_include_them(tmp_path: Path, archetype: str) -> None:
    out = render(tmp_path / f"svc-{archetype}", archetype=archetype)
    for name in (".env.example", "Dockerfile", ".dockerignore", "src/probe/__main__.py"):
        assert (out / name).is_file(), f"{name} missing for the {archetype} archetype"


#: What this generator can actually build. It emits a Python package; a web
#: front end or a mobile app would come out as a plain Python package, so
#: they are not offered.
SERVABLE = {"cli", "library", "backend", "data-ml"}


def _offered() -> set[str]:
    block = CONFIG.read_text(encoding="utf-8").split("\narchetype:", 1)[1]
    block = block.split("\nplinth_sha:", 1)[0]
    return set(re.findall(r"^\s{4}[^:\n]+:\s*([a-z][a-z0-9-]*)\s*$", block, re.M))


def test_we_only_offer_what_we_can_actually_build() -> None:
    """A question must not offer an answer the machine cannot honour."""
    assert _offered() == SERVABLE, _offered()


def test_the_door_can_read_the_archetype_choices() -> None:
    """`scripts/new-project.sh` in plinth reads the choices with a fixed sed pattern:
    four-space indented `Label: value` lines between `archetype:` and the next
    top-level key. Both scripts agree on that shape; this test holds this side."""
    text = CONFIG.read_text(encoding="utf-8")
    block = text.split("\narchetype:", 1)[1]
    block = re.split(r"\n[a-z_]", block, maxsplit=1)[0]
    found = re.findall(r"^    [^:]*: ([a-z][a-z0-9-]*)$", block, re.M)
    assert set(found) == SERVABLE, found


def test_the_conditional_archetypes_are_named_on_one_line() -> None:
    """plinth's floor checker reads this file over the network and takes the first
    `archetype not in [...]` as the set of archetypes that get an image and a
    `.env.example`. The literal must stay on one line, and name only those two."""
    text = CONFIG.read_text(encoding="utf-8")
    hits = re.findall(r"archetype not in \[([^]]*)\]", text)
    assert hits, "no `archetype not in [...]` condition in copier.yml"
    names = {n.strip("' ") for n in hits[0].split(",")}
    assert names == {"backend", "data-ml"}, names
    assert all(h == hits[0] for h in hits), "the conditions disagree with each other"


# ── the archetype pin and the plinth pin ──────────────────────────────────


def _plinth_sha() -> str:
    m = re.search(
        r'^plinth_sha:\n(?:.*\n)*?\s+default: "([0-9a-f]{40})"',
        CONFIG.read_text(encoding="utf-8"),
        re.M,
    )
    assert m, "copier.yml has no plinth_sha with a 40-hex default"
    return m.group(1)


def test_ci_calls_plinth_at_the_pinned_sha(rendered: Path) -> None:
    """The instance's `uses:` must point at plinth at a full commit SHA, never a tag."""
    sha = _plinth_sha()
    ci = (rendered / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    label = (rendered / ".github" / "workflows" / "label.yml").read_text(encoding="utf-8")
    assert f"uses: coolbress/plinth/.github/workflows/python-ci.yml@{sha}" in ci
    assert f"uses: coolbress/plinth/.github/workflows/pr-label.yml@{sha}" in label
    for text in (ci, label):
        for use in re.findall(r"^\s*uses:\s*(\S+)", text, re.M):
            assert re.search(r"@[0-9a-f]{40}$", use), f"not pinned to a commit: {use}"
    assert "coolbress/workflows" not in ci + label, "still calling the archived CI repository"


def test_ci_keeps_the_caller_job_named_ci(rendered: Path) -> None:
    ci = (rendered / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert re.search(r"^jobs:\n  ci:\n", ci, re.M), (
        "the caller job is not named `ci`; the check names break"
    )


def test_ci_runs_on_stacked_pull_requests(rendered: Path) -> None:
    """`pull_request: branches: [main]` skips a pull request whose base is another branch."""
    ci = (rendered / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    block = ci.split("pull_request:", 1)
    assert len(block) == 2, "no pull_request trigger"
    first = block[1].lstrip("\n").splitlines()[0]
    assert not first.strip().startswith("branches:"), (
        "a branches filter on pull_request: stacked PRs get no CI"
    )


def test_third_party_review_is_offered_but_off(rendered: Path) -> None:
    """The optional check is a commented block in ci.yml exposing the two inputs a
    consumer chooses, and nothing in the instance calls pr-review.yml for real."""
    ci = (rendered / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    commented = [ln for ln in ci.splitlines() if ln.startswith("#")]
    block = "\n".join(commented)
    assert f"uses: coolbress/plinth/.github/workflows/pr-review.yml@{_plinth_sha()}" in block
    assert "reviewer-logins:" in block
    assert "ask-comment:" in block
    assert "third-party.yml" in block, "the block does not say where it goes"
    live = [ln for ln in ci.splitlines() if not ln.lstrip().startswith("#")]
    assert not any("pr-review.yml" in ln for ln in live), "pr-review.yml is called for real"
    assert not (rendered / ".github" / "workflows" / "third-party.yml").exists()


def test_dependabot_watches_the_reusable_workflow_pin(rendered: Path) -> None:
    dep = (rendered / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    assert 'package-ecosystem: "github-actions"' in dep, (
        "no github-actions ecosystem: the plinth pin never rises"
    )
    assert 'package-ecosystem: "uv"' in dep


def test_service_archetype_dependabot_watches_the_image(backend: Path, rendered: Path) -> None:
    assert 'package-ecosystem: "docker"' in (backend / ".github" / "dependabot.yml").read_text(
        encoding="utf-8"
    )
    assert 'package-ecosystem: "docker"' not in (rendered / ".github" / "dependabot.yml").read_text(
        encoding="utf-8"
    )


# ── Claude Code settings ──────────────────────────────────────────────────


def _settings(out: Path) -> dict[str, object]:
    data: dict[str, object] = json.loads(
        (out / ".claude" / "settings.json").read_text(encoding="utf-8")
    )
    return data


def test_settings_suggest_the_plinth_marketplace(rendered: Path) -> None:
    marketplaces = _settings(rendered)["extraKnownMarketplaces"]
    assert isinstance(marketplaces, dict)
    plinth = marketplaces["plinth"]
    assert plinth == {"source": {"source": "github", "repo": "coolbress/plinth"}}, plinth


def test_settings_deny_what_the_checks_cannot_undo(rendered: Path) -> None:
    permissions = _settings(rendered)["permissions"]
    assert isinstance(permissions, dict)
    deny = permissions["deny"]
    wants = {
        "force push": ("Bash(git push --force", "Bash(git push -f"),
        "rm -rf": ("Bash(rm -rf",),
        "gh auth token": ("Bash(gh auth token",),
        ".env": ("Read(./.env)",),
        "gh config": ("Read(~/.config/gh",),
    }
    for what, prefixes in wants.items():
        assert any(d.startswith(prefixes) for d in deny), f"nothing denies {what}: {deny}"


def test_settings_allow_the_checks_without_a_prompt(rendered: Path) -> None:
    """The point of the allow list: the commands AGENTS.md tells the agent to run
    never prompt, so the prompts that remain mean something."""
    permissions = _settings(rendered)["permissions"]
    assert isinstance(permissions, dict)
    allow = permissions["allow"]
    for cmd in (
        "uv sync",
        "uv run pytest",
        "uv run ruff",
        "uv run mypy",
        "uv build",
        "git status",
        "git diff",
        "git log",
        "gh pr view",
        "gh pr checks",
        "gh issue list",
    ):
        assert any(a.startswith(f"Bash({cmd}") for a in allow), f"{cmd} would prompt: {allow}"
    assert not any(a.startswith(("Bash(git push", "Bash(gh pr merge", "Bash(rm")) for a in allow), (
        allow
    )


def test_settings_do_not_block_env_example(backend: Path) -> None:
    """`Read(./.env.*)` also matched `.env.example`, the one file that is meant to
    be read. No deny rule may match it, and `.env` itself must still be denied."""
    from fnmatch import fnmatchcase

    permissions = _settings(backend)["permissions"]
    assert isinstance(permissions, dict)
    reads = [d[len("Read(") : -1] for d in permissions["deny"] if d.startswith("Read(./")]
    assert reads, "no Read deny at all"
    blocking = [p for p in reads if fnmatchcase("./.env.example", p)]
    assert not blocking, f"these deny rules block .env.example: {blocking}"
    assert any(fnmatchcase("./.env", p) for p in reads), ".env itself is not denied"
    assert any(fnmatchcase("./.env.local", p) for p in reads), ".env.local is readable"
    sandbox = _settings(backend)["sandbox"]
    assert isinstance(sandbox, dict)
    filesystem = sandbox["filesystem"]
    assert isinstance(filesystem, dict)
    deny_read = filesystem["denyRead"]
    assert not any(fnmatchcase("./.env.example", p) for p in deny_read), deny_read
    assert any(fnmatchcase("./.env", p) for p in deny_read), deny_read
    # Measured 2026-09-07 (Claude Code 2.1.263, macOS): `~/.config/gh` in denyRead
    # stops `gh` itself from starting inside the sandbox ("failed to read
    # configuration: open ~/.config/gh/config.yml: operation not permitted"),
    # and every `gh` command AGENTS.md asks for with it. The token is kept out
    # of the context by the Read deny and the `gh auth token` deny instead.
    assert not any("/.config/gh" in p for p in deny_read), "denyRead on ~/.config/gh breaks gh"
    # Writes outside the project are denied by the sandbox's default; a project
    # allowWrite would widen that, and a denyWrite on a parent of the project
    # would close the project itself. Neither is set.
    assert "allowWrite" not in filesystem
    assert "denyWrite" not in filesystem
    assert "enabled" not in sandbox, (
        "sandbox.enabled is a user setting; the project must not set it"
    )


def test_no_instance_hook(rendered: Path) -> None:
    """The default install has no hooks; the instance does not add one."""
    assert "hooks" not in _settings(rendered)
    assert not (rendered / ".claude" / "session-start.sh").exists()


def test_output_style_ships_but_is_not_applied(rendered: Path) -> None:
    style = rendered / ".claude" / "output-styles" / "non-engineer.md"
    assert style.is_file()
    head = style.read_text(encoding="utf-8").split("---", 2)[1]
    assert "keep-coding-instructions: true" in head, (
        "without keep-coding-instructions the style replaces the engineering instructions wholesale"
    )
    assert "outputStyle" not in _settings(rendered), "the style is applied by default; it is opt-in"


# ── the document set ──────────────────────────────────────────────────────


def test_floor_documents_are_present(rendered: Path) -> None:
    for name in (
        "README.md",
        "AGENTS.md",
        "CONTRIBUTING.md",
        "CHANGELOG.md",
        "SECURITY.md",
        "LICENSE",
        ".github/PULL_REQUEST_TEMPLATE.md",
        ".github/dependabot.yml",
        ".gitattributes",
    ):
        assert (rendered / name).is_file(), f"{name} is not in the instance"
    for form in ("bug", "feature", "task", "config"):
        assert (rendered / ".github" / "ISSUE_TEMPLATE" / f"{form}.yml").is_file(), (
            f"{form}.yml missing"
        )
    for name in ("domain.md", "issue-tracker.md", "triage-labels.md"):
        assert (rendered / "docs" / "agents" / name).is_file(), f"docs/agents/{name} missing"


def test_agents_md_stays_short_and_says_what_matters(rendered: Path) -> None:
    text = (rendered / "AGENTS.md").read_text(encoding="utf-8")
    lines = text.splitlines()
    assert len(lines) <= 60, (
        f"AGENTS.md is {len(lines)} lines; everything in it is loaded every turn"
    )
    for must in (
        "/ask-matt",
        "/implement #N",
        "diagnosing-bugs",
        "/plinth:arsenal",
        "Review findings:",
        "Simplify within the agreed behaviour",
        "## Code Review Rules",
        "irreversible or reaching others, recoverable with one command, or hypothetical",
        "Assisted-by:",
        "Do not invent types",
        "a description that no longer matches the diff",
    ):
        assert must in text, f"AGENTS.md no longer says: {must}"
    assert "when planning" not in text.lower(), "the planning block moved out of AGENTS.md"


def test_contributing_and_readme_list_every_check_agents_lists(rendered: Path) -> None:
    """The same command list lives in three files; two of them drifted once."""
    agents = (rendered / "AGENTS.md").read_text(encoding="utf-8")
    heads = set(re.findall(r"uv (?:run )?[a-z]+(?: (?:check|format))?", agents)) - {"uv sync"}
    assert heads, "no check command found in AGENTS.md"
    for doc in ("CONTRIBUTING.md", "README.md"):
        text = (rendered / doc).read_text(encoding="utf-8")
        missing = sorted(h for h in heads if h not in text)
        assert not missing, f"{doc} does not list {missing}"


def test_contributing_says_the_description_is_the_squash_commit(rendered: Path) -> None:
    text = (rendered / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert "squash commit" in text
    assert "Assisted-by:" in text
    assert "read the description against the final diff" in text
    for t in ("feat", "fix", "docs", "refactor", "revert"):
        assert f"`{t}`" in text, f"{t} is not in the type list"


def test_owner_reaches_pyproject(backend: Path, rendered: Path) -> None:
    """The author and the URLs are the owner who created the repository, not the template's."""
    with_owner = (backend / "pyproject.toml").read_text(encoding="utf-8")
    assert 'authors = [{ name = "someone" }]' in with_owner
    assert 'Homepage = "https://github.com/someone/probe"' in with_owner
    assert "coolbress" not in with_owner
    without = (rendered / "pyproject.toml").read_text(encoding="utf-8")
    assert "authors" not in without, "an unknown owner rendered an author"
    assert "[project.urls]" not in without, "an unknown owner rendered URLs"
    assert "coolbress" not in without


def test_the_old_shape_is_gone(rendered: Path, backend: Path) -> None:
    """Removed on review: the session hook, the logging module and its test, and
    the policy tests that `ci / floor-check` now runs. What stays in the app's
    tests is a package smoke test and tree hygiene."""
    for out in (rendered, backend):
        names = sorted(p.name for p in (out / "tests").glob("*.py"))
        assert names == ["test_probe.py", "test_tree_hygiene.py"], names
        assert not (out / "src" / "probe" / "_logging.py").exists()


def test_the_entry_point_logs_json(backend: Path) -> None:
    text = (backend / "src" / "probe" / "__main__.py").read_text(encoding="utf-8")
    assert "class JsonFormatter" in text
    assert "json.dumps" in text


# ── language ──────────────────────────────────────────────────────────────

#: Words that must not appear anywhere in this repository: Korean text (product
#: text is English), the codenames of experiment repositories, paths into an
#: archived Korean evidence repository, and the archived repositories this
#: template stands apart from. Same list as plinth's docs gate.
FORBIDDEN = (
    r"[ㄱ-힝]",
    r"goppi",
    r"gingoa",
    r"claudeck",
    r"codex-native",
    r"divcal",
    r"direction/[0-9]{2}",
    r"coolbress/workflows",
    r"coolbress/project-template",
    r"coolbress/standards",
)


def _tracked_text() -> dict[str, str]:
    out = subprocess.run(
        ["git", "ls-files"],  # noqa: S607
        cwd=TEMPLATE_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    texts = {}
    for rel in out:
        path = TEMPLATE_ROOT / rel
        if (
            not path.is_file()
            or path.suffix in {".lock", ".pyc"}
            or path.name.startswith("test_copier")
        ):
            continue
        try:
            texts[rel] = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
    return texts


def _hits(pattern: re.Pattern[str], texts: dict[str, str]) -> dict[str, list[str]]:
    hits = {}
    for rel, body in texts.items():
        found = [
            f"{i}: {ln.strip()[:80]}"
            for i, ln in enumerate(body.splitlines(), 1)
            if pattern.search(ln)
        ]
        if found:
            hits[rel] = found
    return hits


def test_no_internal_vocabulary_in_the_template() -> None:
    """Everything an instance receives, and this repository's own text, is English
    and free of internal names. Regexes, so a planted word is caught first."""
    forbidden = re.compile("|".join(FORBIDDEN))
    assert forbidden.search("see direction/04 and goppi"), "the gate does not catch a planted word"
    texts = _tracked_text()
    assert texts, "no tracked text at all"
    assert not _hits(forbidden, texts), (
        f"internal vocabulary in public text: {_hits(forbidden, texts)}"
    )


#: `{% %}` is jinja only. `{{ }}` overlaps with Actions expressions `${{ }}` and
#: Go templates, so it is a leak only when an answer variable is inside.
ANSWER_VARS = (
    "package_name",
    "project_name",
    "archetype",
    "license",
    "owner",
    "plinth_sha",
    "_copier",
)
UNRENDERED = re.compile(r"\{%|" + r"\{\{[^}]*(?:" + "|".join(ANSWER_VARS) + r")[^}]*\}\}")


@pytest.mark.parametrize("archetype", sorted(SERVABLE))
def test_no_unrendered_jinja_survives_into_an_instance(tmp_path: Path, archetype: str) -> None:
    """A file that is not `.jinja` is copied as is; a condition written in it leaks
    into the instance as text, and a YAML file with `{% if %}` in it is broken."""
    out = render(tmp_path / f"jinja-{archetype}", archetype=archetype)
    leaked = {}
    for f in sorted(out.rglob("*")):
        if not f.is_file() or ".git" in f.parts or f.suffix in {".lock", ".pyc"}:
            continue
        try:
            body = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        hits = [
            f"{i}: {line.strip()[:80]}"
            for i, line in enumerate(body.splitlines(), 1)
            if UNRENDERED.search(line)
        ]
        if hits:
            leaked[f.relative_to(out).as_posix()] = hits
    assert not leaked, f"template syntax survived into the instance: {leaked}"


# ── name substitution ─────────────────────────────────────────────────────


def test_repository_name_becomes_a_python_package_name(tmp_path: Path) -> None:
    """`my.app` -> `my_app`: a repository name and a package name follow different rules."""
    out = render(tmp_path / "dotted", project_name="my.app", owner="someone")
    assert (out / "src" / "my_app" / "__init__.py").is_file()
    assert (out / "tests" / "test_my_app.py").is_file()
    assert "from my_app import" in (out / "tests" / "test_my_app.py").read_text(encoding="utf-8")
    pyproject = (out / "pyproject.toml").read_text(encoding="utf-8")
    assert 'name = "my_app"' in pyproject
    assert "someone/my.app" in pyproject, (
        "the URL keeps the repository name; it is GitHub's, not Python's"
    )


def test_license_answer_reaches_pyproject_and_the_license_file(
    tmp_path: Path, rendered: Path
) -> None:
    """Measured 2026-09-07: Apache-2.0 in pyproject with an MIT LICENSE beside it."""
    out = render(tmp_path / "apache", license="Apache-2.0", owner="someone")
    assert 'license = "Apache-2.0"' in (out / "pyproject.toml").read_text(encoding="utf-8")
    year = time.strftime("%Y")  # the template takes it from copier's strftime filter, same clock
    apache = (out / "LICENSE").read_text(encoding="utf-8")
    assert apache.lstrip().startswith("Apache License"), apache[:80]
    assert f"Copyright {year} someone" in apache
    mit = (rendered / "LICENSE").read_text(encoding="utf-8")
    assert mit.startswith("MIT License"), mit[:80]
    assert f"Copyright (c) {year} the probe authors" in mit, (
        "no owner: the project's authors hold it"
    )
    assert "coolbress" not in apache + mit


def test_lockfile_carries_the_package_name(tmp_path: Path) -> None:
    """A mismatch fails `uv sync --locked` on the new repository's first pull request."""
    out = render(tmp_path / "locked", project_name="my.app")
    assert 'name = "my_app"' in (out / "uv.lock").read_text(encoding="utf-8")


@pytest.mark.parametrize("bad", ["9lives", "class", "my+app"])
def test_impossible_names_are_refused_before_anything_is_written(tmp_path: Path, bad: str) -> None:
    dest = tmp_path / "bad"
    with pytest.raises(Exception):  # noqa: B017,PT011 — the type copier raises varies by version
        render(dest, project_name=bad)
    assert not dest.exists() or not any(dest.iterdir()), (
        f"{bad} was refused but files were left behind"
    )


# ── end to end ────────────────────────────────────────────────────────────

#: The archetypes whose file sets differ. Every `_exclude` condition is
#: `archetype not in ['backend', 'data-ml']`, so there are two sets: {cli,
#: library} and {backend, data-ml}. One representative each covers both.
E2E_ARCHETYPES = ("cli", "backend")


def test_the_e2e_representatives_still_cover_every_archetype(tmp_path: Path) -> None:
    sets = {}
    for archetype in SERVABLE:
        out = render(tmp_path / f"cover-{archetype}", archetype=archetype)
        sets[archetype] = frozenset(
            f.relative_to(out).as_posix()
            for f in out.rglob("*")
            if f.is_file() and ".git" not in f.parts and "src/" not in f.relative_to(out).as_posix()
        )
    groups: dict[frozenset[str], list[str]] = {}
    for archetype, files in sets.items():
        groups.setdefault(files, []).append(archetype)
    assert len(groups) == len(E2E_ARCHETYPES), [sorted(v) for v in groups.values()]
    for reps in groups.values():
        assert any(r in E2E_ARCHETYPES for r in reps), f"no representative for {reps}"


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv is not installed")
@pytest.mark.parametrize("archetype", E2E_ARCHETYPES)
def test_generated_project_passes_its_own_checks(tmp_path: Path, archetype: str) -> None:
    """A render that succeeds and a generated repository that is green are two
    different sentences. `uv.lock` carries the project name; a mismatch fails
    the first pull request behind a wall that then stays shut."""
    out = render(
        tmp_path / f"e2e-{archetype}", project_name="my.app", archetype=archetype, owner="someone"
    )
    for step in (
        ["uv", "sync", "--locked", "--quiet"],
        ["uv", "run", "--quiet", "ruff", "check", "."],
        ["uv", "run", "--quiet", "ruff", "format", "--check", "."],
        ["uv", "run", "--quiet", "mypy", "."],
        ["uv", "run", "--quiet", "pytest", "-q"],
        ["uv", "build", "--quiet"],
    ):
        done = subprocess.run(step, cwd=out, capture_output=True, text=True, check=False)  # noqa: S603
        assert done.returncode == 0, (
            f"{' '.join(step)} failed in the generated project\n{done.stdout}\n{done.stderr}"
        )


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv is not installed")
def test_generated_project_passes_the_floor_check(tmp_path: Path) -> None:
    """plinth's `ci / floor-check` runs `scripts/floor-check.py` at the pinned
    commit against the instance. The same checker, the same commit, offline."""
    checker = tmp_path / "floor-check.py"
    url = (
        f"https://raw.githubusercontent.com/coolbress/plinth/{_plinth_sha()}/scripts/floor-check.py"
    )
    fetched = subprocess.run(  # noqa: S603
        ["curl", "-fsSL", "--retry", "3", "-o", str(checker), url],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    if fetched.returncode != 0:
        assert not os.environ.get("CI"), f"could not fetch the checker on CI: {fetched.stderr}"
        pytest.skip("could not fetch floor-check.py (offline)")
    for archetype in E2E_ARCHETYPES:
        out = render(tmp_path / f"floor-{archetype}", archetype=archetype, owner="someone")
        done = subprocess.run(  # noqa: S603
            ["python3", str(checker), "--root", str(out), "--no-network"],  # noqa: S607
            capture_output=True,
            text=True,
            check=False,
        )
        assert done.returncode == 0, (
            f"floor check failed for {archetype}:\n{done.stdout}\n{done.stderr}"
        )


def test_service_archetype_image_actually_builds_and_runs(tmp_path: Path) -> None:
    """The one test that tells the Dockerfile from a stub: build it and run it.
    Skipped only on a machine without docker; CI has it, and the assertion
    below makes sure the skip cannot hide there."""
    if shutil.which("docker") is None:
        assert not os.environ.get("CI"), "CI has no docker: the image test tried to skip silently"
        pytest.skip("docker is not installed (a laptop); on CI the assertion above stops this")

    out = render(tmp_path / "svc", archetype="backend", owner="someone")
    tag = "plinth-template-probe:test"
    built = subprocess.run(  # noqa: S603
        ["docker", "build", "-t", tag, "."],  # noqa: S607
        cwd=out,
        capture_output=True,
        text=True,
        check=False,
    )
    assert built.returncode == 0, f"the image does not build:\n{built.stderr[-2000:]}"
    ran = subprocess.run(  # noqa: S603
        ["docker", "run", "--rm", tag],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    assert ran.returncode == 0, f"the image does not run:\n{ran.stderr[-2000:]}"
    first = ran.stdout.strip().splitlines()[0]
    record = json.loads(first)
    assert record["message"] == "started", first
    assert record["greeting"] == "Hello, world!", first
    whoami = subprocess.run(  # noqa: S603
        ["docker", "run", "--rm", "--entrypoint", "id", tag, "-un"],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    assert whoami.stdout.strip() != "root", "the container runs as root"
