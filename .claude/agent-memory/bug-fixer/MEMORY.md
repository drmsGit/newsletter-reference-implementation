# Memory Index

- [Items already fixed](items_fixed.md) — backlog entries I have implemented; check before starting, the open sections are not pruned
- [Items refused or blocked](items_refused.md) — entries that are underspecified, sit behind the protected-path wall, or depend on another open entry. Check here first: two of the 🔴 auth entries are not implementable as written.
- [Repo facts worth not re-deriving](repo_facts.md) — suite baseline (157), how to run it, DB quirks, and the DB-free test shape

Memory now lives in the main checkout and persists; the worktree-strands-memory
problem from runs 1-2 is fixed, do not re-report it.

Items are not always from `docs/backlog.md` — run 4's came from
`docs/architecture/code-slimmer-report.md` (245KB; grep the finding, never read it
whole, and read its `## Unverified — the specific checks a human should run`
section for your finding's precondition before changing anything).

Writing memory here needs a plain one-part Bash append from the scratchpad; the
`Write`/`Edit` tools refuse paths outside the worktree. See the harness note at
the end of `items_fixed.md`.
