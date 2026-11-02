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

These are best-effort targets. The projects are maintained by one person with no
on-call rotation, and this file does not promise what cannot be operated. If your
report is urgent, say so in the report.

## Scope

- `plinth` — the plugin, the reusable CI workflows, and the scripts that create
  repositories and apply rulesets
- `plinth-template` — the project template
- `plinth-lab` — research and tooling; no runtime surface

Projects *generated* by the template are not covered here; report those to their
own maintainers.

## Supported versions

The latest release of each repository. Older releases are not patched.

## What these repositories do

- Dependencies are pinned by lockfile; Dependabot opens weekly updates.
- GitHub Actions are pinned to commit SHAs — tags are mutable and a supply-chain vector.
- Secrets are never committed. `.env` is ignored; only `.env.example` is tracked.
- `main` is protected: nothing merges without green CI.
- No home-grown cryptography — standard libraries and vetted implementations only.
