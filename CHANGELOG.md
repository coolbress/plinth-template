# Changelog

The format is [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
versions follow [Semantic Versioning](https://semver.org/). A MAJOR version
means `copier update` on an instance needs hands.

## [Unreleased]

### Changed
- The commented-out third-party review job in `.github/workflows/ci.yml` no
  longer carries a rendered SHA on its `uses:` line; it names the `ci` job's
  SHA as the one to copy when enabling the job. Nothing kept that commented
  SHA in step with the active lines (Dependabot moves the active ones and
  ignores comments; a hand move can set it to anything), so the next
  `copier update` found three different values there and stopped on a
  conflict: measured on a repository updated from v1.7.1 to v1.9.0, where
  every other change applied without hands. The 1.9.0 note's "without hands"
  held for every file but this line on a repository with a hand-moved comment
  (plinth #463). The active `uses:` lines are unchanged.

## [1.9.0] - 2026-10-10

A new repository's agent is told to run the checks `AGENTS.md` lists before a
commit, through a project skill named `verify`, and its review budget says how
to judge what is still fixed after two rounds. `copier update` applies both
without hands: one new file and one longer line in `AGENTS.md`.

### Added
- A new repository carries a project skill, `.claude/skills/verify/SKILL.md`.
  Claude Code tells the agent to run a project skill named `verify` right
  before a commit, except for a commit that changes only documents or only
  tests. It is a prompt, not a hook: the agent chooses whether to run it, and
  in 5 of 6 trial code commits it did (the sixth ran most of the checks
  itself). The skill names
  the code block in `AGENTS.md` as the list of commands and copies none of
  them. A red command stops the commit, and a check that looks wrong is fixed
  in the same change or asked about, never committed over in silence. CI stays
  the gate. A plugin's skill does not trigger this, so it ships here and not in
  plinth (plinth #409, #458).

### Changed
- The review-budget line of a new repository's `AGENTS.md` says how to judge
  the class that is still fixed after two rounds: by what the diff does, not
  by the reviewer's severity label. A line of guidance that could say more
  exposes nothing, so it is never that class. When a finding repeats the last
  one's kind, the author rewrites once for the whole kind (plinth #423, #457).
  It stays at 59 lines.

## [1.8.1] - 2026-10-09

The comment on a new repository's Dependabot configuration says how the plinth
workflow pins are kept up to date: bare commit SHAs that Dependabot resolves
to a release on its own, raised together after the default cooldown. No
rendered file changes but that comment.

### Changed
- The comment above the `github-actions` entry of `.github/dependabot.yml`
  no longer promises a version comment the pins do not carry. It says what
  a Dependabot job on a rendered repository showed: the plinth pins are bare
  commit SHAs, Dependabot reads the release from the SHA and raises `ci.yml`
  and `label.yml` together in one pull request after GitHub's default
  three-day cooldown (plinth #455). The rendered `uses:` lines are unchanged.

## [1.8.0] - 2026-10-07

A new repository's agent hands a refused workflow push to a person instead
of widening its token, and writes an issue's ending when a merge closes it.

### Changed
- A new repository's `AGENTS.md` names workflow permission next to
  administration: a push GitHub refuses because it changes
  `.github/workflows/` stops at the commit and goes to a person, who pushes
  it from a separate terminal, and a refusal is never answered by widening
  the everyday token (a re-login or `gh auth refresh`), which can replace it
  with a token that reaches every repository the account can (plinth #417). It also says that closing an
  issue writes its `## Outcome`, and that whoever merges writes it when
  `Closes` closes the issue on merge (plinth #418). It stays at 59 lines.
- `docs/agents/issue-tracker.md` ends a research, prototype or grilling child
  in `## Decision`, not also `## Outcome`, as plinth's own copy does.

## [1.7.1] - 2026-10-05

A new repository calls plinth v1.7.2, whose `ci / deps` no longer fails every
pull request on a private repository without GitHub Code Security.

### Changed
- The `plinth_sha` default moves from `8f4edfc` (plinth v1.5.0) to `e52e750`
  (plinth v1.7.2). On a private repository without GitHub Code Security, a new
  repository's `ci / deps` no longer fails every pull request: GitHub refuses
  dependency review there, and the job now passes with a warning that nothing
  was checked where the repository is not a fork and its dependency graph
  answers (plinth #395). Its CI also carries plinth's fixes since v1.5.0. This
  repository's own CI moves to the same commit.

## [1.7.0] - 2026-10-04

A new repository's issue form, pull request template and `AGENTS.md` tie each
acceptance criterion to the test that checks it.

### Changed
- A new repository ties each acceptance criterion to its evidence (plinth
  #299). The task form's acceptance criteria are a "Done means" checklist,
  ticked when the issue closes, with an unticked one named under
  `## Outcome`. The pull request template asks the description to name, for
  each criterion it meets, the test that checks it or why none does, and says
  a named test shows the criterion was exercised, not proved. `AGENTS.md`
  says both, and a resume reads an issue's unticked criteria; it stays at 59
  lines. No check enforces the form.

## [1.6.0] - 2026-10-03

A new repository calls plinth v1.5.0, which reads a private repository's wall
against its licences, and its checks run again when a pull request is edited.

### Changed
- The `plinth_sha` default, the plinth commit a new repository's CI calls, moves
  from `8e96702` (plinth v1.1.0) to `8f4edfc` (plinth v1.5.0). A new
  repository's `ci / floor-check` then reads a private repository's wall
  against its licences, so one created without the CodeQL rule (no Code
  Security) can merge its first pull request, and reports push protection;
  `ci / pr-title` refuses a title ending in `(#N)`. This repository's own CI
  moves to the same commit.
- A new repository's `ci.yml` runs on the `edited` pull-request event besides
  the default types, so a retitled pull request re-runs `ci / pr-title` and an
  edited description re-reads `ci / diff-size`'s warning without a push
  (plinth #322). Every job re-runs on such an edit; the workflow's concurrency
  cancels the run it replaces. This repository's own `ci.yml` does the same.

## [1.5.9] - 2026-09-29

A new repository's CI calls plinth v1.1.0, so it gets plinth's 1.1 checks on a
pull request that weakens the checks.

### Changed
- The `plinth_sha` default, the plinth commit a new repository's CI calls, moves
  from `2673947` to `8e96702`, plinth v1.1.0. A new repository then gets
  plinth's 1.1 checks: `ci / diff-size` warns about a change to the checks the
  pull request description does not name, and `ci / floor-check` fails when
  the `ci` job no longer calls plinth's workflow at a commit SHA, or carries a
  key other than `uses:`, `with:`, `secrets:` and `permissions:`. The
  generated `ci.yml` passes it unchanged. This repository's own CI moves to
  the same commit.

## [1.5.8] - 2026-09-27

A new repository's CI calls plinth at the commit that carries plinth's pre-1.0
checker fixes, not at a commit from 2026-09-11.

### Changed
- The `plinth_sha` default, the plinth commit a new repository's CI calls, moves
  from `98e8e56` (2026-09-11, plinth 0.5.10's time) to `2673947`. That commit
  carries plinth's pre-1.0 checker fixes: `floor-check` compares each required
  check with the app its ruleset entry pins, reads every ruleset, and
  `pr-review.yml` refuses inputs it cannot honour. With the old default, a repository created
  by plinth 1.0 would have run the old checker until Dependabot raised the pin.
  This repository's own CI moves to the same commit.
- The commented third-party review example asks for `pull-requests: read`,
  not `write`; the check needs no more without the summons secret.

## [1.5.7] - 2026-09-27

A generated repository's settings deny `gh repo delete`, which no required
check can undo.

### Changed
- The generated `.claude/settings.json` denies `gh repo delete`, and
  `AGENTS.md`'s list of what the settings deny names it. The login plinth's
  tutorial recommends can delete any repository the person owns, and no
  required check brings one back. The deny covers the command, not every
  route to the same API (`gh api -X DELETE` is not matched); a ruleset edit
  through `gh api` is not denied either, so `AGENTS.md`'s "never ask for
  administration" still carries that. Found by plinth's pre-1.0 review.

## [1.5.6] - 2026-09-27

A generated repository's agent is told that a decision the next person needs
goes into the issue or pull request, not only into Claude Code's machine-local
memory.

### Changed
- The generated `AGENTS.md` says where a decision lives. Claude Code's
  automatic memory stays on the machine it ran on, so a decision, an
  unverified item or a next step the next person needs goes into the issue or
  pull request, not only into memory. The record in issues and pull requests
  is what a new session, another machine or another engineer can read; since
  2026 the agent also keeps its own memory by default, and nothing said which
  one carries the handover.

## [1.5.5] - 2026-09-26

A generated repository's agent is told to answer in the language the person
writes in, and that a close, fix or resolve word before an issue number
anywhere in a pull request's description closes that issue.

### Changed
- The generated `AGENTS.md` and the `non-engineer` output style say to answer
  the person in the language they write in, summaries included. Code,
  commits, pull requests and documents follow the repository's own
  convention. In plinth's first v1.0.0 release-candidate run the person wrote
  in Korean, and the agent's closing summaries, shaped as the style's
  **Insight** block, came back in English. The style is off by default, so
  `AGENTS.md`, read every turn, carries the line too (#30).
- The generated `CONTRIBUTING.md` step 5, `AGENTS.md` and pull request
  template say that a close, fix or resolve word before `#N` anywhere in the
  description closes that issue on merge, a sentence included. In plinth,
  "the two fixes #65 decided" closed the v1.0.0 issue.
- The 1.5.4 section's opening sentence said a tool's default lines "no longer
  reach `main`"; it now says what the template tells the agent, as the 1.5.4
  Release already does.

## [1.5.4] - 2026-09-26

A generated repository tells its agent that `Assisted-by` is the only line
that marks AI, and to remove a tool's default `Co-Authored-By` and
generated-with line. Whether an agent follows it is not yet observed.

### Changed
- The generated `CONTRIBUTING.md`, `AGENTS.md` and pull request template say
  that `Assisted-by` is the only line that marks AI: a tool's default
  `Co-Authored-By` for the AI and its generated-with line are removed, in
  commits and in the description, while a person's trailers stay. Step 5's
  "existing attribution is preserved" had read as keeping them; in plinth's
  second release-candidate pass the agent kept both, and the generated-with
  line reached `main` (#34).

## [1.5.3] - 2026-09-25

A generated repository's agent merges only when the person says so for that
pull request, with the command that keeps the description as the commit, and
checks a worktree before removing it.

### Changed
- The generated `AGENTS.md` says who merges and how: only when the person says
  so for that pull request, since a yes for one does not carry to the next and
  "tidy up" is not a yes, unless the person gave a standing instruction for the
  session, which the agent then names. It merges with `CONTRIBUTING.md` step
  7's command, never plain `gh pr merge --squash`. Step 7 says the same. It
  also says to run `git status --porcelain --ignored` in a worktree and ask
  before removing it: `git worktree remove` deletes ignored files, such as a
  local data file, without a word. In plinth's v1.0.0 release-candidate run
  the agent merged without asking twice, once in a new session, used plain
  `gh pr merge --squash` for the first pull request, and removed a worktree
  unchecked (#31).

## [1.5.2] - 2026-09-25

A generated repository's `ci.yml` points a reader who wants to know what a
check does, or why it is red, at plinth's Required checks page.

### Changed
- The generated `ci.yml` points "what each check does" at plinth's Required
  checks page, which gives each check, what a red means and the fix, and is
  held to plinth's ruleset by a test there. Before, it pointed at
  `python-ci.yml`, the workflow's source; the comment still names it as the
  implementation (#27).

## [1.5.1] - 2026-09-24

A generated repository's `CONTRIBUTING.md` gives the merge command that keeps
a pull request's description as its squash commit, so a description does not
land on `main` hard-wrapped at 72 columns.

### Changed
- The generated `CONTRIBUTING.md` (step 7) and this repository's own (step 5)
  give the merge command that makes the squash commit the pull request
  description: `gh pr merge --squash` with the description passed as `--body`.
  Without it GitHub's default squash message is the description hard-wrapped
  at 72 columns, so a description written at about 80 columns lands on `main`
  with stray one-word lines. Both `AGENTS.md` files point at that step. Found
  and measured in coolbress/plinth#250 (#24).

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
