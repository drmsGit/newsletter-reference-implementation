---
name: review-only-never-edit
description: This agent reports findings and never edits backend/, docs/ or storage/ — write access is scoped to its own memory directory only
metadata:
  type: feedback
---

Report findings; never apply them. Write/Edit are scoped to
`.claude/agent-memory/code-slimmer/` and nothing else — not `backend/`, not
`docs/`, not `storage/`, not the rest of `.claude/`. This holds even when asked
mid-run to "just fix it".

**`docs/backlog.md` is off limits including appends** — read it to avoid
re-reporting known items, never write to it. An item reaches the backlog only
after the human triages the report and chooses *act/fix*, the same gate
`/interview-review` applies. Appending would wreck its priority ordering and
park false positives beyond the context that would catch them.

**Why:** deleting code merely *believed* dead is the exact failure this agent
exists to prevent, and in a reference architecture the usual signal — no
callers — is inverted for every seam example. A reviewer that can fix what it
should have reported stops reporting. If a change is wanted it is the human's
to make, or to delegate to a session allowed to make it.

**How to apply:** findings go in three buckets, most confident first —
Confirmed (traced, genuinely unreachable) / Suspected (name the dynamic path
that could reach it) / Design smell (works, but duplicated, over-built or
misplaced). Each gets file+line, why it is unnecessary, impact of removal, risk
before deletion, and a cleanup plan ordered safest-step-first. Be aggressive in
what you look for and conservative in what you call Confirmed. Cap at 15.

Two project rules that shape the report: an ADR beats tidiness — name the
number and report the tension rather than recommending around it; and open
forks are noted as options, implemented in the final MVP package, never chased
one at a time (so: no rewrites proposed).

Working method that kept this cheap: read the module pages in
`docs/architecture/Code/` first (Purpose / Public surface / Invariants per
module), then `rg` counts, and only read a file whole when a finding needs its
context. Never load the tree into the session.

Related: [[seams-do-not-flag]], [[backlog-already-logged]]
