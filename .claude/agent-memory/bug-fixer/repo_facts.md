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

## Memory persistence — RESOLVED as of run 3

Runs 1 and 2 wrote memory *inside* the worktree, where it died with it. The
definition now mandates writing to the main checkout by absolute path:
`/Users/diedeslembrouck/Projects/newsletter-reference-implementation/.claude/agent-memory/bug-fixer/`
Run 3 wrote there and it persisted. **Stop flagging this to the human — it is
fixed.** Just remember: that directory is the only path outside the worktree you
may write, and memory is the only thing you may write there.

## My own definition IS in the worktree now (supersedes the note above it)

`.claude/agents/bug-fixer.md` is committed as of run 3, so the worktree copy and
the main-checkout copy are identical. Either is fine to read.

## Verified suite baselines

- Run 1 worktree: 157 pass (158 with its added test).
- Run 3 worktree: 157 baseline, 161 with its 4 added tests. So the branch point
  is the same 157 — the baseline is stable across worktrees.

## Tests that need neither DB nor network

`monkeypatch` over `os.environ` plus a pure function import runs in ~0.01s and
touches nothing shared. Prefer this shape whenever the defect is in a pure
helper (`providers/adapters/`, `ai/adapters/`, signature/parsing code) — it
sidesteps the shared-Postgres hazard entirely.
