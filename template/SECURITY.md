# Security

## Reporting a vulnerability

**Do not open a public issue.** Use the repository's private reporting form:
**Security → Report a vulnerability** (GitHub Security Advisories). Include what
you found, how to reproduce it, and the version or commit you tested.

## Response: targets, not an SLA

| | Target |
|---|---|
| Acknowledgement | within 3 business days |
| Fix for medium severity or higher | within 60 days |

These are best-effort targets. This project has no on-call rotation, and this
file does not promise what cannot be operated. If your report is urgent, say so
in the report.

## Supported versions

The latest release. Older releases are not patched.

## What this repository does

- Dependencies are pinned by lockfile; Dependabot opens weekly updates.
- GitHub Actions are pinned to commit SHAs; tags are mutable and a supply-chain vector.
- Secrets are never committed. `.env` is ignored; only `.env.example` is tracked.
- `main` is protected: nothing merges without green CI.
- No home-grown cryptography: standard libraries and vetted implementations only.
