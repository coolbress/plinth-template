# Triage labels

Skills refer to five triage roles by name. This table maps those names to the
label strings in this tracker. Labels are created by `/plinth:new-project` when the repository is created;
no skill creates them. (mattpocock/skills seed, MIT.)

| Label in mattpocock/skills | Label in our tracker | Meaning |
| --- | --- | --- |
| `needs-triage` | `needs-triage` | A maintainer has to evaluate it |
| `needs-info` | `needs-info` | Waiting on the reporter |
| `ready-for-agent` | `ready-for-agent` | Fully specified; an AFK agent can take it |
| `ready-for-human` | `ready-for-human` | Needs a human to implement |
| `wontfix` | `wontfix` | Will not be done |

When a skill names a role (for example "apply the AFK-ready triage label"), use
the string in the right-hand column. To use different words, change only that
column.
