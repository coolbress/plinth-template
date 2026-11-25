"""The `Look back` form, the end-or-hand-over form's new steps, and what a
commit or an issue would publish (#352, second part).

`/plinth:guide` finds the last look back by its title (coolbress/plinth#1145).
The end-or-hand-over form gains the steps that keep data, money and access
from being lost or left behind. `.gitignore` and `CONTRIBUTING.md` keep logs,
tables, screenshots and notebook outputs out of a public history.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml  # type: ignore[import-untyped]

from template_render import render


@pytest.fixture(scope="module")
def github(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return render(tmp_path_factory.mktemp("gh") / "p")


@pytest.fixture(scope="module")
def gitlab(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return render(tmp_path_factory.mktemp("gl") / "p", host="gitlab")


def _form(out: Path, name: str) -> dict[str, Any]:
    path = out / ".github" / "ISSUE_TEMPLATE" / f"{name}.yml"
    form: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return form


def _flat(text: str) -> str:
    return " ".join(text.replace("`", "").split())


# The seven questions of coolbress/plinth#1145, in its order.
LOOK_BACK = (
    "1. Is shipping easy",
    "2. The mix of work",
    "3. What the last look back promised",
    "4. What can be removed",
    "5. Where the documents disagree with the code",
    "6. Is the floor intact",
    "7. Did the agent repeat a mistake",
)


def test_look_back_form_asks_the_seven_questions_and_the_tickets(github: Path) -> None:
    form = _form(github, "look-back")
    assert form["title"].startswith("Look back "), "the guide finds it by this title"
    fields = [f for f in form["body"] if f["type"] == "textarea"]
    labels = [f["attributes"]["label"] for f in fields]
    assert labels == [*LOOK_BACK, "Tickets made (at most three)"]
    by_label = {f["attributes"]["label"]: _flat(f["attributes"]["description"]) for f in fields}
    for words in ("feat: and fix: merges", "incident notes", "each with a date"):
        assert any(words in d for d in by_label.values()), words
    floor = by_label["6. Is the floor intact"]
    for words in (
        "/plinth:floor-check",
        "when a restore of the data was last tried",
        "a row count before and after",
        "spend limits still set",
        "/usage (w for the last 7 days)",
        "Actions minutes",
    ):
        assert words in floor, words
    assert "one rung up" in by_label["7. Did the agent repeat a mistake"]
    tickets = by_label["Tickets made (at most three)"]
    assert "sub-issue" in tickets
    assert "within two days" in tickets


def test_gitlab_has_no_look_back_template(gitlab: Path) -> None:
    """The guide reads GitHub only, so GitLab gets none (#352, Not building)."""
    names = [p.name for p in (gitlab / ".gitlab" / "issue_templates").iterdir()]
    assert not [n for n in names if "look" in n.lower()], names


# GitHub's form, then GitLab's template: the same steps, each host's words.
_EXPORT = "A final export of the data is made, and kept or handed over, before the database"
_BILLING = "Spend limits, billing alerts and the billing account are removed, or handed over."
_MIRROR = "git clone --mirror of the repository and an export of"
_BEFORE_DELETING = {
    "github": (_EXPORT, _BILLING, f"{_MIRROR} its issues and pull requests"),
    "gitlab": (_EXPORT, _BILLING, f"{_MIRROR} the project"),
}
_HANDOVER = {
    "github": (
        "the new owner joins as a second person, restores the data into a new database, "
        "and ships one change through a pull request",
        "the repository, where it runs, the package registry, the domain, a connected "
        "reviewer, an error tracker or uptime monitor",
        "the old owner is removed as a collaborator (GitHub adds them on a transfer)",
        "every repository secret, deploy key and webhook holding the old owner's token is replaced",
        ".github/CODEOWNERS, if the project has one, names the new owner",
        "the trusted publisher names the new owner",
    ),
    "gitlab": (
        "the new owner joins as a second person, restores the data into a new database, "
        "and ships one change through a merge request",
        "the repository, where it runs, the package registry, the domain, a connected "
        "reviewer, an error tracker or uptime monitor",
        "the old owner's membership is removed",
        "every CI/CD variable, deploy key and webhook holding the old owner's token is replaced",
        "CODEOWNERS, if the project has one, names the new owner",
        "the trusted publisher names the new owner",
    ),
}
_BEFORE_ARCHIVING = {
    "github": "Before archiving, every collaborator is removed, the agent's own account included",
    "gitlab": "Before archiving, every member is removed, the agent's own account included",
}


def _end_steps(host: str, out: Path) -> tuple[list[str], list[str]]:
    """The steps, then the handover steps, as one flat line each."""
    if host == "github":
        fields = {f.get("id"): f for f in _form(out, "end-or-hand-over")["body"]}
        steps, handover = (
            [_flat(o["label"]) for o in fields[k]["attributes"]["options"]]
            for k in ("steps", "handover")
        )
        return steps, handover
    text = (out / ".gitlab" / "issue_templates" / "End-or-hand-over.md").read_text(encoding="utf-8")
    steps_part = text.split("## Steps", 1)[1].split("\n## ", 1)[0]
    handover_part = text.split("## For a handover", 1)[1].split("\n## ", 1)[0]
    return (
        [_flat(line[6:]) for line in steps_part.splitlines() if line.startswith("- [ ] ")],
        [_flat(line[6:]) for line in handover_part.splitlines() if line.startswith("- [ ] ")],
    )


@pytest.mark.parametrize("host", ["github", "gitlab"])
def test_end_or_hand_over_saves_before_it_deletes_and_hands_over_access(
    host: str, github: Path, gitlab: Path
) -> None:
    steps, handover = _end_steps(host, github if host == "github" else gitlab)
    deleting = next(i for i, s in enumerate(steps) if s.startswith("The data is deleted"))
    for i, words in enumerate(_BEFORE_DELETING[host]):
        assert words in steps[i], f"step {i} lacks: {words}"
        assert i < deleting
    archiving = next(i for i, s in enumerate(steps) if s.startswith("The repository is archived"))
    assert steps[archiving - 1].startswith(_BEFORE_ARCHIVING[host])
    assert len(handover) == 5, handover
    for words in _HANDOVER[host]:
        assert any(words in line for line in handover), f"no handover step says: {words}"
    if host == "github":
        said = next(
            f for f in _form(github, "end-or-hand-over")["body"] if f.get("id") == "handover"
        )
        for page in ("transferring-a-repository", "backing-up-a-repository"):
            assert page in said["attributes"]["description"], page


# Placed where a person or an agent would leave them; git itself is asked.
_IGNORED = (
    "app.log",
    "logs/server.log",
    "export.csv",
    "reports/2026/sales.csv",
    "Screenshot 2026-11-26 at 10.00.00.png",
    "docs/screenshot-1.jpg",
    "Screen Shot 2020-01-01 at 9.00.00 AM.png",
)
_KEPT = (
    "tests/fixtures/rows.csv",
    "src/probe/data/codes.csv",
    "docs/img/diagram.png",
    "src/probe/screenshot.py",
    "notebooks/explore.ipynb",
)


def test_gitignore_leaves_logs_tables_and_screenshots_out(github: Path, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", "-q", str(repo)], check=True)  # noqa: S603, S607
    (repo / ".gitignore").write_bytes((github / ".gitignore").read_bytes())
    for name in (*_IGNORED, *_KEPT):
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / name).write_text("x\n", encoding="utf-8")
    for names, code in ((_IGNORED, 0), (_KEPT, 1)):
        for name in names:
            found = subprocess.run(  # noqa: S603
                ["git", "check-ignore", "-q", "--no-index", name],  # noqa: S607
                cwd=repo,
                check=False,
            )
            assert found.returncode == code, f"{name}: check-ignore exit {found.returncode}"


_CONTRIBUTING = {
    "github": (
        "A pull request merges only after the other person approves it.",
        "The person who asked the agent for a change does not approve the agent account's "
        "pull request for it",
    ),
    "gitlab": (
        "A merge request merges only after the other person approves it.",
        "The person who asked the agent for a change does not approve the agent account's "
        "merge request for it",
    ),
}


@pytest.mark.parametrize("host", ["github", "gitlab"])
def test_contributing_says_what_a_commit_publishes_and_who_approves(
    host: str, github: Path, gitlab: Path
) -> None:
    out = github if host == "github" else gitlab
    text = _flat((out / "CONTRIBUTING.md").read_text(encoding="utf-8"))
    two = text.split("## Two people", 1)[1].split(" ## ", 1)[0]
    assert "When the project has a second person" in two
    for line in _CONTRIBUTING[host]:
        assert line in two, line
    for line in (
        "On a public repository, a log, a screenshot or an issue attachment holding real data "
        "publishes it",
        "Notebooks are committed with their outputs, which can carry data rows, paths and "
        "printed tokens, so clear outputs before committing",
        "an optional tool such as nbstripout",
        "is not installed",
    ):
        assert line in text, line
