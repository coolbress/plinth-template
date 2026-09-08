# Changelog

The format is [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
versions follow [Semantic Versioning](https://semver.org/). A MAJOR version
means `copier update` on an instance needs hands.

## [Unreleased]

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
