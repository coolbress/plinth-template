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
result. Two tests go further: `test_generated_project_passes_its_own_checks`
runs `uv sync --locked`, ruff, mypy, pytest and `uv build` inside a rendered
instance (network, for the packages), and
`test_service_archetype_image_actually_builds_and_runs` builds and runs the
`backend` image (docker; skipped on a machine without it, never on CI).

## Test a render by hand

```bash
uvx copier copy --vcs-ref HEAD . /tmp/probe   # HEAD: the working tree, not the last tag
cd /tmp/probe && uv sync --locked && uv run pytest
```

## Land a change

1. Branch from `main`: `git switch -c <type>/<slug>`.
2. Commit with a Conventional Commits title, `type(scope): summary`, one of the
   eleven standard types. A commit made with AI carries the trailer
   `Assisted-by: <agent>:<model>`.
3. Open a pull request. Its description becomes the body of the squash commit:
   what changed and why, how it was verified, and, when AI wrote or assisted,
   the `Assisted-by:` trailer as the last line. Delete the template's comment
   lines; GitHub keeps HTML comments in the squash message.
4. Merge when green. Squash is the only merge method and the branch is deleted
   on merge.

## Cut a release

A change that reaches an instance needs a tag; copier picks the latest tag
and plinth pins one. Tag from the merged `main`, `vX.Y.Z`, MAJOR when
`copier update` on an instance needs hands. Write the release note as the
"why" for a consumer, then tell plinth: its `scripts/new-project.sh` pins the
tested tag and its next release names it.

## What a change must keep true

- The caller job in both `ci.yml` files stays named `ci`.
- `copier.yml` keeps the four questions `/plinth:new-project` answers and the
  `archetype not in [...]` condition on one line; plinth's floor checker reads it.
- `plinth_sha` in `copier.yml` and the `uses:` pins in `.github/workflows` are
  full commit SHAs of `coolbress/plinth`.
- Nothing an instance receives names an internal repository or is written in
  Korean; `test_no_internal_vocabulary_in_the_template` holds the list.
