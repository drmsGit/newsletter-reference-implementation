# Memory Index — backlog-sequencer

First run 2026-09-12. Refine these files on later runs; do not rebuild the graph from scratch.

- [Dependency edges](graph-edges.md) — the durable blocks/blocked-by set, with the evidence line for each edge
- [Cost-of-delay classes](cost-of-delay.md) — Rises / Flat / Decays, with the reason each item rises and who pays the tax
- [Same-surface batches](same-surface-batches.md) — file-level clusters, verified against the tree
- [Needs-ADR downstream map](needs-adr-downstream.md) — the 15 items and what sits behind each interview
- [Staleness watchlist](staleness-watchlist.md) — contradictions found, and which are already confirmed against code

## Standing constraints (do not re-derive)
- Never edit `docs/backlog.md`. Top of section = do next is a human decision record.
- Write access is this directory only.
- No calendar time, velocity, hours, or story points, ever.
- `docs/backlog.md` is ~197KB across only 315 lines — each item is ONE very long line.
  Grep by section, then `awk 'NR==<n>'` a single item and pipe through `fold -s -w 160`.
  Section line ranges as of 2026-09-12: Bugs 23-51, Features 53-147, Needs ADR 148-203,
  Won't Do 204-207, Done 208-312.
