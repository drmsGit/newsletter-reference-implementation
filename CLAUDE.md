# Newsletter Architecture

Open-source newsletter architecture MVP. Teachable and tailorable, not a fixed
commercial product. Learnings feed the separate Condor use case.

## Where things live
- ADRs: `docs/architecture/ADR/` — 83 records, numbered to 167 (sparse)
- ADR filenames: `ADR-NNN — Title Case Title.md` (em dash, spaces, NOT kebab-case)
- Cross-references are Obsidian wikilinks: `[[ADR-101 — Provider Capabilities Are Explicit]]`
- Strategy + decision log: `docs/playbook-strategy.md` — the live business record
- Queue: `docs/backlog.md` (Bugs / Features / Needs ADR)
- Business context: `docs/business/` — brief, positioning, gates, assumptions
- Business decisions: `docs/business/decisions/` — same shape as ADRs
- `docs/` is an Obsidian vault; `backend/` is outside it, so code paths are
  written as inline code, never wikilinked.

## ADR rules
- Required sections: `## Status`, `## Context`, `## Decision`,
  `## Consequences` (with `### Positive` and `### Negative`), `## Related ADRs`
- `## Notes` is optional — 45 of 81 records use it.
- There is no "Alternatives Considered" section. Do not add one.
- Status lives twice and must agree: lowercase `status:` in YAML frontmatter,
  Title Case under `## Status`.
- Status is one of: Proposed | Accepted | Superseded by ADR-NNN | Deprecated
- Never edit an Accepted ADR's Decision. Supersede it with a new ADR instead.
  One supersession exists: ADR-165 supersedes ADR-001 (2026-09-12). It is still
  rare enough to be worth saying out loud when you propose another.
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
One P0 defect still blocks public exposure — gate 3, inbound machine
authentication. See `docs/business/LAUNCH-GATES.md`.
