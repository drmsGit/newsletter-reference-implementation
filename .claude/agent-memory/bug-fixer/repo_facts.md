# Facts not worth re-deriving

## Running the suite

The documented command works verbatim. Baseline before my first run: **157 pass**
(158 with the one test I added). `.env` absent is fine.

```
cd <worktree>/backend && \
  /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python \
  -m pytest tests/ -q
```

**Do not write `cd <main>/backend 2>/dev/null || cd <worktree>/backend`** — the
first branch succeeds and you silently read and edit the main checkout. Use the
worktree's absolute path only. I nearly verified the wrong tree this way; caught
it by diffing main vs worktree (they were identical, so no harm).

## My own definition is not in the worktree

`.claude/agents/bug-fixer.md` exists only in the **main checkout** — it postdates
the worktree branch point, so the worktree's `.claude/agents/` has no
`bug-fixer.md`. Read it read-only from the main checkout.

## Shared dev Postgres

Confirmed: the suite runs against the live dev DB. Tests that need engagement
fixtures can hang an `EngagementEventDB` off an existing `DeliveryExecutionDB`
(id 1, recipient 39) and an existing `ContentCategoryAssignmentDB`
(content_id 1 → categories 2 and 11) — treat those as handles for *where* to
write, never as expected values, per `tests/test_signals.py`'s own docstring.
Delete the rows and restore any `AppConfigDB` key you set, in `finally`.

A `SIGNAL_WEIGHTS` config row **already exists** in the dev DB with values equal
to the code defaults — read it and restore it rather than writing `{}`.

## Backlog navigation

`docs/backlog.md`: 315 lines / ~200KB. Sections at: Bugs 23, Features 53,
Needs ADR 146, Won't Do 200, Done 204, Related 313. Grep a section with
`awk 'NR>=23 && NR<=52'`, then `awk 'NR==<n>' | fold -s -w 160` for one item.

## Memory does not survive the worktree (IMPORTANT)

Run 2 discovered run 1's memory stranded in `.claude/worktrees/agent-afd52ccdfdbe71252/`,
never merged to the main checkout — so run 2 started blind despite run 1 having
written good notes. `memory: project` writes into *this* worktree, and the
worktree is never committed (by design: we leave it dirty for a human).

Run 2 carried run 1's files forward by copying them. That does not scale. **Tell
the human, every run, that agent memory needs to be copied out of the worktree
or it is lost.**
