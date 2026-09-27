Check the task queue (`docs/queue/`, Backlog.md) for structural problems and report them. This is a read-only check, not a grooming session: nothing is fixed, reordered or closed unless the user says so.

## Step 1 — run the check
Run `python3 .claude/scripts/queue_check.py` from the repo root. It reads every task file against `backlog.config.yml` and prints `ERROR`, `WARN` and `INFO` lines, then exits 1 if there are errors.

It checks, mechanically:
- a Done task still in `tasks/`, or an open one in `completed/`
- duplicate task IDs, and filenames that disagree with their ID
- duplicate ordinals, and ordinals outside the Bugs / Features / Needs ADR ranges
- `needs-adr` tasks outside the Needs ADR range, and the reverse
- dependencies, and `task-N` mentions in descriptions or notes, that point at no task
- statuses, priorities, types and labels the config does not know
- wikilinks in open tasks that do not resolve in the vault
- open tasks with no type or no area label (warnings)

## Step 2 — report
Group the output by kind rather than pasting it. For each error, name the task and the one-line CLI fix. For example:
- `backlog task complete task-N` for a Done task left in `tasks/`
- `backlog task edit task-N --labels …` for a wrong label

Keep the `INFO` list of Parked tasks to one line; it is a reminder, not a finding.

## Step 3 — fix only with the user's go-ahead
Offer the fixes; apply none until the user says which. Then:
- **Use the `backlog` CLI, never edit a task file by hand.** The Backlog.md block in `CLAUDE.md` says so, and a status edit alone leaves a Done task in `tasks/`. Use `backlog task complete`.
- **Never change an ordinal or a priority to make a check pass.** Order is a record of the user's decisions. A duplicate ordinal is reported and the user picks which task goes first.
- **Never rewrite a description.** Descriptions are the original entries, verbatim. A broken wikilink inside one is reported; whether to fix the text is the user's call.
- Stage by path (`git add docs/queue`), never `git add -A`.

## What this does not do
It does not judge content: whether a task is still true against the code, whether an ADR has quietly answered it, whether two tasks are the same work. Those need reading and belong to the `backlog-sequencer` agent. If the check turns up something that looks like one of those, say so and suggest the sequencer; do not investigate it here.

Do not write counts from the output into any file.
