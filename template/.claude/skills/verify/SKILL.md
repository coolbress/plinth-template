---
name: verify
description: Run this repository's checks, the commands in AGENTS.md's code block, before a commit.
---

# Verify

Run the commands in the code block at the top of `AGENTS.md`, in that order.
That block is the only list: do not keep a second copy of the commands here or
anywhere else.

- A command that fails stops the commit. Report it with its output.
- A check that looks wrong, such as a test of the old behaviour after an
  intended change, is said to be wrong and fixed in the same change, or the
  person is asked. Never commit over a failing check in silence.
- CI runs the same checks as required checks and is the gate. This is the
  early look, so a failure costs a commit instead of a pull request round.
