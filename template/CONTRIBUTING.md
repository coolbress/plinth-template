# Contributing

Changes land through pull requests only. `main` is protected by a ruleset
that requires the checks below; nobody pushes to it directly, the owner included.
The ruleset stops the everyday agent, not the administrator: the owner, or
anyone holding administration, can change it, which is why the agent never
holds administration (`AGENTS.md`).

## Run the checks

```bash
uv sync --locked
uv run ruff check . && uv run ruff format --check .
uv run mypy .
uv run pytest
uv build
```

CI runs each of these as a separate check (`ci / lint`, `ci / typecheck`,
`ci / test`, `ci / build`) and adds a secret scan, a dependency review, a
diff-size limit, a title check, a floor check and CodeQL. The list of
required checks is the repository's ruleset, not this file. Warnings are errors
in pytest (`filterwarnings = ["error"]`); a third-party warning that blocks gets
one narrow ignore in `pyproject.toml`, with its reason.

## Land a change

1. For anything bigger than a typo, open an issue first, with acceptance criteria
   a check or a reviewer can confirm. A typo goes straight to a pull request.
2. Branch from `origin/main`, always naming the base. Unless the checkout is
   yours alone — no command tells you whether another session is in it — make
   the branch in its own worktree: `git fetch origin`, then
   `git worktree add --no-track -b <type>/<slug> .claude/worktrees/<slug> origin/main`.
   In a checkout that is yours alone, `git switch -c <type>/<slug> --no-track
   origin/main` does the same in place. Without the base either command starts
   the branch at whatever `HEAD` is, which carries another task's commits into
   yours. `--no-track` leaves the branch with no upstream: tracking
   `origin/main`, a bare `git push` refuses and the fix git prints first is
   `git push origin HEAD:main` — a push to `main`, not to your branch.
3. Commit. A commit made with AI carries the trailer `Assisted-by: <agent>:<model>`.
4. Open a pull request. Its title is `type(scope): summary`, checked by
   `ci / pr-title`; the eleven types are `feat` `fix` `docs` `style` `refactor`
   `perf` `test` `build` `ci` `chore` `revert`. Do not invent a type; extra
   meaning goes in the scope (`docs(research):`, `fix(security):`).
5. The description becomes the body of the squash commit, so write it as one,
   in this shape:

   ```text
   ## What and why

   The problem, what actually changed, the result, and why this approach.

   ## How it was verified

   What was run and what it showed; important unverified items and follow-ups.

   Closes #N

   Assisted-by: <agent>:<model>
   ```

   The issue link goes after the verification section, directly above the
   attribution. `Closes #N` only when the pull request completes that issue;
   partial work links with `Part of #N`, related work with `Related to #N`.
   `Closes` drives GitHub's auto-close, so the wrong verb closes an unfinished
   issue. With no issue to link, omit the line. Existing attribution is
   preserved: several trailers form one contiguous block at the end.

   This is your repository's convention, not a rule imposed from outside — if
   your team settles on a different shape, change this file and the templates
   together. Check the template that actually applies before you write: a local
   `.github/PULL_REQUEST_TEMPLATE.md`, or your owner account's `.github`
   defaults when there is none. `gh pr create --body`/`--body-file` bypasses it,
   so read it yourself. Delete its comment lines — GitHub keeps HTML comments in
   the squash message.
6. Before merging, read the description against the final diff: what changed
   and why, what was verified and what was not, as of the last commit. A
   review fix that changed the scope changes the description too, because
   the description is what lands on `main`.

   Say what was actually run, and name what was not. A review run in the same
   session that wrote the change is not an independent review. When you change
   behaviour, verify the boundaries and partial failures of the inputs and
   states it touches, record which paths you exercised and which you did not,
   and do not widen the result of a few cases into a guarantee about all of
   them. Put user-facing explanation and history where it belongs — `README.md`,
   `CHANGELOG.md`, or the page that covers it; not every change needs a README
   edit.
7. Merge when every required check is green. Squash is the only merge method;
   the commit is the pull request title and description, and the branch is
   deleted on merge. The description is the commit only when the merge passes
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

## Pull request size

Aim at 200 changed lines and stay under 400; `ci / diff-size` blocks above.
The figure comes from the largest published code-review case study (Cisco,
one team): review effect falls off around 200 lines and 400 is its ceiling.
Documentation and lockfiles are not counted. A bigger change is split into
stacked pull requests; CI runs on each against its own base.

## Tests

- A change in behaviour or a bug fix comes with the test that catches it, in the
  same pull request; a documentation, configuration or refactoring change that
  keeps behaviour does not need one, say so in the description.
- Writing the failing test first is encouraged, not enforced.
- A new behaviour has a test that actually runs it. The measure is not coverage
  but whether the test would fail if the behaviour broke.
