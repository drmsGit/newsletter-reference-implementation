# Newsletter Architecture

Open-source newsletter architecture MVP. Teachable and tailorable, not a fixed
commercial product. Learnings feed the separate Condor use case.

## Where things live
- ADRs: `docs/architecture/ADR/` — numbering is sparse and permanent. **No
  count or highest number is recorded here on purpose**: every figure this
  line has carried went stale within days. Run `ls` and read the directory.
- ADR filenames: `ADR-NNN — Title Case Title.md` (em dash, spaces, NOT kebab-case)
- Cross-references are Obsidian wikilinks: `[[ADR-101 — Provider Capabilities Are Explicit]]`
- Strategy + decision log: `docs/playbook-strategy.md` — the live business record
- Queue: Backlog.md tasks in `docs/queue/tasks/`, read and written only through
  the `backlog` CLI (config: `backlog.config.yml`). Inside the vault so task
  wikilinks resolve.
  - **Order is priority: `ordinal` ascending = do next.** Plain `task list`
    sorts by priority first, so always pass `--sort ordinal`:
    `backlog task list --status "To Do" --sort ordinal --plain`.
  - The old sections are ordinal ranges: 1xxxxx Bugs, 2xxxxx Features,
    3xxxxx Needs ADR, 5xxxxx Done. Bugs outrank features of similar importance.
    Ordinals step by 100, so a new item slots between neighbours without
    renumbering them.
  - `priority` (P0–P3) is set only where an entry states one; `Parked` means
    it must be prioritised before anything else happens to it.
  - Labels: `needs-adr` (📋 — blocked on a design decision), and area
    `backend` / `frontend` / `docs`. Type: bug / feature / chore / docs / decision.
  - Done tasks are moved to `docs/queue/completed/` (`backlog task complete
    task-N`). There they drop out of `task list`, the board and `backlog
    search`; reach them with `backlog task view task-N` or by grepping
    `docs/queue/completed/`. Check there before calling something unfixed.
  - Descriptions are essays, not tickets: keep the reasoning and `file:line`
    citations; never summarise an entry down.
  - Backlog.md's own `docs/queue/decisions/` and `docs/queue/docs/` stay
    unused — decisions go in ADRs or `docs/business/decisions/`.
- `docs/backlog.md` is a signpost to the queue since 2026-09-27. Never add to
  it. The last full version is `git show b70f432^:docs/backlog.md`; the "line
  N" in each migrated task's notes refers to that version. ADRs and agent
  memory cite `docs/backlog.md:NNN` as it stood on the date they were written,
  and the file's length changed a lot over time, so resolve those against that
  date: `git show $(git rev-list -1 --before=<date written> HEAD):docs/backlog.md`. The citations themselves are historical; do not
  rewrite them.
- Business context: `docs/business/` — brief, positioning, gates, assumptions
- Business decisions: `docs/business/decisions/` — same shape as ADRs
- Technology explainers: `docs/implementation/` — one file per technology,
  pitched below the ADRs: what it is, why it was chosen, what was rejected.
  **This tier has its own template and it is NOT an ADR** — it carries an
  `## Alternatives Considered` section, which ADRs must never have.
- `docs/` is an Obsidian vault; `backend/` is outside it, so code paths are
  written as inline code, never wikilinked.

## ADR rules
- Required sections: `## Status`, `## Context`, `## Decision`,
  `## Consequences` (with `### Positive` and `### Negative`), `## Related ADRs`
- `## Notes` is optional and used by most records. Absence is never a defect.
- There is no "Alternatives Considered" section. Do not add one.
- Status lives twice and must agree: lowercase `status:` in YAML frontmatter,
  Title Case under `## Status`.
- Status is one of: Proposed | Accepted | Superseded by ADR-NNN | Deprecated
- Never edit an Accepted ADR's Decision. Supersede it with a new ADR instead.
  Supersessions so far: ADR-165 supersedes ADR-001 (2026-09-12), ADR-186
  supersedes ADR-178 (2026-10-04). Still rare enough to be worth saying out
  loud when you propose another.
- To amend an Accepted ADR without superseding it, append a dated addendum
  section (the ADR-101 pattern), never a rewrite of Decision.
- Never renumber. Numbers are permanent identifiers.
- ADR-003, -004, -005, -127, -128, -129 were reformatted; treat their current
  form as the reference template.

## Working rules
- Never read all ADRs into the main session. Delegate the sweep to a subagent.
- Architecture decisions are made in this repo, not in chat. If a decision is
  reached elsewhere, write the ADR before implementing it.
- Business-side decisions go in `docs/business/decisions/`, not in ADRs.
- **An accepted ADR is not an implementation plan.** Before implementing one,
  hold a **final-design pass**: where exactly each part lands, which existing
  functions it reuses, what it deliberately does not touch, and what could
  break. Decisions taken silently under "just implementing what was agreed"
  are still design decisions, and they are the ones nobody reviewed.
- Do not invent ADR numbers. **Run `ls docs/architecture/ADR/` and take the
  highest — do not trust a number written here.** This line has gone stale
  twice in three days (154 → 165 → 166), because the number changes every
  time an ADR is written and nothing updates the rule that records it.
- Never read the .env file. If you need information out of this file, ask.

## Before any code change
State, before touching any file — whether asked to review, suggest, or implement:
1. Which file(s) will change
2. What the change does
3. Which ADR (by number) governs it — if none applies, say so explicitly
4. What could break or is unverified

## Positioning gate
Public beta is blocked on the positioning statement, not on features.
Current state: see `docs/business/POSITIONING.md`.
Which gates still block public exposure is recorded in
`docs/business/LAUNCH-GATES.md` and nowhere else — read it rather than a
summary here. This line once named gate 3 as open for two weeks after it
closed (2026-09-18).

<!-- BACKLOG.MD GUIDELINES START -->
<!-- backlog.md-instructions-version: 1.53.0 -->
<CRITICAL_INSTRUCTION>

## Backlog.md Workflow

This project uses Backlog.md for task and project management.

**At the beginning of each conversation in this project, run `backlog instructions overview` before answering or taking action. Re-read it only if you have not read it yet in the current conversation.**

Use the overview to decide whether to search, read, create, or update Backlog tasks.

Before task lifecycle actions, read the matching detailed guide:
- `backlog instructions task-creation` before creating or splitting tasks
- `backlog instructions task-execution` before planning, changing status or assignee, adding a plan or implementation notes, or implementing task work
- `backlog instructions task-finalization` before checking acceptance criteria, writing final summaries, or moving tasks to terminal statuses

Use `backlog <command> --help` before running unfamiliar commands. Help shows options, fields, and examples.

Do not edit Backlog task, draft, document, decision, or milestone markdown files directly. Use the `backlog` CLI so metadata, relationships, and history stay consistent.

</CRITICAL_INSTRUCTION>
<!-- BACKLOG.MD GUIDELINES END -->
