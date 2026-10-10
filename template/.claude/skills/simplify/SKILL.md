---
name: simplify
description: Clean up the staged change within its agreed behaviour, then run AGENTS.md's checks, before a commit.
---

# Simplify

A pass over the change about to be committed, after it works and before the
commit. It keeps the agreed behaviour, the tests and `AGENTS.md`'s rules
exactly as they are; it changes only how the change is written.

- Reuse a helper that already exists instead of a new one beside it.
- Remove an abstraction with one use, and scaffolding for a need nobody has yet.
- Before adding a dependency, check what the standard library, the platform or
  a dependency already installed does.
- Prefer the shorter form of the same logic.

Never cut validation at a trust boundary, error handling that prevents a loss,
a security measure, or anything the issue asked for. When unsure, keep it.

On a commit that answers a review finding, the pass covers only the lines that
fix touches: the diff the reviewer read is not reshuffled under them.

End by running the commands in the code block at the top of `AGENTS.md`, in
that order; do not keep a copy of them here. A command that fails stops the
commit: report it with its output.
