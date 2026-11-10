# plinth-template

The copier template a new Python repository starts from when
[plinth](https://github.com/coolbress/plinth) creates it. What it renders is a
repository that passes plinth's checks on its first pull request: the CI
call, the document set, the issue forms, Dependabot, the Claude Code settings.

## Use

Normally `/plinth:new-project <owner>/<name>` renders it for you, creates the
repository, raises the required checks, and answers the questions below,
asking you only the ones a person decides. To render it by hand:

```bash
uv tool install copier          # or: pipx install copier
copier copy gh:coolbress/plinth-template my-app
```

`uvx copier copy gh:coolbress/plinth-template my-app` works without installing.
The package name is derived from the repository name; a name that cannot
become a Python package is refused before any file is written.

On GitHub copier asks thirteen questions, and Enter takes the default for all
but the first:

- the repository name, the owner, the license (MIT or Apache-2.0);
- the kind of project, one of five: `cli`, `library`, `backend`, `data-ml`,
  or `web`, a server-rendered Django app with Postgres, GitHub only;
- `plinth_sha`, the commit of coolbress/plinth the CI calls; Enter takes the
  one this release was tested with;
- the host, GitHub or GitLab;
- whether the owner's `.github` repository already publishes a pull-request
  template, issue forms, `SECURITY.md`, a code of conduct; each yes leaves
  this project's own copy out;
- whether to add a code of conduct, the Contributor Covenant 3.0; yes asks
  where reports go;
- whether the repository is public or private, which decides where
  `SECURITY.md` sends a security report;
- whether a third-party code reviewer, such as Codex's, is already connected
  to the account; yes adds the `third-party / review` check.

`web` adds where the app runs: Render, which plinth builds and checks, or
somewhere else, which then asks where. GitLab asks eight: the owner's
`.github` files, visibility and the third-party reviewer are not asked, and the
checksum of plinth's GitLab pipeline is.

## What an instance gets

- `.github/workflows/ci.yml` calling plinth's reusable `python-ci.yml` at a
  commit SHA, `label.yml` calling plinth's `pr-label.yml` at the same commit
  to label each pull request by type, and Dependabot to raise that SHA. On
  GitLab, `.gitlab-ci.yml` includes plinth's pipeline at a commit with its
  checksum instead.
- `third-party.yml`, calling plinth's `pr-review.yml` at the same commit, when
  the third-party reviewer question is answered yes. It reports and is not
  required.
- `template-reminder.yml`: on the 3rd of each month, an issue when the
  project's template is behind the tag its plinth commit was tested with,
  listing the update steps in order; it closes the issue once the project is
  current. It never updates anything itself.
- `release.yml` for every kind but `web`: a version tag publishes the
  package to PyPI (`cli`, `library`; every package of a uv workspace, each at
  its own version), the image to GitHub's container registry
  (`backend`), or the training run's files to a GitHub Release (`data-ml`).
- README, LICENSE, CONTRIBUTING, CHANGELOG, SECURITY, `AGENTS.md` with the
  `CLAUDE.md` symlink, and the three `docs/agents` files the mattpocock skills
  read.
- Forms: issue forms (bug, feature, task, end or hand over) and a pull request
  template, unless the owner's `.github` publishes its own; GitLab gets the
  same as issue and merge request templates.
- `CODE_OF_CONDUCT.md`, the Contributor Covenant 3.0, only when asked for.
- `docs/how-to/`: `keep-this-project-current.md`, the three updates in order;
  `undo-a-merged-change.md`, a revert through a pull request; and
  `publish-a-release.md` beside each `release.yml`.
- `.claude/settings.json`: the plinth marketplace suggested, the commands the
  checks need allowed without a prompt, force push, `rm -rf`, `.env` and the
  `gh` token denied, and the same `.env` rules for the sandbox. The deny
  covers the Read tool, the shell's readers (`cat`, `head`, `tail`, `sed`,
  `grep`, `<`, `.`, `source`) and a `cat` or `grep` of `.env` inside `$(...)`
  or a subshell; a `bash -c`, another reader inside `$(...)`, a search that
  does not name the file, or a script that opens it is stopped only by the
  sandbox, which is a user setting and is not turned on here.
  `.claude/permissions.md` says which commands still ask and why, and the
  `verify` skill runs the checks before a commit.
- `.claude/output-styles/beginner-or-non-engineer.md`, turned on by
  `.claude/settings.json`; the instance's README says how a person turns it
  off in `.claude/settings.local.json`.
- For `backend`, `data-ml` and `web`: a `Dockerfile` pinned by digest,
  `.dockerignore` and `.env.example`. `data-ml` adds `MODEL_CARD.md`, `data/`
  and a training entry point; `web` adds the Django project and, on Render,
  `render.yaml`.

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

## Keeping an instance current

Three updates reach an instance, in this order, because the first decides
what the second can bring. The instance's
`docs/how-to/keep-this-project-current.md` has the commands and how to tell
each is done.

1. **Update plinth** on the person's computer. Its pinned template tag is the
   tag step 2 moves to.
2. **`/plinth:template-update`** in the instance. It runs `copier update`
   (`.copier-answers.yml` remembers where the instance came from) on a
   branch, shows its plan, asks before it writes, and opens a draft pull
   request. The update is a merge, not a copy: where the instance and the
   template changed the same lines it recommends a side and applies it on the
   person's word. On GitLab, `/plinth:floor-check` prints the `copier update`
   line instead.
3. **Merge the plinth pin pull request** Dependabot opens, which raises the
   commit `ci.yml`, `label.yml` and, when it is there, `third-party.yml`
   call. On GitLab nothing
   raises it; the how-to gives the commands.

Nothing in an instance turns on an automatic update. plinth's own
auto-update is chosen in a session outside any project: inside one, the same
choice rewrites that project's committed `.claude/settings.json`.

## Checks

```bash
uv sync --locked
uv run ruff check . && uv run ruff format --check .
uv run mypy .
uv run pytest          # renders the template and checks the result; needs uv, network and docker
uv build
```

See [CONTRIBUTING.md](CONTRIBUTING.md).
