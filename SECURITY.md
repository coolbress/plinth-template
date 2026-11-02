# Security

## Reporting a vulnerability

**Do not open a public issue.** Use the repository's private reporting form:
**Security → Report a vulnerability** (GitHub Security Advisories). Include what you
found, how to reproduce it, and the version or commit you tested.

## Response — targets, not an SLA

| | Target |
|---|---|
| Acknowledgement | within 3 business days |
| Fix for medium severity or higher | within 60 days |

These are best-effort targets. The project is maintained by one person with no
on-call rotation, and this file does not promise what cannot be operated. If your
report is urgent, say so in the report.

## Scope

This repository: the project template under `template/` and what it renders, and
the harness that tests it.

The plugin, its reusable CI workflows and its scripts are reported to
`coolbress/plinth`. A project *generated* by the template is covered only for
what the template put in it; report the rest to that project's own maintainers.

## Supported versions

The latest release. Older releases are not patched.

## What this repository does

- Dependencies are pinned by lockfile; Dependabot opens weekly updates.
- GitHub Actions and `plinth_sha` are pinned to full commit SHAs — tags are mutable
  and a supply-chain vector.
- Secrets are never committed. `.env` is ignored.
- `main` is protected: nothing merges without green CI.
- No home-grown cryptography — standard libraries and vetted implementations only.
