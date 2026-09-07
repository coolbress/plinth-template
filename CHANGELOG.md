# Changelog

The format is [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
versions follow [Semantic Versioning](https://semver.org/). A MAJOR version
means `copier update` on an instance needs hands.

## [Unreleased]

### Added
- The template, rebuilt in English from the archived `coolbress/project-template`
  (v2.18.0): instances call `coolbress/plinth`'s reusable CI at a pinned commit,
  Dependabot raises the pin, `.claude/settings.json` suggests the plinth
  marketplace, allows the check commands without a prompt and denies what the
  checks cannot undo, the `non-engineer` output style ships off by default, and
  `AGENTS.md` carries the situation entrances and the review rules.

### Removed
- The instance session hook, `_logging.py` and the policy tests that
  `ci / floor-check` now runs; the app's tests are a smoke test and tree hygiene.
