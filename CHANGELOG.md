# Changelog

The format is [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
versions follow [Semantic Versioning](https://semver.org/). A MAJOR version
means `copier update` on an instance needs hands.

## [Unreleased]

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
