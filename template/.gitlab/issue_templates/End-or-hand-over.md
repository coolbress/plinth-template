<!-- Use this when you stop working on the project, or when someone else takes it over. Tick each step when it is done. A step that does not apply to this project (no users, no package, no server) gets a line under "Not needed" instead of a tick. -->

## What happens to the project

<!-- Delete the line that does not apply. -->

- It stops for good
- Someone else takes it over: <!-- their account or name -->

## Steps

- [ ] A final export of the data is made, and kept or handed over, before the database is deleted.
- [ ] Spend limits, billing alerts and the billing account are removed, or handed over.
- [ ] When the account itself will close, a `git clone --mirror` of the repository and an export of the project (Settings, General, Advanced, Export project), which carries its issues and merge requests, are kept.
- [ ] The data is deleted, or handed to the new owner.
- [ ] Keys, tokens and passwords the project used are revoked, or handed over and then changed.
- [ ] The people who use it are told what is happening and when.
- [ ] The package is yanked or marked deprecated, or handed over, on the registry it was published to.
- [ ] The container image and the running service are deleted, or handed over, so nothing keeps costing money.
- [ ] Before archiving, every member but the person who archives is removed, the agent's own account included, so no other account keeps access to an archived project.
- [ ] The repository is archived, or moved to the new owner. Archive last, after closing this issue; an archived project's issues cannot be changed.

## For a handover

<!-- Leave these unticked when the project stops for good. -->

- [ ] Before the project moves, the new owner joins as a second person, restores the data into a new database, and ships one change through a merge request.
- [ ] Access is handed over wherever the project has it: the repository, where it runs, the package registry, the domain, a connected reviewer, an error tracker or uptime monitor.
- [ ] After the move, the old owner's membership is removed, and every CI/CD variable, deploy key and webhook holding the old owner's token is replaced.
- [ ] `CODEOWNERS`, if the project has one, names the new owner.
- [ ] For a package published to PyPI through a trusted publisher set up for this project, the publisher names the new owner and project path before the next release; with an API token, the token is replaced instead.

## Not needed

<!-- Each step that does not apply to this project, and why, one line each. For example: Package: it was never published. -->

## What went well

<!-- What you would do the same way in the next project. -->

## What the agent kept getting wrong

<!-- Mistakes the coding agent made more than once, even after being told. -->

## A rule or check to add next time

<!-- For each mistake above, the line in AGENTS.md or the check in CI that would have caught it. A check that fails is stronger than a rule that asks. If plinth is installed, type /retro in Claude Code, in the session you are looking back on: it suggests rules and checks from what went wrong there. Copy the ones you keep here. -->

<!-- When this closes, write the ending under "## Outcome": which steps were done, which were not needed, and anything left open with why. -->

/label ~task
