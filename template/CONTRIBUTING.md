# Contributing

Changes land through pull requests only. `main` is protected by a ruleset
that requires the checks below; nobody pushes to it directly, the owner included.

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
2. Branch from `main`: `git switch -c <type>/<slug>`.
3. Commit. A commit made with AI carries the trailer `Assisted-by: <agent>:<model>`.
4. Open a pull request. Its title is `type(scope): summary`, checked by
   `ci / pr-title`; the eleven types are `feat` `fix` `docs` `style` `refactor`
   `perf` `test` `build` `ci` `chore` `revert`. Do not invent a type; extra
   meaning goes in the scope (`docs(research):`, `fix(security):`).
5. The description becomes the body of the squash commit, so write it as one:
   what changed and why, how it was verified, and, when AI wrote or assisted,
   the `Assisted-by:` trailer as the last line. Delete the template's comment
   lines: GitHub keeps HTML comments in the squash message.
6. Merge when every required check is green. Squash is the only merge method;
   the commit is the pull request title and description, and the branch is
   deleted on merge.

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
