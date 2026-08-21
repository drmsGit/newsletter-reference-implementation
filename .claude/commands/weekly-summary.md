Summarize what happened in this repository over the last 7 days — or since the last entry in `docs/weekly-summary.md`, if that's more recent than 7 days ago.

Gather from:
- `git log` — commits, files touched, and commit messages in the window
- ADRs added or changed in `docs/architecture/ADR/`
- `docs/backlog.md` — items added, resolved, or reprioritized
- `docs/architecture/interview-prep/` — new baselines generated, or questions resolved via `/interview-review`
- `docs/business-interview.md` and `docs/business-interview-baseline.md` — findings resolved via `/business-review`
- `docs/playbook-strategy.md` Decision Log — new entries in the window

Produce two sections:

## Technical
What was built or changed, grouped by feature/module. Note ADRs touched, backlog items closed or added, and interview-prep questions resolved. Reference specific files/functions where it matters.

## Business / Project
What strategic or business decisions were made or logged, referencing the relevant Decision Log entries and business-interview resolutions by date. Flag any findings still `🟡 deferred` or `⚠️ unsure` that are worth surfacing as still-open.

Keep it tight — this is a digest, not a report. Point to existing logged entries by file and date rather than re-explaining decisions already recorded in full elsewhere.

Append the result to `docs/weekly-summary.md` under a new `## Week of <date>` heading, most recent entry first. Create the file with that heading if it doesn't exist yet.
Delegate any full-set ADR or codebase sweep to a subagent; the summary is composed in the main session from what comes back, never from reading the sets directly.
