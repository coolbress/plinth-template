"""Each release section says which rendered files an update changes and which
questions it adds, under one fixed heading (#359).

coolbress/plinth's update plan quotes the block under that heading for each
release between the tag a project records and the one plinth targets
(coolbress/plinth#1184), so its text is fixed: `### Files and questions`.
Under it, one item per line:

    - `AGENTS.md`                a rendered file the release changes, adds or deletes
    - question `records_language` a copier question the release adds
    - None.                      neither

A file is named by its path under `template/` as the instance has it: no
`.jinja`, a `{% if %}` name as the name it renders, `{{ package_name }}` as
`<package>`, and the answers file as `.copier-answers.yml`.

Sections released before this rule stay as published (decisions in force):
the rule holds from the first release after v1.51.0, and for `[Unreleased]`.
"""

from __future__ import annotations

import re
import subprocess

import pytest
import yaml  # type: ignore[import-untyped]

from template_render import TEMPLATE_ROOT

HEADING = "### Files and questions"
LAST_BEFORE_THE_RULE = (1, 51, 0)
CHANGELOG = TEMPLATE_ROOT / "CHANGELOG.md"
_ITEM = re.compile(
    r"^- (?:`(?P<file>[^`]+)`|question `(?P<question>[A-Za-z_][A-Za-z0-9_]*)`|(?P<none>None\.))$"
)


def _sections(text: str) -> list[tuple[str, str]]:
    """(title, body) of each `## ` section, in order: `[Unreleased]` or `[x.y.z]`."""
    parts = re.split(r"^## ", text, flags=re.M)[1:]
    return [
        (p.split("\n", 1)[0].split(" ", 1)[0], p.split("\n", 1)[1] if "\n" in p else "")
        for p in parts
    ]


def _version(title: str) -> tuple[int, ...] | None:
    m = re.fullmatch(r"\[(\d+)\.(\d+)\.(\d+)\]", title)
    return tuple(int(g) for g in m.groups()) if m else None


def _ruled(title: str, body: str) -> bool:
    v = _version(title)
    if v is None:
        return title == "[Unreleased]" and bool(body.strip())
    return v > LAST_BEFORE_THE_RULE


def _block(body: str) -> list[str] | None:
    """The lines under HEADING, up to the next `### ` or the end; None without it."""
    if f"\n{HEADING}\n" not in f"\n{body}":
        return None
    after = f"\n{body}".split(f"\n{HEADING}\n", 1)[1]
    return [ln for ln in after.split("\n### ", 1)[0].splitlines() if ln.strip()]


def _items(block: list[str]) -> tuple[set[str], set[str], list[str]]:
    """(files, questions, lines that are not an item); `None.` must stand alone."""
    files, questions, bad = set(), set(), []
    for ln in block:
        m = _ITEM.match(ln)
        if not m:
            bad.append(ln)
        elif m["file"]:
            files.add(m["file"])
        elif m["question"]:
            questions.add(m["question"])
    if any(ln == "- None." for ln in block) and len(block) != 1:
        bad.append("`- None.` with other items")
    return files, questions, bad


def _questions(config_text: str) -> set[str]:
    return {k for k in yaml.safe_load(config_text) if not k.startswith("_")}


def rendered_name(template_path: str) -> str:
    """The path an instance has for `template/<path>`."""
    p = template_path.removeprefix("template/")
    p = p.replace("{{ _copier_conf.answers_file }}", ".copier-answers.yml")
    p = p.replace('{{ "" }}', "").replace("{{ package_name }}", "<package>")
    p = re.sub(r"\{%[^%]*%\}", "", p)
    return p.removesuffix(".jinja")


def _ruled_sections() -> list[tuple[str, str]]:
    return [(t, b) for t, b in _sections(CHANGELOG.read_text(encoding="utf-8")) if _ruled(t, b)]


