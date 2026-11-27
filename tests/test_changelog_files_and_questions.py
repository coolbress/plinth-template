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

Sections released before this rule stay as published (decisions in force),
v1.52.0 among them, cut before the rule landed: it holds from the first
release after v1.52.0, and for `[Unreleased]`.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]

from template_render import TEMPLATE_ROOT

HEADING = "### Files and questions"
LAST_BEFORE_THE_RULE = (1, 52, 0)
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


def _git(*args: str, cwd: Path = TEMPLATE_ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def _tagged(tag: str) -> bool:
    return _git("rev-parse", "-q", "--verify", f"refs/tags/{tag}").returncode == 0


def _to_check(sections: list[tuple[str, str]]) -> tuple[str, str, str] | None:
    """(title, body, tag to compare from): the newest numbered section while it
    has no tag yet, the release being cut, against the section before it;
    otherwise `[Unreleased]` against the newest numbered section's tag."""
    numbered = [(t, b) for t, b in sections if _version(t)]
    if numbered and not _tagged("v" + numbered[0][0].strip("[]")) and len(numbered) > 1:
        return numbered[0][0], numbered[0][1], "v" + numbered[1][0].strip("[]")
    unreleased = next((b for t, b in sections if t == "[Unreleased]"), "")
    if numbered and unreleased.strip():
        return "[Unreleased]", unreleased, "v" + numbered[0][0].strip("[]")
    return None


def _changed_since(tag: str, cwd: Path = TEMPLATE_ROOT) -> set[str]:
    """The rendered names of the files `template/` changed since `tag`. Read
    NUL-separated (`-z`): without it git quotes a path holding `"`, such as
    `{{ "" }}.env.example.jinja`, and the name would not map."""
    diff = _git(
        "diff", "--name-only", "-z", "--no-renames", f"{tag}..HEAD", "--", "template/", cwd=cwd
    )
    assert diff.returncode == 0, diff.stderr
    return {rendered_name(p) for p in diff.stdout.split("\0") if p}


def test_a_changed_path_with_a_quote_maps_to_its_rendered_name(tmp_path: Path) -> None:
    def git(*args: str) -> None:
        assert _git(*args, cwd=tmp_path).returncode == 0

    git("init", "-q")
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "a")
    git("tag", "base")
    (tmp_path / "template").mkdir()
    (tmp_path / "template" / '{{ "" }}.env.example.jinja').write_text("x\n", encoding="utf-8")
    git("add", "-A")
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "b")
    assert _changed_since("base", cwd=tmp_path) == {".env.example"}


def test_the_list_is_the_template_diff_since_the_last_tag() -> None:
    """The release being cut (its section written, its tag not yet made) or
    else `[Unreleased]`, against the tag before it. Checked where that tag is
    in the clone: by hand, in the release step (CONTRIBUTING.md, Cut a
    release, step 2). CI's checkout has no tags, so there it is skipped,
    saying so."""
    target = _to_check(_sections(CHANGELOG.read_text(encoding="utf-8")))
    if target is None:
        pytest.skip("no section to compare: no [Unreleased] entries and no untagged release")
    title, body, tag = target
    if not _tagged(tag):
        pytest.skip(f"{tag} is not in this clone (CI fetches no tags); run it in the release step")
    changed = _changed_since(tag)
    old = _git("show", f"{tag}:copier.yml")
    assert old.returncode == 0, old.stderr
    now = _questions((TEMPLATE_ROOT / "copier.yml").read_text(encoding="utf-8"))
    added = now - _questions(old.stdout)
    files, questions, _ = _items(_block(body) or [])
    assert files == changed, (
        f"{title} lists but {tag}..HEAD did not change: {sorted(files - changed)}; "
        f"changed but not listed: {sorted(changed - files)}"
    )
    assert questions == added, (
        f"{title} lists {sorted(questions)}; added since {tag}: {sorted(added)}"
    )


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
    assert _ruled("[1.52.0]", "x") is False
    assert _ruled("[1.53.0]", "x") is True
    assert _ruled("[Unreleased]", "\n") is False
