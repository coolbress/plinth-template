# plinth-template

The copier template a new Python repository starts from when
[plinth](https://github.com/coolbress/plinth) creates it. What it renders is a
repository that passes plinth's checks on its first pull request: the CI
call, the document set, the issue forms, Dependabot, the Claude Code settings.

## Use

Normally `/plinth:new-project <owner>/<name>` renders it for you, creates the
repository, and raises the required checks. To render it by hand:

```bash
uv tool install copier          # or: pipx install copier
copier copy gh:coolbress/plinth-template my-app
```

`uvx copier copy gh:coolbress/plinth-template my-app` works without installing.
Four questions: the repository name, the owner, the license, the kind of
project (`cli`, `library`, `backend`, `data-ml`). The package name is derived
from the repository name; a name that cannot become a Python package is refused
before any file is written.

## What an instance gets

- `.github/workflows/ci.yml` calling plinth's reusable `python-ci.yml` at a
  commit SHA, and Dependabot to raise that SHA; a commented, optional
  `third-party / review` block.
- README, LICENSE, CONTRIBUTING, CHANGELOG, SECURITY, `AGENTS.md` with the
  `CLAUDE.md` symlink, issue forms (bug, feature, task), a pull request
  template, and the three `docs/agents` files the mattpocock skills read.
- `.claude/settings.json`: the plinth marketplace suggested, the commands the
  checks need allowed without a prompt, force push, `rm -rf`, `.env` and the
  `gh` token denied, and the same `.env` rules for the sandbox. The sandbox
  itself is a user setting and is not turned on here.
- `.claude/output-styles/non-engineer.md`, not applied by default; select it
  under `/config` → Output style.
- For `backend` and `data-ml`: a `Dockerfile` pinned by digest, `.dockerignore`,
  an entry point that logs JSON, and `.env.example`.

## Layout

```text
plinth-template/
├── copier.yml          questions, conditions, _subdirectory
├── pyproject.toml      ┐
├── src/template_render/│  the template's own project: render and check
├── tests/              │
├── .github/workflows/  ┘  (this repository's CI; not rendered)
└── template/           the only thing rendered into an instance
```

## Versions

copier compares tags as PEP 440 versions and picks the latest; without a tag
it falls back to `HEAD`. Tags start at `v1.0.0`. plinth pins one tag, the one
it was tested with, and its release notes name it.

| | When |
|---|---|
| MAJOR | `copier update` on an instance needs hands: a renamed or deleted file, a new required question |
| MINOR | a new file, a new question with a default, a new test |
| PATCH | text, comments, a fix that keeps behaviour |

An instance catches up with `uvx copier update` (its `.copier-answers.yml`
remembers where it came from).

## Checks

```bash
uv sync --locked
uv run ruff check . && uv run ruff format --check .
uv run mypy .
uv run pytest          # renders the template and checks the result; needs uv, network and docker
uv build
```

See [CONTRIBUTING.md](CONTRIBUTING.md).