def test_each_section_after_the_rule_has_the_heading_and_only_items_under_it() -> None:
    problems = []
    for title, body in _ruled_sections():
        block = _block(body)
        if block is None:
            problems.append(f"{title} has no `{HEADING}`")
            continue
        _, _, bad = _items(block)
        if not block:
            problems.append(
                f"{title}: `{HEADING}` lists nothing; write `- None.` when there is nothing"
            )
        problems += [f"{title}: not an item: {ln}" for ln in bad]
    assert problems == [], problems


def test_each_question_it_names_is_a_question_in_copier_yml() -> None:
    known = _questions((TEMPLATE_ROOT / "copier.yml").read_text(encoding="utf-8"))
    unknown = [
        f"{title}: {q}"
        for title, body in _ruled_sections()
        for q in sorted(_items(_block(body) or [])[1])
        if q not in known
    ]
    assert unknown == [], f"not a key in copier.yml: {unknown}"


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=TEMPLATE_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_the_unreleased_list_is_the_template_diff_since_the_last_tag() -> None:
    """Checked where the last tag is in the clone: by hand, in the release step
    (CONTRIBUTING.md, Cut a release, step 2). CI's checkout has no tags, so
    there it is skipped, saying so."""
    sections = _sections(CHANGELOG.read_text(encoding="utf-8"))
    body = next((b for t, b in sections if t == "[Unreleased]"), "")
    last = next((t for t, _ in sections if _version(t)), None)
    if not body.strip() or last is None:
        pytest.skip("no [Unreleased] entries, or no released section to compare from")
    tag = "v" + last.strip("[]")
    if _git("rev-parse", "-q", "--verify", f"refs/tags/{tag}").returncode != 0:
        pytest.skip(f"{tag} is not in this clone (CI fetches no tags); run it in the release step")
    diff = _git("diff", "--name-only", "--no-renames", f"{tag}..HEAD", "--", "template/")
    assert diff.returncode == 0, diff.stderr
    changed = {rendered_name(p) for p in diff.stdout.splitlines() if p}
    old = _git("show", f"{tag}:copier.yml")
    assert old.returncode == 0, old.stderr
    added = _questions((TEMPLATE_ROOT / "copier.yml").read_text(encoding="utf-8")) - _questions(
        old.stdout
    )
    files, questions, _ = _items(_block(body) or [])
    assert files == changed, (
        f"listed but not changed: {sorted(files - changed)}; "
        f"changed but not listed: {sorted(changed - files)}"
    )
    assert questions == added, f"listed: {sorted(questions)}; added since {tag}: {sorted(added)}"


@pytest.mark.parametrize(
    ("path", "name"),
    [
        ("template/AGENTS.md.jinja", "AGENTS.md"),
        ("template/{{ _copier_conf.answers_file }}.jinja", ".copier-answers.yml"),
        ('template/{{ "" }}.env.example.jinja', ".env.example"),
        ("template/src/{{ package_name }}/app.py.jinja", "src/<package>/app.py"),
        (
            "template/.github/workflows/{% if archetype == 'backend' %}release.yml{% endif %}",
            ".github/workflows/release.yml",
        ),
        ("template/.streamlit/config.toml", ".streamlit/config.toml"),
    ],
)
def test_a_template_path_is_named_as_the_instance_has_it(path: str, name: str) -> None:
    assert rendered_name(path) == name


def test_a_section_without_the_heading_or_with_a_stray_line_is_refused() -> None:
    assert _block("### Added\n\n- x\n") is None
    files, questions, bad = _items(
        ["- `AGENTS.md`", "- question `records_language`", "- AGENTS.md"]
    )
    assert files == {"AGENTS.md"}
    assert questions == {"records_language"}
    assert bad == ["- AGENTS.md"]
    assert _items(["- None.", "- `AGENTS.md`"])[2] == ["`- None.` with other items"]
    assert _ruled("[1.51.0]", "x") is False
    assert _ruled("[1.52.0]", "x") is True
    assert _ruled("[Unreleased]", "\n") is False
