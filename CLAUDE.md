# Newsletter Architecture

Open-source newsletter architecture MVP. Teachable and tailorable, not a fixed
commercial product. Learnings feed the separate Condor use case.

## Where things live
- ADRs: `docs/architecture/ADR/` — 75 records, numbered to 154 (sparse)
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
- `## Notes` is optional — 39 of 75 records use it.
- There is no "Alternatives Considered" section. Do not add one.
- Status lives twice and must agree: lowercase `status:` in YAML frontmatter,
  Title Case under `## Status`.
- Status is one of: Proposed | Accepted | Superseded by ADR-NNN | Deprecated
- Never edit an Accepted ADR's Decision. Supersede it with a new ADR instead.
  Nothing has been superseded yet — you would be the first, so say so.
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
- Do not invent ADR numbers. Check the highest existing number first (154).

## Before any code change
State, before touching any file — whether asked to review, suggest, or implement:
1. Which file(s) will change
2. What the change does
3. Which ADR (by number) governs it — if none applies, say so explicitly
4. What could break or is unverified

## Positioning gate
Public beta is blocked on the positioning statement, not on features.
Current state: see `docs/business/POSITIONING.md`.
Two P0 defects also block public exposure — see `docs/business/LAUNCH-GATES.md`.
