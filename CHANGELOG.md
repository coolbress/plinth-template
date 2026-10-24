# Changelog

The format is [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
versions follow [Semantic Versioning](https://semver.org/). A MAJOR version
means `copier update` on an instance needs hands.

## [Unreleased]

### Added
- A `web` project's pre-deploy step is `python -m <package>.predeploy`
  (#105). On the first Blueprint deploy Render creates the database and
  the service together, and `migrate` could start before the database
  accepted connections, failing the first deploy (coolbress/plinth #607).
  The step now retries only the connection, every 5 seconds for up to two
  minutes, then runs `migrate` once; a failing migration is not retried,
  and a database that never answers still fails the deploy with the last
  error. The instance's tests cover all four paths without waiting.
- The `web` README says, in plain words, how to make the first account
  (`python -m django createsuperuser` in the web service's own Shell, the
  password pasted rather than typed blind) and how to get data back
  (Recovery, Restore Database at least ten minutes ago into a new
  database, then the web service's `DATABASE_URL`), with the window per
  workspace plan from Render's backups page, read 2026-10-24: the past 3
  days on Hobby, 7 on Pro or higher.

### Changed
- A `web` project's settings add Render's `RENDER_EXTERNAL_HOSTNAME` to
  the allowed hosts, and the entry point starts with either it or
  `DJANGO_ALLOWED_HOSTS` (#105). Render names a service
  `<name>-<4 characters>.onrender.com`, so the host typed in the Blueprint
  form before the service existed was refused with 400. Another host is
  still refused, and the secret key and the database URL are still
  required. `render.yaml` keeps its `DJANGO_ALLOWED_HOSTS` entry, now for
  a custom domain, and changes its `preDeployCommand`: an instance with
  Auto Sync off needs Manual Sync once after the update is merged.

## [1.22.0] - 2026-10-22

The agent no longer stops for an approval at the start of every task. A
rendered project's `.claude/settings.json` now allows the read and the
worktree step that `AGENTS.md` asks for first, and a new
`.claude/permissions.md` says which commands still ask and why: pushing,
opening and merging a pull request, and removing a worktree, each a moment
the person should see. `copier update` from 1.21.0 completed without hands
on untouched cli instances on GitHub and GitLab and an untouched web
instance on GitHub. It changes `.claude/settings.json` and `AGENTS.md`,
adds `.claude/permissions.md`, and keeps each instance's own plinth pin;
each updated instance equals a fresh render. Hand-edited instances were not
updated.

### Added
- `.claude/permissions.md`: every command `AGENTS.md` and `CONTRIBUTING.md`
  tell the agent to run either matches an allow rule or is listed there as
  asking on purpose, with the reason (#94). A template test holds the two
  documents and the list against each other on both hosts.

### Changed
- `.claude/settings.json` allows `git fetch origin` (that exact command),
  `git worktree list` and `git worktree add --no-track -b`, the spelling
  `AGENTS.md` gives. Measured on Claude Code 2.1.307: in a
  `claude -p --setting-sources project,local` session the first two ran
  with no denial, a rule without `:*` matched its own text only, and
  `git worktree remove`, `git push` and `gh pr create` still asked.

## [1.21.0] - 2026-10-21

A fresh render of any archetype calls plinth v2.6.0, the release that
carries the `ci / diff-size` rows for the `web` archetype
(coolbress/plinth #615). In a new `web` repository that check now asks a
person to approve a pull request that widens the public route list, edits
or deletes an existing migration, changes the production settings module,
`render.yaml`, the `Dockerfile` or `tests/migration_rows.json`; in a new
repository of every archetype it asks when the `archetype:` line of
`.copier-answers.yml` changes or the file goes. Nothing else in a render
changes. `copier update` from 1.20.0 completed without hands on untouched
cli instances on GitHub and GitLab and an untouched web instance on
GitHub. It changes `.copier-answers.yml` alone and keeps each instance's
own plinth pin, so an existing repository gets the new rows when its
Dependabot raises the pin; hand-edited instances were not updated.

### Changed
- The `plinth_sha` default moves from `1af8f03` (plinth v2.5.0) to
  `d50950b` (plinth v2.6.0). plinth's `gitlab/python-ci.yml` has the same
  bytes at both commits, so `plinth_gitlab_integrity` is unchanged, and no
  caller grants a new permission.

## [1.20.0] - 2026-10-21

A new archetype, `web`: a Django app on Postgres, deployed to Render, with
access rules its tests prove. It renders the app, its migrations and
representative rows, a `render.yaml`, an image job that serves, and the
walls that keep production credentials out of the agent's session. Its
`ci.yml` turns on plinth's `ci / migrations` and `ci / deploy-check`, and a
fresh render of any archetype calls plinth v2.5.0. `web` is GitHub only and
costs about US $13 a month on Render; the archetype question says so.
`copier update` from 1.19.0 completed without hands on untouched cli
instances on GitHub and GitLab and an untouched backend instance on GitHub.
It changes `.gitignore` alone and keeps each instance's own plinth pin;
hand-edited instances were not updated.

### Added
- A `web` archetype, the first part of coolbress/plinth #612's prototype
  gate: a Django 5.2 LTS project under `src/`, served by uvicorn from
  `python -m <package>`, with Postgres from `DATABASE_URL`. Its settings
  come from the environment, and the entry point refuses to start without
  the secret key, the allowed hosts and the database URL. WhiteNoise serves
  the static files the image collects at build time, the admin's included;
  `.env.example` lists every key the project reads, and the README says to
  load `.env` with `uv run --env-file .env`. A rendered `web`
  project passes its own `uv sync --locked`, ruff, mypy (with django-stubs),
  pytest (with pytest-django) and `uv build`, under the names and assertions
  the checks already have. GitHub only: copier refuses `web` with
  `host: gitlab`. plinth does not offer `web` until it pins a tag that also
  has coolbress/plinth #613, #614 and #615.
- The `web` archetype's `image` job, the second part of that gate. A server
  never exits, so the container starts detached with production-shaped
  settings (a key made for the run, placeholder hosts, no database reached),
  must answer `/healthz`, and its first log line must carry
  `"message": "started"`, the line the job already reads. Two tests run it:
  one starts `python -m <package>` installed without the dev tools, and on
  CI one runs the rendered job's own steps with docker, then gets the
  admin's stylesheet from the running container as `text/css`, which
  `collectstatic` in the image's build put there.
- A `web` project's `ci.yml` passes `web: true` to plinth's python-ci, which
  turns on `ci / migrations` and `ci / deploy-check` (coolbress/plinth
  #614). Its settings silence `security.W005` and `security.W021` (HSTS
  include-subdomains and preload) from the first render, each with the
  reason: preload is hard to undo, and subdomains reach the whole domain. A
  fresh render then passes `manage.py check --deploy --fail-level WARNING`.
  The README says how to turn either on, and to run `manage.py migrate`
  before the first start on a new database.
- A `web` project carries a small app, `notes`, to show its access rules:
  log in, write a note, read and change your own. Every view needs a
  logged-in person unless it is marked public (Django's
  `LoginRequiredMiddleware`), every route is marked public or for logged-in
  people, and every query filters by the person, so another person's note
  is not found. Its tests, inside `ci / test` and asked over HTTPS as the
  host's proxy asks, show:
  - an anonymous request goes to the log-in URL;
  - another person's note answers 404, to reading and to changing;
  - the log-in, write and read flow passes through the forms with CSRF
    checked;
  - an unmarked route fails, a rule that is plinth's proposal, not a
    published standard.

  `tests/migration_rows.json` holds two users, a group and a note for each.
  `ci / migrations` reads these rows from the base commit, and a test loads
  them, so a file that no longer loads fails first.
- A `web` project's `render.yaml` (Render Blueprint) declares one web
  service built from its `Dockerfile` and one Postgres, both on paid
  plans, never `free`. The database has the 1 GB disk its price includes
  and accepts connections from Render's private network only. A commit to
  the default branch deploys only after its checks pass.
  `python -m django migrate` runs before each deploy, so a failed
  migration stops the deploy while the running version keeps serving.
  The health check is `/healthz`. The secret key is generated by Render,
  the allowed hosts are typed in its dashboard, and the file holds no
  secret.
- A `web` project's `.claude/settings.json` denies the Render CLI and its
  credentials (`~/.render/`), and `AGENTS.md` says production is Render's:
  no Render API key in the session, deploys only through Render's GitHub
  integration, production credentials only in Render and GitHub environment
  secrets.
- The archetype question states the web choice's cost: about US $13 a month
  on Render (a $7 web service and a $6 Postgres) besides the Claude
  subscription. Free Postgres is unsupported (deleted after 30 days, no
  backups), and Render has no spending cap.

### Changed
- The `plinth_sha` default moves from `033fbe3` (plinth v2.0.0) to
  `1af8f03` (plinth v2.5.0), the release with the `web` input. For every
  other archetype the two new checks report a pass that does not apply,
  which no ruleset requires, and no caller grants a new permission.
  `plinth_gitlab_integrity` is unchanged: `gitlab/python-ci.yml` has the
  same bytes at both commits.
- `.gitignore` ignores `db.sqlite3` and `staticfiles/`, Django's local
  database and collected static files, in every archetype. No other file
  of an existing archetype's render changes.

## [1.19.0] - 2026-10-20

A rendered project's agent reports in one place and says which account it
works under. The output style "Beginner or non-engineer" is now the only
reporting contract: `AGENTS.md` stops pointing at the report in
`/plinth:arsenal`, which plinth removes in the release that pins this tag.
At a session's first task, at a resume and before a merge, the agent reads
its login and whether it administers the repository, and says what that
means for the merge; `.claude/settings.json` allows those reads as exact
commands. Only those three files change. `copier update` from 1.18.0
completed without hands on untouched cli instances on GitHub and GitLab and
an untouched backend instance on GitHub, and the updated files equal a fresh
render; hand-edited instances were not updated.

### Changed
- One reporting contract instead of two (coolbress/plinth #602). The output
  style "Beginner or non-engineer" now carries the moments to report (a
  task's start, an important choice, a failure, the end of a change, a
  resume) and, at a start or a resume, the goal, the next action and where
  the record lives. `AGENTS.md` no longer points at the five-item report in
  `/plinth:arsenal`, which plinth removes in the same release.
- The output style says which account the agent works under, read in that
  session, at a session's first task, at a resume and before a merge. As an
  admin of the repository (GitLab: a Maintainer or Owner), a failing
  required check still stops the merge, but merging a passing one and
  approving a change that weakens a check are guidance only; when the account cannot be
  read, merge separation is not established. One sign-in read is never taken
  as a separated merge. On GitLab the role decides, since no rule reserves
  the merge to an admin.
  `.claude/settings.json` allows its two reads as exact commands, so they
  run without an approval prompt; no `gh api` or `glab api` prefix is allowed.

## [1.18.0] - 2026-10-19

A rendered project stops sending its agent to skills plinth v2.1.0 no
longer installs. From that release, plinth installs eight
`mattpocock-skills` skills and lists twelve more, `/ask-matt`,
`/grill-with-docs` and `/wayfinder` among them, which
`claude plugin install mattpocock-skills-extra@plinth` adds. "Starting
something new" in `AGENTS.md` now points at `/plinth:arsenal`;
`docs/agents/domain.md` and `docs/agents/issue-tracker.md` say which skill is
listed and how to add it. Only the wording of those three files changes.
`copier update` from 1.17.0 completed without hands on untouched cli
instances on GitHub and GitLab and an untouched backend instance on GitHub;
hand-edited instances were not updated.

### Changed
- A rendered project no longer sends the agent to skills plinth stops
  installing (coolbress/plinth #593). From plinth's next release,
  `/ask-matt`, `/grill-with-docs`, `/wayfinder` and nine more
  `mattpocock-skills` skills are listed, not installed;
  `claude plugin install mattpocock-skills-extra@plinth` adds them.
  `AGENTS.md`'s "Starting something new" points at `/plinth:arsenal`,
  because `/ask-matt` recommended skills that were not installed.
  `docs/agents/domain.md` says `/domain-modeling` creates `CONTEXT.md`
  without naming `/grill-with-docs`. `docs/agents/issue-tracker.md` says
  `/wayfinder` is listed only and how to add it; the `wayfinder:*` labels
  and the map-and-child steps are unchanged and work by hand.

## [1.17.0] - 2026-10-19

A rendered project is ready for plinth v2.0.0. When a pull request changes
how strict the checks are, an admin's approval now turns `ci / diff-size`
green without a push, and a new project calls plinth v2.0.0. The agent
brings each such change to the person as their decision. Not run yet: a
review-started run in a repository that keeps an older plinth pin. Reading
plinth v1.17.0 and v1.23.0, it should repeat the push run's result.
`copier update` from 1.16.0 completed without hands on untouched cli
instances: on GitHub keeping the old pin, with the tested pin, and with a
pin Dependabot had raised to plinth v1.23.0, and on GitLab keeping the old
pin and its checksum.

The order matters for a repository made from an earlier tag: update the
template first, then raise the plinth pin. `/plinth:template-update` keeps
the pin your workflows call today unless you choose the tested one, so the
update adds the two permissions while CI still calls the plinth it called
before, which runs as it did. Once that update is merged, raising the pin to
plinth v2.0.0 or later is safe, by hand or by Dependabot's pull request.
Choosing the tested pin in the same update moves both together, which is
safe as well. The other order breaks CI: a pin raised to v2.0.0 before the
update makes every check fail at startup, since plinth v2.0.0 asks for
permissions the old `ci.yml` does not give. A Dependabot pull request that
raises the pin and was opened before the update fails the same way; after
the update is merged, ask Dependabot to rebase it, or close it.

### Changed
- A rendered project's CI also runs when a review is submitted or dismissed,
  its `ci` job grants `pull-requests: read` and `actions: write`, and its
  `concurrency` group is keyed on the event (coolbress/plinth #586). From
  plinth v2.0.0, `ci / diff-size` fails a pull request that changes how
  strict the checks are until an admin approves its head; the run that
  approval starts re-runs the latest red run, and the check turns green
  without a push. From a fork the token is read-only and cannot re-run it;
  the check then says to use "Re-run failed jobs". With one `concurrency`
  group for every event, that re-run cancelled the review run that started
  it and the merge was refused as `cancelled` (coolbress/plinth #518).
- The `plinth_sha` default moves from `1e163e2` (plinth v1.17.0) to
  `033fbe3` (plinth v2.0.0), and `plinth_gitlab_integrity` to that commit's
  checksum of `gitlab/python-ci.yml`. A new project calls the check that
  needs the two grants.
- The output style says a change to the checks that `diff-size` lists is
  the person's decision: the agent brings each one with a recommendation
  and what to check, and does not merge that pull or merge request on its
  own word.

## [1.16.0] - 2026-10-17

The agent in a rendered repository keeps the person's language after a skill
loads: in Korean sessions that ran the `verify` skill before a commit, the
progress lines after it were English 1 time in 19 instead of 8 in 18. On
GitLab it reads the status of a job the project adds, such as a backend's
`docker-image`, from the last line of that job's log, under the allow rule
it already had. Still seen after the change, in small samples: a whole final
report in English in 1 of 10 sessions (as on 1.15.0), and the line announcing
`verify` before the call in English in 3 of 15 sessions with the shipped
wording (0 of 10 on 1.15.0). `copier update` from 1.15.0 completed without
hands on an untouched cli instance on GitHub and an untouched backend
instance on GitLab.

### Changed
- The output style's language rule says that what loads into the session, a
  skill's or a command's instructions, `AGENTS.md` or a file the agent opens,
  does not set the language of its messages, and the `verify` skill ends with
  a line saying the same for what the agent tells the person while it runs
  (coolbress/plinth #574). In Korean sessions that called `verify` before a
  commit, 8 of 18 progress lines after the skill call were English on 1.15.0
  and 1 of 19 with this change, ten sessions each. A first wording that said
  "English you read is no reason to switch" made it worse (7 of 8 in five
  sessions) and is not shipped.
- On GitLab, the output style names the read for a job the project adds, such
  as a backend's `docker-image`, whose log has no `Verdict` line:
  `glab ci trace -p <pipeline-id> <job> | tail -n 1`, where `Job succeeded` is
  a pass and any other line is not (coolbress/plinth #571). The `Verdict`
  filter printed nothing for that job whether it passed or failed. Measured on
  a pipeline where it passed and one where it failed; it ran without a prompt
  under the existing `glab ci trace` allow rule, and no rule is added.
- A repository made from an earlier tag gets these only after
  `/plinth:template-update` to the tag that carries them.

## [1.15.0] - 2026-10-17

Before the agent in a rendered repository calls a check green, the output
style now has it read the run with a named command and copy every
`not yet confirmed` line, or say it found none; and it keeps answering in the
person's language for the whole session, also when it quotes English tool
output. On GitLab the commands it names run without a prompt; `glab ci get`
is still not allowed, so a pipeline's variables stay behind an approval.
Still open: on GitLab the named commands do not show the status of a job the
project adds, such as a backend's `docker-image` (coolbress/plinth #571).
`copier update` from 1.14.0 completed without hands on the cli instances
measured on both hosts, including ones with an allow or deny line added by
hand.

### Changed
- The output style names the commands that read a run's `not yet confirmed`
  lines and asks the agent to run them before it calls a check green, then to
  copy every such line word for word or say it found none
  (coolbress/plinth #563): on GitHub `gh run view <run-id>`, whose
  `ANNOTATIONS` carry each job's first nine (the rest are in the job summary,
  which only the run's page shows); on GitLab
  `glab ci trace -p <pipeline-id> <job>`, filtered to the `Verdict` line and
  the `not yet confirmed:` lines, so that one of plinth's jobs whose log has
  no `Verdict` shows as one and is not a pass; a job the project adds, such
  as a backend's `docker-image`, is judged by its GitLab status. At coolbress/plinth-reach#21 the agent
  read the pass/fail list only. Both commands were run on a run that carried
  such a line.
- The language rule moves to a section of its own and says it holds for the
  whole session, and that English in quoted tool output is no reason to
  switch: after a merge, the report had come back in English to a person who
  wrote in Korean.
- On GitLab, `.claude/settings.json` allows `glab ci trace` and the exact
  filter the style pipes it into, `grep -E ' Verdict$|not yet confirmed:'`
  (coolbress/plinth #570). Without them a session in default permission mode
  stopped for an approval before each report; plain `grep` needs no rule, but
  this pattern did. The style reads the pipeline's ID with
  `glab mr view <iid> -F json --jq .head_pipeline.id`, already allowed, rather
  than `glab ci get`, which is not allowed: its `--with-variables` prints the
  pipeline's variables, and a rule on the written flag is passed by a quoted
  spelling. The GitHub commands were already allowed.
- A repository made from an earlier tag gets these only after
  `/plinth:template-update` to the tag that carries them.

## [1.14.0] - 2026-10-16

The agent in a rendered repository now explains its work for a beginner
engineer or a non-engineer by default: the output style is on, renamed, and
adds a decision report at a merge, a template update or a failure, one
recommended option before any choice, and a plain clause for a term at its
first use. A person turns it off for themselves with `/output-style default`.
`copier update` from 1.13.0 completed without hands on four cli instances;
a personal local setting that selected `Non-engineer` needs its line removed.

### Changed
- The output style is on by default and written for a beginner engineer or a
  non-engineer (coolbress/plinth #555). `.claude/settings.json` sets
  `"outputStyle": "Beginner or non-engineer"`, on both hosts.
  `.claude/output-styles/non-engineer.md` becomes
  `beginner-or-non-engineer.md`, and its text no longer assumes a reader who
  will not read the code. Besides the **Insight** block after a change, it
  asks for a decision report at a merge, a template update or a failure (what
  changed; each check's verdict, `pass`, `fail` or `not yet confirmed`, with
  the `not yet confirmed` lines and a dependency review that compared nothing
  read from the run's summary first; what is still unknown, on GitLab that no
  check is required by name; what the person decides, with one recommended
  option), one recommended option before any choice, the command to type when
  a request matches `/plinth:new-project` or `/plinth:template-update`, and a
  plain clause for a term at its first use. The instance's README says what
  the style does and how a person turns it off: `/output-style default`,
  which writes `"outputStyle": "default"` to `.claude/settings.local.json`; a
  user setting does not, because the project's setting takes precedence.
- A repository made from an earlier tag gets the style only after
  `/plinth:template-update` to this tag. A `.claude/settings.local.json` that
  selected `Non-engineer` still takes precedence after the update and names a
  style that no longer exists: until that line is removed, Claude Code uses
  its default style for that person.

## [1.13.0] - 2026-10-13

A new repository can live on GitLab.com: `host: gitlab` renders a
`.gitlab-ci.yml` that includes plinth v1.17.0's GitLab pipeline at a commit
SHA with its checksum, GitLab's merge request and issue templates, and
guidance that names `glab` and merge requests. On GitLab.com Free a rendered
project's merge requests ran green and merged as one squash commit.
`host: github`, the default, renders as before; `copier update` on a GitHub
instance that keeps its pin changes only the answers file, which gains
`host: github`.

### Added
- A `host` question, `github` (the default) or `gitlab` (plinth #353). With
  `gitlab` an instance gets a `.gitlab-ci.yml` that includes plinth's
  `gitlab/python-ci.yml` from GitHub at `plinth_sha` with an
  `include:integrity` checksum, GitLab merge request and issue templates
  under `.gitlab/`, and nothing under `.github/`; its `AGENTS.md`,
  `CONTRIBUTING.md`, issue-tracker guide, `SECURITY.md`, README, settings
  and comments name `glab`, merge requests and the pipeline's job names. A
  service archetype's image check runs with Docker-in-Docker as the job
  `docker-image` (`image` is a GitLab CI keyword). The new
  `plinth_gitlab_integrity` answer carries the checksum; the default is the
  default pin's, and with another pin that commit's checksum is passed (a
  wrong one fails the pipeline with "failed integrity check", before any
  job). `plinth_sha` must be a full commit SHA, on both hosts. With `github` an instance renders as before, given the same
  answers: four archetype and option combinations differ only in the
  answers file's new `host: github` line.

### Changed
- The `plinth_sha` default moves from `3039c32` (plinth v1.15.0) to `1e163e2`
  (plinth v1.17.0), the first release with `gitlab/python-ci.yml`.
  `python-ci.yml` and `pr-label.yml` are the same at both commits, so a
  GitHub instance's checks do not change. This repository's own CI moves to
  the same commit.

### Fixed
- The 1.12.1 note below said `copier update` changes the pin in two workflow
  files. Not by itself: `/plinth:template-update` passes the pin the
  repository's workflows call (coolbress/plinth #219), so an update keeps it.
  The pin moves only when a person chooses the pin the tag was tested with,
  `--plinth-pin tested` (coolbress/plinth #511), as an update of a 1.12.1
  repository to 1.13.0 did: both `uses:` lines and `.copier-answers.yml` then
  named `1e163e2`.

## [1.12.1] - 2026-10-13

A new repository's CI calls plinth v1.15.0 instead of v1.7.2, so its
`ci / test` reports the changed lines no test ran, without failing the check.
`copier update` changes the pin in two workflow files.

### Changed
- The `plinth_sha` default moves from `e52e750` (plinth v1.7.2) to `3039c32`
  (plinth v1.15.0). A new repository's `ci / test` runs the tests under
  coverage and, on a pull request, reports the changed lines no test ran as
  `not yet confirmed`, without failing the check (plinth #503); each job's
  summary says pass, fail or not yet confirmed (plinth #439); `ci / diff-size`
  lists kept test files that lost lines or gained skip markers (plinth #444);
  `ci / lint` gives zizmor the job's token, and every zizmor audit except
  known-vulnerable-actions blocks (plinth #451). No check name, job, input or
  secret a caller passes changes. This repository's own CI moves to the same
  commit.

## [1.12.0] - 2026-10-12

A new repository carries one pre-commit skill instead of two, and refuses
shell file writes so the agent writes code with its edit tools. In five
trials per case, Claude Sonnet 5.5 ran the skill before 4 of 5 commits with
both changes, against 0 or 1 of 5 with either alone or neither.
`copier update` removes one file and changes three; a local edit to
`simplify` is deleted with it, visibly in the update's diff.

### Changed
- A new repository carries one pre-commit skill, `verify`, instead of two. Its
  first step is the cleanup pass `simplify` carried, with the same wording; its
  second runs the commands in `AGENTS.md`'s code block, last.
  `.claude/skills/simplify/` is removed. In coolbress/plinth#496's trials
  (Claude Code 2.1.296, five runs per cell, one small change), Claude Sonnet
  5.5 ran a pre-commit skill before 0 of 5 commits on 1.11.0, 1 of 5 with the
  skills folded, 0 of 5 with the deny rules below, and 4 of 5 with both; Claude
  Opus 5.5 ran one before 5 of 5 in every case. These are trial counts, not a
  rate. They point the same way as coolbress/plinth#474, where Sonnet ran
  `verify` alone before 12 of 14 commits written with its edit tools and 2 of
  16 written from the shell, and with both skills present ran neither before
  any of 10.
  `copier update` from 1.11.0 removes `simplify` without a conflict even
  where the repository edited it, so a local edit there is deleted with the
  file: it shows in the update's uncommitted diff, to carry into `verify`
  before committing.
- `.claude/settings.json` denies `Bash(cat)`, `Bash(tee:*)` and
  `Bash(sed -i:*)`, so the agent writes files with its edit tools. Claude Code
  strips a redirection before it matches a rule, so a heredoc write such as
  `cat > f << 'EOF'` is matched as bare `cat`, while `cat README.md` and
  `cat README.md | head` still run; a rule that spells `>` refuses nothing.
  What it costs: a person who asks for `tee` or `sed -i` is refused too, and
  needs a hand edit of `.claude/settings.json` or their editor. A refusal is
  not a prompt: the call is refused, and when a heredoc is chained after
  another command (`git switch -c … && cat > f << 'EOF'`) the whole call is,
  so the agent runs the first command again. What it lets through:
  `echo … > f`, `printf … > f`, `python3 -c` writes and `cat file > copy`.
  `AGENTS.md` gains one line: write files with the Edit and Write tools; a
  denied call ran nothing and is not a prompt, so the agent writes the file
  with the edit tools and runs any chained commands on their own, and never
  asks the person to approve it or loosen the deny list.

### Fixed
- What 1.10.0's trial counts left unexplained (coolbress/plinth#474): Sonnet's
  fall from 1.9.0's 5 of 6 to 1 of 18 for `simplify` and 2 of 16 for
  `verify` was not the Claude Code version. It followed how Sonnet wrote the
  code, with its edit tools or from the shell, and whether one skill or two
  was present. In those trials Sonnet ran ruff, mypy and pytest before every
  commit anyway, chained after the file writes in the same shell command; what
  the skipped skills left out was `uv build`, `uv sync --locked` and the
  cleanup pass.

## [1.11.0] - 2026-10-11

A new repository's two project skills say what they replace. `verify` runs
the checks, not the app, and points to the bundled `/run` for the running app;
`simplify` also removes wasted work the change adds. `copier update` changes
two files.

### Changed
- The `verify` project skill says it runs the checks, not the app: it takes
  the place of Claude Code's bundled `/verify`, which builds and runs the app,
  and it sends a person who wants to see the change working to the bundled
  `/run`, which nothing replaces (coolbress/plinth#476).
- The `simplify` project skill gains one directive: remove wasted work the
  change adds (repeated computation or I/O, independent steps run one after
  another, blocking work at startup or on a hot path). It is an addition from
  the comparison with the bundled `/simplify`, whose efficiency angle the pass
  lacked; no missed case was observed (coolbress/plinth#476).

## [1.10.0] - 2026-10-10

A new repository's agent is told to clean a change up before a code commit,
through a second project skill, `simplify`, which then runs the checks
`AGENTS.md` lists. It carries the cleanup rules plinth's default set used to
ship in a skill nobody invoked. `copier update` adds one file.

### Added
- A new repository carries a second project skill,
  `.claude/skills/simplify/SKILL.md`. Claude Code tells the agent to run a
  project skill named `simplify`, like one named `verify`, right before a
  commit, except for a commit that changes only documents or only tests; the
  project skill takes the place of the bundled `/simplify` there. The pass
  keeps the agreed behaviour, the tests and `AGENTS.md`'s rules: it reuses a
  helper that exists, removes an abstraction with one use and scaffolding for
  a later need, looks at the standard library, the platform or an installed
  dependency before adding one, and takes the shorter form of the same logic.
  It never cuts validation at a trust boundary, error handling that prevents a
  loss, a security measure or anything the issue asked for. On a commit that
  answers a review finding it covers only the lines that fix touches. It ends
  on the commands in `AGENTS.md`'s code block, named and not copied. The rules
  come from `ponytail-skills`, a skill plinth's default set carried and no
  observed session ever invoked; plinth #302 decided to move them to a skill
  Claude Code is told to run (plinth #467). It is a prompt, not a hook, and
  how often the agent follows it depends on the model. Exploratory runs with
  `claude -p` on Claude Code 2.1.296, on a rendered repository (two more
  runs stopped on permission prompts and are not counted):
  - Claude Opus 5.5 called `simplify` before 3 of 3 commits of a new
    function and 3 of 3 commits answering a planted review finding. It
    called `verify` first in 1 and 3 of those, and ran the checks again after
    `simplify` in 3 of those 4. It called no skill before 2 README-only
    commits.
  - Claude Sonnet 5.5 called `simplify` before 1 of 18 commits of a new
    function (11 with both skills, 7 with `simplify` alone) and 0 of 3
    review-fix commits; `verify` before 2 of 16 new-function commits (11
    with both, 5 with `verify` alone, which 1.9.0's note measured at 5 of 6
    on 2.1.295) and 0 of 3 review-fix commits. It called no skill before 4
    README-only commits.
  - All 6 review-fix commits changed only the fix's lines; Sonnet's ran no
    pass, so that half says nothing about the skill.

  CI stays the gate.

## [1.9.1] - 2026-10-10

The commented-out third-party review job in a new repository's `ci.yml` no
longer carries a rendered commit SHA, so a template update cannot conflict on
a comment nothing keeps in step. The update that brings this version in still
conflicts once on a comment moved by hand; later ones do not.

### Changed
- The commented-out third-party review job in `.github/workflows/ci.yml` no
  longer carries a rendered SHA on its `uses:` line; it names the `ci` job's
  SHA as the one to copy when enabling the job. Nothing kept that commented
  SHA in step with the active lines (Dependabot moves the active ones and
  ignores comments; a hand move can set it to anything), so the next
  `copier update` found three different values there and stopped on a
  conflict: measured on a repository updated from v1.7.1 to v1.9.0, where
  every other change applied without hands. The 1.9.0 note's "without hands"
  held for every file but this line on a repository with a hand-moved comment
  (plinth #463). The update that brings this version in still conflicts once
  on a comment that was moved by hand (the old render, the file and the new
  render differ); after it, the line is the same in every render, so a later
  update keeps whatever the comment says. Both measured with copier 9.18.2.
  The active `uses:` lines are unchanged.

## [1.9.0] - 2026-10-10

A new repository's agent is told to run the checks `AGENTS.md` lists before a
commit, through a project skill named `verify`, and its review budget says how
to judge what is still fixed after two rounds. `copier update` applies both
without hands: one new file and one longer line in `AGENTS.md`.

### Added
- A new repository carries a project skill, `.claude/skills/verify/SKILL.md`.
  Claude Code tells the agent to run a project skill named `verify` right
  before a commit, except for a commit that changes only documents or only
  tests. It is a prompt, not a hook: the agent chooses whether to run it, and
  in 5 of 6 trial code commits it did (the sixth ran most of the checks
  itself). The skill names
  the code block in `AGENTS.md` as the list of commands and copies none of
  them. A red command stops the commit, and a check that looks wrong is fixed
  in the same change or asked about, never committed over in silence. CI stays
  the gate. A plugin's skill does not trigger this, so it ships here and not in
  plinth (plinth #409, #458).

### Changed
- The review-budget line of a new repository's `AGENTS.md` says how to judge
  the class that is still fixed after two rounds: by what the diff does, not
  by the reviewer's severity label. A line of guidance that could say more
  exposes nothing, so it is never that class. When a finding repeats the last
  one's kind, the author rewrites once for the whole kind (plinth #423, #457).
  It stays at 59 lines.

## [1.8.1] - 2026-10-09

The comment on a new repository's Dependabot configuration says how the plinth
workflow pins are kept up to date: bare commit SHAs that Dependabot resolves
to a release on its own, raised together after the default cooldown. No
rendered file changes but that comment.

### Changed
- The comment above the `github-actions` entry of `.github/dependabot.yml`
  no longer promises a version comment the pins do not carry. It says what
  a Dependabot job on a rendered repository showed: the plinth pins are bare
  commit SHAs, Dependabot reads the release from the SHA and raises `ci.yml`
  and `label.yml` together in one pull request after GitHub's default
  three-day cooldown (plinth #455). The rendered `uses:` lines are unchanged.

## [1.8.0] - 2026-10-07

A new repository's agent hands a refused workflow push to a person instead
of widening its token, and writes an issue's ending when a merge closes it.

### Changed
- A new repository's `AGENTS.md` names workflow permission next to
  administration: a push GitHub refuses because it changes
  `.github/workflows/` stops at the commit and goes to a person, who pushes
  it from a separate terminal, and a refusal is never answered by widening
  the everyday token (a re-login or `gh auth refresh`), which can replace it
  with a token that reaches every repository the account can (plinth #417). It also says that closing an
  issue writes its `## Outcome`, and that whoever merges writes it when
  `Closes` closes the issue on merge (plinth #418). It stays at 59 lines.
- `docs/agents/issue-tracker.md` ends a research, prototype or grilling child
  in `## Decision`, not also `## Outcome`, as plinth's own copy does.

## [1.7.1] - 2026-10-05

A new repository calls plinth v1.7.2, whose `ci / deps` no longer fails every
pull request on a private repository without GitHub Code Security.

### Changed
- The `plinth_sha` default moves from `8f4edfc` (plinth v1.5.0) to `e52e750`
  (plinth v1.7.2). On a private repository without GitHub Code Security, a new
  repository's `ci / deps` no longer fails every pull request: GitHub refuses
  dependency review there, and the job now passes with a warning that nothing
  was checked where the repository is not a fork and its dependency graph
  answers (plinth #395). Its CI also carries plinth's fixes since v1.5.0. This
  repository's own CI moves to the same commit.

## [1.7.0] - 2026-10-04

A new repository's issue form, pull request template and `AGENTS.md` tie each
acceptance criterion to the test that checks it.

### Changed
- A new repository ties each acceptance criterion to its evidence (plinth
  #299). The task form's acceptance criteria are a "Done means" checklist,
  ticked when the issue closes, with an unticked one named under
  `## Outcome`. The pull request template asks the description to name, for
  each criterion it meets, the test that checks it or why none does, and says
  a named test shows the criterion was exercised, not proved. `AGENTS.md`
  says both, and a resume reads an issue's unticked criteria; it stays at 59
  lines. No check enforces the form.

## [1.6.0] - 2026-10-03

A new repository calls plinth v1.5.0, which reads a private repository's wall
against its licences, and its checks run again when a pull request is edited.

### Changed
- The `plinth_sha` default, the plinth commit a new repository's CI calls, moves
  from `8e96702` (plinth v1.1.0) to `8f4edfc` (plinth v1.5.0). A new
  repository's `ci / floor-check` then reads a private repository's wall
  against its licences, so one created without the CodeQL rule (no Code
  Security) can merge its first pull request, and reports push protection;
  `ci / pr-title` refuses a title ending in `(#N)`. This repository's own CI
  moves to the same commit.
- A new repository's `ci.yml` runs on the `edited` pull-request event besides
  the default types, so a retitled pull request re-runs `ci / pr-title` and an
  edited description re-reads `ci / diff-size`'s warning without a push
  (plinth #322). Every job re-runs on such an edit; the workflow's concurrency
  cancels the run it replaces. This repository's own `ci.yml` does the same.

## [1.5.9] - 2026-09-29

A new repository's CI calls plinth v1.1.0, so it gets plinth's 1.1 checks on a
pull request that weakens the checks.

### Changed
- The `plinth_sha` default, the plinth commit a new repository's CI calls, moves
  from `2673947` to `8e96702`, plinth v1.1.0. A new repository then gets
  plinth's 1.1 checks: `ci / diff-size` warns about a change to the checks the
  pull request description does not name, and `ci / floor-check` fails when
  the `ci` job no longer calls plinth's workflow at a commit SHA, or carries a
  key other than `uses:`, `with:`, `secrets:` and `permissions:`. The
  generated `ci.yml` passes it unchanged. This repository's own CI moves to
  the same commit.

## [1.5.8] - 2026-09-27

A new repository's CI calls plinth at the commit that carries plinth's pre-1.0
checker fixes, not at a commit from 2026-09-11.

### Changed
- The `plinth_sha` default, the plinth commit a new repository's CI calls, moves
  from `98e8e56` (2026-09-11, plinth 0.5.10's time) to `2673947`. That commit
  carries plinth's pre-1.0 checker fixes: `floor-check` compares each required
  check with the app its ruleset entry pins, reads every ruleset, and
  `pr-review.yml` refuses inputs it cannot honour. With the old default, a repository created
  by plinth 1.0 would have run the old checker until Dependabot raised the pin.
  This repository's own CI moves to the same commit.
- The commented third-party review example asks for `pull-requests: read`,
  not `write`; the check needs no more without the summons secret.

## [1.5.7] - 2026-09-27

A generated repository's settings deny `gh repo delete`, which no required
check can undo.

### Changed
- The generated `.claude/settings.json` denies `gh repo delete`, and
  `AGENTS.md`'s list of what the settings deny names it. The login plinth's
  tutorial recommends can delete any repository the person owns, and no
  required check brings one back. The deny covers the command, not every
  route to the same API (`gh api -X DELETE` is not matched); a ruleset edit
  through `gh api` is not denied either, so `AGENTS.md`'s "never ask for
  administration" still carries that. Found by plinth's pre-1.0 review.

## [1.5.6] - 2026-09-27

A generated repository's agent is told that a decision the next person needs
goes into the issue or pull request, not only into Claude Code's machine-local
memory.

### Changed
- The generated `AGENTS.md` says where a decision lives. Claude Code's
  automatic memory stays on the machine it ran on, so a decision, an
  unverified item or a next step the next person needs goes into the issue or
  pull request, not only into memory. The record in issues and pull requests
  is what a new session, another machine or another engineer can read; since
  2026 the agent also keeps its own memory by default, and nothing said which
  one carries the handover.

## [1.5.5] - 2026-09-26

A generated repository's agent is told to answer in the language the person
writes in, and that a close, fix or resolve word before an issue number
anywhere in a pull request's description closes that issue.

### Changed
- The generated `AGENTS.md` and the `non-engineer` output style say to answer
  the person in the language they write in, summaries included. Code,
  commits, pull requests and documents follow the repository's own
  convention. In plinth's first v1.0.0 release-candidate run the person wrote
  in Korean, and the agent's closing summaries, shaped as the style's
  **Insight** block, came back in English. The style is off by default, so
  `AGENTS.md`, read every turn, carries the line too (#30).
- The generated `CONTRIBUTING.md` step 5, `AGENTS.md` and pull request
  template say that a close, fix or resolve word before `#N` anywhere in the
  description closes that issue on merge, a sentence included. In plinth,
  "the two fixes #65 decided" closed the v1.0.0 issue.
- The 1.5.4 section's opening sentence said a tool's default lines "no longer
  reach `main`"; it now says what the template tells the agent, as the 1.5.4
  Release already does.

## [1.5.4] - 2026-09-26

A generated repository tells its agent that `Assisted-by` is the only line
that marks AI, and to remove a tool's default `Co-Authored-By` and
generated-with line. Whether an agent follows it is not yet observed.

### Changed
- The generated `CONTRIBUTING.md`, `AGENTS.md` and pull request template say
  that `Assisted-by` is the only line that marks AI: a tool's default
  `Co-Authored-By` for the AI and its generated-with line are removed, in
  commits and in the description, while a person's trailers stay. Step 5's
  "existing attribution is preserved" had read as keeping them; in plinth's
  second release-candidate pass the agent kept both, and the generated-with
  line reached `main` (#34).

## [1.5.3] - 2026-09-25

A generated repository's agent merges only when the person says so for that
pull request, with the command that keeps the description as the commit, and
checks a worktree before removing it.

### Changed
- The generated `AGENTS.md` says who merges and how: only when the person says
  so for that pull request, since a yes for one does not carry to the next and
  "tidy up" is not a yes, unless the person gave a standing instruction for the
  session, which the agent then names. It merges with `CONTRIBUTING.md` step
  7's command, never plain `gh pr merge --squash`. Step 7 says the same. It
  also says to run `git status --porcelain --ignored` in a worktree and ask
  before removing it: `git worktree remove` deletes ignored files, such as a
  local data file, without a word. In plinth's v1.0.0 release-candidate run
  the agent merged without asking twice, once in a new session, used plain
  `gh pr merge --squash` for the first pull request, and removed a worktree
  unchecked (#31).

## [1.5.2] - 2026-09-25

A generated repository's `ci.yml` points a reader who wants to know what a
check does, or why it is red, at plinth's Required checks page.

### Changed
- The generated `ci.yml` points "what each check does" at plinth's Required
  checks page, which gives each check, what a red means and the fix, and is
  held to plinth's ruleset by a test there. Before, it pointed at
  `python-ci.yml`, the workflow's source; the comment still names it as the
  implementation (#27).

## [1.5.1] - 2026-09-24

A generated repository's `CONTRIBUTING.md` gives the merge command that keeps
a pull request's description as its squash commit, so a description does not
land on `main` hard-wrapped at 72 columns.

### Changed
- The generated `CONTRIBUTING.md` (step 7) and this repository's own (step 5)
  give the merge command that makes the squash commit the pull request
  description: `gh pr merge --squash` with the description passed as `--body`.
  Without it GitHub's default squash message is the description hard-wrapped
  at 72 columns, so a description written at about 80 columns lands on `main`
  with stray one-word lines. Both `AGENTS.md` files point at that step. Found
  and measured in coolbress/plinth#250 (#24).

## [1.5.0] - 2026-09-22

`plinth_sha` is a recorded answer, so an update can be told to keep the pin
the repository already has.

### Changed
- `plinth_sha` is asked and written into `.copier-answers.yml` instead of
  being computed on every render. While it was `when: false`, copier neither
  recorded it nor let `--data` override it, so each `copier update`
  re-rendered the `uses:` pins from this template's own default: a conflict in
  every workflow file of an instance whose Dependabot had raised them — which
  is every instance, given time — and a silent move back to the template's
  value where it had not. Measured on copier 9.18.2: with the answer recorded,
  `copier update --data plinth_sha=<the pin the repository has now>` keeps the
  pin, records it, applies the template's real workflow changes and conflicts
  nowhere. A render still takes this file's value by default, so nothing
  changes for a new project; the by-hand render in `CONTRIBUTING.md` now asks
  one more question, and Enter answers it (#22).

## [1.4.3] - 2026-09-22

An instance's tree-hygiene tests skip a fresh render whatever language git
speaks, instead of failing on three of them.

### Fixed
- `tests/test_tree_hygiene.py` asks git for its file list with `LC_ALL=C`, so
  the narrow "not a git repository" skip meets the message it was written
  against. git translates that message, and gettext prefers `LANGUAGE` over
  the locale, so where git speaks another language the skip missed and all
  three tree-hygiene tests failed with `git ls-files failed: …` instead. That
  is the state of the by-hand render check `CONTRIBUTING.md` documents, which
  runs pytest in a directory that is not a repository yet, and of this
  template's own render test (#19). The skip still reads the message rather
  than the exit status: 128 is git's general fatal status, and a broken
  `GIT_DIR` inside a real work tree returns it too, so keying on the number
  would widen the skip. The template's test suite now builds the translated
  case itself — `LANGUAGE` with `LC_ALL` and `LC_MESSAGES` removed and `LANG`
  naming a real locale — and fails if it cannot.

## [1.4.2] - 2026-09-21

Branch instructions name their base, the agent file says what to do about a
checkout another session may be using, and a worktree made under `.claude/`
is ignored.

### Added
- `AGENTS.md` opens `## Always` with the shared-checkout rule: before editing,
  inspect the branch, working-tree changes, worktree list and commits ahead of
  the intended base (`git fetch origin`, then `git status -sb`,
  `git worktree list`, `git log --oneline origin/main..HEAD`). Those show the
  state of the checkout, not who else is using it: no command shows another
  session, so a clean checkout on `main` is not proof that it is yours alone.
  When it is not, or when it holds unrelated or unexplained work, leave it
  untouched and work in a uniquely named worktree branched from an explicitly
  verified base; never switch, reset, rebase or stash another task's checkout
  (plinth #218).
- `.gitignore` ignores `.claude/worktrees/`, which Claude Code's documentation
  asks for and which the rule now names as the worktree's path. Without the
  line, `git add .` after `git worktree add .claude/worktrees/x -b wt-x`
  stages the worktree as a `160000` gitlink, which git warns about and a
  reader who does not open the diff commits: a clone will not contain it and
  will not know how to get it. With the line, nothing of the worktree is
  staged.

### Changed
- Every branch instruction names its base, and a worktree is the default
  wherever the checkout may not be yours alone: `git fetch origin`, then
  `git worktree add --no-track -b <type>/<slug> .claude/worktrees/<slug> origin/main`,
  or `git switch -c <type>/<slug> --no-track origin/main` in a checkout that
  is. `git switch -c <type>/<slug>` alone starts the branch at whatever `HEAD`
  is; run from another task's scratch commit it carries that commit into the
  new branch, which is the incident behind plinth #218. `--no-track` leaves
  the new branch with no upstream: tracking `origin/main`, a bare `git push`
  refuses, and the fix git prints first is `git push origin HEAD:main` — a
  push to `main`, not to the branch. Naming the base does not stop uncommitted
  changes riding along — git carries compatible ones onto the new branch and
  prints only `M file` — which is why the rule above is a separate guard and
  not the same one said twice.

## [1.4.1] - 2026-09-13

The `image` job's comment tells a server instance to capture `docker logs`
before piping, so a closed pipe cannot fail a healthy container.

### Fixed
- The `image` job's comment shows a server instance how to read the container
  log: capture `docker logs` into a variable, then pipe from the variable. An
  instance that rewrote the step as `docker logs … | head -1` failed on some
  runs with exit 141, `head` closing the pipe before `docker logs` finished
  and `pipefail` counting the SIGPIPE, with the container healthy
  (plinth #151). The template's own line already captured before piping; the
  test now refuses a live docker process on a pipe and requires the capture
  form in the comment.

## [1.4.0] - 2026-09-11

A service instance gets an image check, the label check finally runs in an
instance's CI, and the agent file says a ruleset change is a person's.

### Added
- A backend or data-ml instance's `ci.yml` carries an `image` job: build the
  Dockerfile, run the image, read its first log line. A plain job, not one in
  python-ci.yml, so a cli or library instance never carries it; the check name
  is `image`, and `/plinth:new-project` requires it in the ruleset for these
  archetypes (plinth #127). The entry point has no port yet, so the one
  request is a run to completion; a server replaces that line with a `curl`.
- `AGENTS.md`: never ask for administration on the everyday token; a ruleset,
  required-check or code-scanning change is a person's, typed through plinth's
  `scripts/with-admin-token.sh` or made in Settings. `CONTRIBUTING.md` states
  the limit: the wall stops the everyday agent, not the administrator
  (plinth #129).

### Changed
- `plinth_sha` is `98e8e56` (plinth after v0.5.4). The pinned python-ci.yml
  now carries the label check (plinth #100) and counts what a run could not
  verify (plinth #124); `13e5082` predated both, so granting `issues: read`
  against it would have changed nothing.

### Fixed
- `ci.yml` grants `issues: read` to its python-ci.yml call, on the job. A
  called workflow cannot widen what its caller grants, so `ci / floor-check`'s
  label check read an API error and reported `not verified` in every instance
  (plinth #102).
- Dependabot's docker updates ignore major and minor: a Python minor bump moves
  the build stage, `.python-version` and mypy together. `python:3.12-slim` to
  `3.14-slim` was green on every required check and could not start, the
  virtualenv copied from the 3.12 build stage pointing at an interpreter the
  run image lacked (plinth #120). Digests and patches still rise.

## [1.3.0] - 2026-09-10

The agent settings also stop a `cat` or `grep` of `.env` inside `$(...)` or a
subshell, where the Read deny does not look.

### Fixed
- `.claude/settings.json` also denies `Bash(cat *.env)` and `Bash(grep *.env)`.
  The Read deny's Bash check sees only a top-level command: measured on Claude
  Code 2.1.267, `echo "$(cat .env)"`, `x=$(cat .env)`, `export $(cat .env |
  xargs)`, `(cat .env)` and `{ cat .env; }` ran with `Read(./.env)` denied in
  every spelling (anthropics/claude-code#89055). A Bash rule reaches those:
  with the two rules every one of them and `env $(grep -v "^#" .env | xargs)`
  is refused, while `cat .env.example`, `grep KEY .env.example` and
  `grep -rn "os.environ" .` still run. Still open, and said in README and
  AGENTS.md: `bash -c "cat .env"`, another reader inside `$(...)`
  (`x=$(head -1 .env)` returned the value), `grep -r SECRET .`, an
  interpreter (plinth #136).

## [1.2.0] - 2026-09-10

The agent settings also stop a sourced `.env`, and the documents say what the
deny reaches and what only the sandbox does.

### Fixed
- `.claude/settings.json` also denies `. ./.env` and `source .env`
  (`Bash(. *.env*)`, `Bash(source *.env*)`). Measured on Claude Code 2.1.267
  with the sandbox off: `Read(./.env)` already stops `cat`, `head`, `tail`,
  `sed`, `grep` and `<` in Bash, alone or in a pipe, `&&` or `;` chain, but a
  sourced `.env` ran, and a line that was not `KEY=VALUE` printed its value
  in the shell's error (plinth #128). The two rules stop every sourcing shape
  tried, `set -a; . ./.env; set +a` included, and leave `.venv/bin/activate`
  alone. Not covered by any deny rule, and now said in README and AGENTS.md:
  `$(cat .env)`, `bash -c "cat .env"`, an interpreter opening the file; the
  sandbox's `denyRead`, already written, stops those when the sandbox is on.

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
