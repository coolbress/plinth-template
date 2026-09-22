# Changelog

The format is [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
versions follow [Semantic Versioning](https://semver.org/). A MAJOR version
means `copier update` on an instance needs hands.

## [Unreleased]

## [1.5.0] - 2026-09-22

`plinth_sha` is a recorded answer, so an update can be told to keep the pin
the repository already has.

### Changed
- `plinth_sha` is asked and written into `.copier-answers.yml` instead of
  being computed on every render. While it was `when: false`, copier neither
  recorded it nor let `--data` override it, so each `copier update`
  re-rendered the `uses:` pins from this template's own default: a conflict in
  every workflow file of an instance whose Dependabot had raised them — which
  is every instance, given time — and a silent move back to the template's
  value where it had not. Measured on copier 9.18.2: with the answer recorded,
  `copier update --data plinth_sha=<the pin the repository has now>` keeps the
  pin, records it, applies the template's real workflow changes and conflicts
  nowhere. A render still takes this file's value by default, so nothing
  changes for a new project; the by-hand render in `CONTRIBUTING.md` now asks
  one more question, and Enter answers it (#22).

## [1.4.3] - 2026-09-22

An instance's tree-hygiene tests skip a fresh render whatever language git
speaks, instead of failing on three of them.

### Fixed
- `tests/test_tree_hygiene.py` asks git for its file list with `LC_ALL=C`, so
  the narrow "not a git repository" skip meets the message it was written
  against. git translates that message, and gettext prefers `LANGUAGE` over
  the locale, so where git speaks another language the skip missed and all
  three tree-hygiene tests failed with `git ls-files failed: …` instead. That
  is the state of the by-hand render check `CONTRIBUTING.md` documents, which
  runs pytest in a directory that is not a repository yet, and of this
  template's own render test (#19). The skip still reads the message rather
  than the exit status: 128 is git's general fatal status, and a broken
  `GIT_DIR` inside a real work tree returns it too, so keying on the number
  would widen the skip. The template's test suite now builds the translated
  case itself — `LANGUAGE` with `LC_ALL` and `LC_MESSAGES` removed and `LANG`
  naming a real locale — and fails if it cannot.

## [1.4.2] - 2026-09-21

Branch instructions name their base, the agent file says what to do about a
checkout another session may be using, and a worktree made under `.claude/`
is ignored.

### Added
- `AGENTS.md` opens `## Always` with the shared-checkout rule: before editing,
  inspect the branch, working-tree changes, worktree list and commits ahead of
  the intended base (`git fetch origin`, then `git status -sb`,
  `git worktree list`, `git log --oneline origin/main..HEAD`). Those show the
  state of the checkout, not who else is using it: no command shows another
  session, so a clean checkout on `main` is not proof that it is yours alone.
  When it is not, or when it holds unrelated or unexplained work, leave it
  untouched and work in a uniquely named worktree branched from an explicitly
  verified base; never switch, reset, rebase or stash another task's checkout
  (plinth #218).
- `.gitignore` ignores `.claude/worktrees/`, which Claude Code's documentation
  asks for and which the rule now names as the worktree's path. Without the
  line, `git add .` after `git worktree add .claude/worktrees/x -b wt-x`
  stages the worktree as a `160000` gitlink, which git warns about and a
  reader who does not open the diff commits: a clone will not contain it and
  will not know how to get it. With the line, nothing of the worktree is
  staged.

### Changed
- Every branch instruction names its base, and a worktree is the default
  wherever the checkout may not be yours alone: `git fetch origin`, then
  `git worktree add --no-track -b <type>/<slug> .claude/worktrees/<slug> origin/main`,
  or `git switch -c <type>/<slug> --no-track origin/main` in a checkout that
  is. `git switch -c <type>/<slug>` alone starts the branch at whatever `HEAD`
  is; run from another task's scratch commit it carries that commit into the
  new branch, which is the incident behind plinth #218. `--no-track` leaves
  the new branch with no upstream: tracking `origin/main`, a bare `git push`
  refuses, and the fix git prints first is `git push origin HEAD:main` — a
  push to `main`, not to the branch. Naming the base does not stop uncommitted
  changes riding along — git carries compatible ones onto the new branch and
  prints only `M file` — which is why the rule above is a separate guard and
  not the same one said twice.

## [1.4.1] - 2026-09-13

The `image` job's comment tells a server instance to capture `docker logs`
before piping, so a closed pipe cannot fail a healthy container.

### Fixed
- The `image` job's comment shows a server instance how to read the container
  log: capture `docker logs` into a variable, then pipe from the variable. An
  instance that rewrote the step as `docker logs … | head -1` failed on some
  runs with exit 141, `head` closing the pipe before `docker logs` finished
  and `pipefail` counting the SIGPIPE, with the container healthy
  (plinth #151). The template's own line already captured before piping; the
  test now refuses a live docker process on a pipe and requires the capture
  form in the comment.

## [1.4.0] - 2026-09-11

A service instance gets an image check, the label check finally runs in an
instance's CI, and the agent file says a ruleset change is a person's.

### Added
- A backend or data-ml instance's `ci.yml` carries an `image` job: build the
  Dockerfile, run the image, read its first log line. A plain job, not one in
  python-ci.yml, so a cli or library instance never carries it; the check name
  is `image`, and `/plinth:new-project` requires it in the ruleset for these
  archetypes (plinth #127). The entry point has no port yet, so the one
  request is a run to completion; a server replaces that line with a `curl`.
- `AGENTS.md`: never ask for administration on the everyday token; a ruleset,
  required-check or code-scanning change is a person's, typed through plinth's
  `scripts/with-admin-token.sh` or made in Settings. `CONTRIBUTING.md` states
  the limit: the wall stops the everyday agent, not the administrator
  (plinth #129).

### Changed
- `plinth_sha` is `98e8e56` (plinth after v0.5.4). The pinned python-ci.yml
  now carries the label check (plinth #100) and counts what a run could not
  verify (plinth #124); `13e5082` predated both, so granting `issues: read`
  against it would have changed nothing.

### Fixed
- `ci.yml` grants `issues: read` to its python-ci.yml call, on the job. A
  called workflow cannot widen what its caller grants, so `ci / floor-check`'s
  label check read an API error and reported `not verified` in every instance
  (plinth #102).
- Dependabot's docker updates ignore major and minor: a Python minor bump moves
  the build stage, `.python-version` and mypy together. `python:3.12-slim` to
  `3.14-slim` was green on every required check and could not start, the
  virtualenv copied from the 3.12 build stage pointing at an interpreter the
  run image lacked (plinth #120). Digests and patches still rise.

## [1.3.0] - 2026-09-10

The agent settings also stop a `cat` or `grep` of `.env` inside `$(...)` or a
subshell, where the Read deny does not look.

### Fixed
- `.claude/settings.json` also denies `Bash(cat *.env)` and `Bash(grep *.env)`.
  The Read deny's Bash check sees only a top-level command: measured on Claude
  Code 2.1.267, `echo "$(cat .env)"`, `x=$(cat .env)`, `export $(cat .env |
  xargs)`, `(cat .env)` and `{ cat .env; }` ran with `Read(./.env)` denied in
  every spelling (anthropics/claude-code#89055). A Bash rule reaches those:
  with the two rules every one of them and `env $(grep -v "^#" .env | xargs)`
  is refused, while `cat .env.example`, `grep KEY .env.example` and
  `grep -rn "os.environ" .` still run. Still open, and said in README and
  AGENTS.md: `bash -c "cat .env"`, another reader inside `$(...)`
  (`x=$(head -1 .env)` returned the value), `grep -r SECRET .`, an
  interpreter (plinth #136).

## [1.2.0] - 2026-09-10

The agent settings also stop a sourced `.env`, and the documents say what the
deny reaches and what only the sandbox does.

### Fixed
- `.claude/settings.json` also denies `. ./.env` and `source .env`
  (`Bash(. *.env*)`, `Bash(source *.env*)`). Measured on Claude Code 2.1.267
  with the sandbox off: `Read(./.env)` already stops `cat`, `head`, `tail`,
  `sed`, `grep` and `<` in Bash, alone or in a pipe, `&&` or `;` chain, but a
  sourced `.env` ran, and a line that was not `KEY=VALUE` printed its value
  in the shell's error (plinth #128). The two rules stop every sourcing shape
  tried, `set -a; . ./.env; set +a` included, and leave `.venv/bin/activate`
  alone. Not covered by any deny rule, and now said in README and AGENTS.md:
  `$(cat .env)`, `bash -c "cat .env"`, an interpreter opening the file; the
  sandbox's `denyRead`, already written, stops those when the sandbox is on.

## [1.1.0] - 2026-09-08

The record-writing rules, and the door can stop overwriting an owner's own
conventions.

### Added
- `owner_has_pr_template` and `owner_has_issue_forms`: two `when: false`
  answers `/plinth:new-project` supplies, so an owner who already publishes a
  pull-request template or issue forms in their `.github` repository keeps
  them. The files are never written rather than written and deleted. Two
  answers and not one, because GitHub decides the pull-request template per
  file and the issue templates per folder: a single local form, or just a
  `config.yml`, stops the whole shared folder being inherited.

### Changed
- `CONTRIBUTING.md`, `docs/agents/issue-tracker.md` and `AGENTS.md` carry the
  record-writing rules: the pull-request shape (`## What and why`, `## How it
  was verified`, the issue link, the attribution trailer), `Closes` versus
  `Part of` versus `Related to` and why the verb matters, that a review run in
  the session that wrote the change is not independent, that a behaviour change
  is verified at its boundaries and partial failures with the exercised and
  unexercised paths recorded, and what a record has to carry whatever its
  shape. Each says the convention is the instance's own and theirs to change.
- The pull-request template and the `bug`, `feature` and `task` forms match
  `coolbress/.github`'s. No new field and no new required input: the forms end
  with a display-only note that decisions and the ending belong in the body.
  `blank_issues_enabled: true` is unchanged.

## [1.0.0] - 2026-09-07

The first release: the tag `/plinth:new-project` renders.

### Added
- The template: instances call `coolbress/plinth`'s reusable CI at a pinned commit,
  Dependabot raises the pin, `.claude/settings.json` suggests the plinth
  marketplace, allows the check commands without a prompt and denies what the
  checks cannot undo, the `non-engineer` output style ships off by default, and
  `AGENTS.md` carries the situation entrances and the review rules.
- The `owner` question (default empty): it renders pyproject's author and URLs.
  `/plinth:new-project` passes the repository's owner; empty means unknown and
  neither is rendered.
- `LICENSE` is rendered from the `license` choice, `MIT` or `Apache-2.0`, with
  the owner as the copyright holder, or "the <project> authors" when it is empty.

### Removed
- The instance session hook, `_logging.py` and the policy tests that
  `ci / floor-check` now runs; the app's tests are a smoke test and tree hygiene.
