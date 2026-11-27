# Contributing

plinth-template is the copier template `/plinth:new-project` renders. Changes
land through pull requests only; `main` is protected by a ruleset that requires
the checks below.

## Run the checks

```bash
uv sync --locked
uv run ruff check . && uv run ruff format --check .
uv run mypy .
uv run pytest
uv build
```

`pytest` renders the template into temporary directories and checks the
result. Some tests go further: `test_generated_project_passes_its_own_checks`
runs `uv sync --locked`, ruff, mypy, pytest and `uv build` inside a rendered
instance (network, for the packages);
`test_service_archetype_image_actually_builds_and_runs` builds and runs the
`backend` image, and `test_web_archetype_image_job_passes_as_rendered` runs
the `web` instance's `image` job steps as rendered (docker; both skipped on a
machine without it, never on CI).

## Test a render by hand

```bash
uvx copier copy --vcs-ref HEAD . /tmp/probe   # HEAD: the working tree, not the last tag
cd /tmp/probe && uv sync --locked && uv run pytest
```

It asks for `plinth_sha` along with the rest; Enter takes the commit this
template is tested with. It is a recorded answer rather than a computed one so
that `copier update` on an instance can be given the pin that instance has
now, instead of re-rendering this file's default over it (#22). On GitHub it
also asks whether the owner's `.github` repository publishes a pull-request
template and issue forms; Enter answers no, and the template writes its own.
They are recorded for the same reason (coolbress/plinth#726).

## Land a change

A change only to this repository is filed here, even though plinth raises its
pin afterwards; the pull request that raises the pin closes the issue. A
change that also touches plinth (the door, `/plinth:floor-check`, plinth's
docs) is filed in coolbress/plinth, and the pull request here ends with
`Part of coolbress/plinth#N`.

1. Branch from `origin/main`, always naming the base. Unless the checkout is
   yours alone — no command tells you whether another session is in it — make
   the branch in its own worktree: `git fetch origin`, then
   `git worktree add --no-track -b <type>/<slug> .claude/worktrees/<slug> origin/main`.
   In a checkout that is yours alone, `git switch -c <type>/<slug> --no-track
   origin/main` does the same in place. Without the base either command starts
   the branch at whatever `HEAD` is, which carries another task's commits into
   yours. `--no-track` leaves the branch with no upstream: tracking
   `origin/main`, a bare `git push` refuses and the fix git prints first is
   `git push origin HEAD:main` — a push to `main`, not to your branch.
2. Commit with a Conventional Commits title, `type(scope): summary`, one of the
   eleven standard types. A commit made with AI carries the trailer
   `Assisted-by: <agent>:<model>`.
3. Open a pull request. Its description becomes the body of the squash commit:
   what changed and why, how it was verified, and, when AI wrote or assisted,
   the `Assisted-by:` trailer as the last line. Delete the comment lines of
   `.github/PULL_REQUEST_TEMPLATE.md`; GitHub keeps HTML comments in the
   squash message. That file and `.github/ISSUE_TEMPLATE/` are this
   repository's own, copied from `template/.github/` at v1.35.0 with this
   repository's rules; a change under `template/` does not reach them.
4. Before merging, read the description against the final diff: what changed
   and why, what was verified and what was not, as of the last commit. A
   review fix that changed the scope changes the description too, because
   the description is what lands on `main`.
5. Merge when green. Squash is the only merge method and the branch is deleted
   on merge. The description is the squash commit only when the merge passes
   it: without a body, GitHub's default squash message is the description
   hard-wrapped at 72 columns, and `gh pr merge --squash` takes that default.

   ```bash
   body="$(gh pr view <n> --json body --jq .body)" &&
     gh pr merge <n> --squash --match-head-commit <sha> --body "$body"
   ```

   The `&&` stops the merge when the read fails, rather than merging with an
   empty body, and no file is left in the checkout to be committed later.
   `--match-head-commit` names the head the description was read against: a
   commit pushed after it stops the merge. It pins the commits only; the
   description is read when the command runs, so finish editing it first.

## Cut a release

A change that reaches an instance needs a tag; copier picks the latest tag
and plinth pins one.

1. Before writing the release section, raise the three `coolbress/plinth`
   pins in `.github/workflows` (`ci.yml`, `label.yml`, `third-party.yml`) to
   plinth's latest release, and merge that once its CI is green on them.
   Dependabot's `actions` pull request does it when it names that release;
   its three-day cooldown and weekly schedule often leave it a release or more
   behind (#278 named v2.35.0 when v2.38.0 was out), and then the raise is by
   hand. The latest release's commit:

   ```bash
   git ls-remote --tags https://github.com/coolbress/plinth.git |
     grep -E 'refs/tags/v[0-9]+\.[0-9]+\.[0-9]+\^\{\}$' | sort -t/ -k3 -V | tail -1
   ```

   Why: a new project calls plinth at `plinth_sha`'s default, so it starts at
   whatever this release carries. Releases v1.45.0 to v1.47.0 carried v2.32.0
   while plinth reached v2.38.0, and a project made on 2026-11-20 was told on
   its first day that its pin was 28 commits behind (#288). An existing
   project keeps its own pin on `copier update` (#22); its Dependabot raises
   it.
2. In the pull request that adds the version's `CHANGELOG.md` section, raise
   `plinth_sha` in `copier.yml` to that same commit, and
   `plinth_gitlab_integrity` to its checksum:

   ```bash
   curl -fsSL https://raw.githubusercontent.com/coolbress/plinth/<sha>/gitlab/python-ci.yml |
     openssl dgst -sha256 -binary | openssl base64 -A
   ```

   Title it `docs(changelog): the X.Y.Z section`: that title, and on `main`
   the squash commit's subject that carries it, is what opens the release
   window for the two tests below. The job's checkout has no tags, so the
   window is read from the event and needs no network; a release pull
   request under another title is not checked. Run by hand, the window is
   open while the newest section has no tag in your clone.

   coolbress/plinth reads the default at a tag as what that tag was tested
   with. Inside the window two tests stop the release:
   `test_a_release_carries_the_plinth_pin_its_own_ci_calls` when the default
   is not what `.github/workflows` calls, and
   `test_a_release_starts_new_projects_at_plinths_latest_release` when it is
   not plinth's latest release, naming both; only this one reads plinth's
   tags, and an unread tag list fails it. The section says what a new
   project's pin moves to. Outside the window neither compares or reads
   anything: Dependabot raises the workflows' pins, plinth releases again,
   and the default waits for the next release.
   The section opens with `### Files and questions`, that text exactly:
   coolbress/plinth's update plan quotes the block under it for each release
   a project's update crosses. One item per line: `` - `<path>` `` for each
   rendered file the release changes, adds or deletes (its path under
   `template/` as the instance has it: no `.jinja`, a `{% if %}` name as the
   name it renders, `{{ package_name }}` as `<package>`), `` - question
   `<name>` `` for each question it adds to `copier.yml`, or `- None.`.
   `tests/test_changelog_files_and_questions.py` fails a section from v1.52.0
   on without it, a line under it that is no item, and a question that is not
   a key in `copier.yml`. Whether the list is the release's whole diff of
   `template/` needs the last tag, which CI's checkout lacks, so there it
   skips: before tagging, run it in a clone that has the tags
   (`uv run pytest tests/test_changelog_files_and_questions.py`), and fix the
   list until it passes. A pull request that changes `template/` adds its
   files to `[Unreleased]`'s list as it goes; the release step checks the
   whole.
3. Tag from the merged `main` once its CI is green, `vX.Y.Z`, MAJOR when
   `copier update` on an instance needs hands. Merge nothing between the
   release pull request and the tag: a later commit on `main` is outside the
   window, so neither test checks it. A plinth release in this window turns
   the release pull request's re-run red: raise to it, or tag before it lands.
4. Write the release note as the "why" for a consumer, then tell plinth: its
   `scripts/new-project.sh` pins the tested tag and its next release names it.

## When the base-image watch opens an issue

`.github/workflows/image-watch.yml` runs on Mondays and on demand (Actions,
Base-image watch, Run workflow, with a tag or empty for the latest release).
It renders `backend` and `web`, runs each render's own `image` job with a
grace of 7 days, and on a failure opens, or comments on, one issue titled
`Base-image watch: …`. The issue names each finding and the day new projects
start failing on it. The fix is a raised digest in `template/Dockerfile.jinja`
(Dependabot's `docker` pull request, or by hand), a template release, and
plinth's pin raise. Close the issue once a run passes.

## What a change must keep true

- The caller job in both `ci.yml` files stays named `ci`.
- `copier.yml` keeps the four questions `/plinth:new-project` answers and the
  `archetype not in [...]` condition on one line; plinth's floor checker reads it.
- `plinth_sha` in `copier.yml` and the `uses:` pins in `.github/workflows` are
  full commit SHAs of `coolbress/plinth`.
- Nothing an instance receives names an internal repository or is written in
  Korean; `test_no_internal_vocabulary_in_the_template` holds the list.
