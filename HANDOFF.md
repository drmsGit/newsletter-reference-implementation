# HANDOFF — Newsletter Blueprint → business account

**Written:** 2026-09-04 · **Old-account contract ends:** 2026-09-26
**Purpose:** move this project cleanly from the old Claude account (desktop-app
sessions) to the new business account. The Claude Code **Terminal is already on
the new account**; the desktop-app session histories are what won't carry over.

---

## ▶️ Paste this into your first business-account session

```
Continue work on the Newsletter Blueprint at
/Users/diedeslembrouck/Projects/newsletter-reference-implementation — a
vendor-neutral reference architecture for email marketing systems (FastAPI
modular monolith + server-side Jinja UI), published as a playbook + starter
package. This is a fresh session on a new account; there is no prior chat
history, so rebuild context from disk.

READ FIRST (in order):
1. HANDOFF.md (repo root) — account-migration notes + the open queue below.
2. CLAUDE.md (repo root) — project rules. The ADR discipline there is strict:
   required sections, status-in-two-places, never edit an Accepted ADR's
   Decision (supersede instead), never renumber, highest ADR number is 154 +
   the proposed 160–164.
3. docs/playbook-strategy.md (§5 Decision Log, §6 Roadmap, §7 Open Questions),
   docs/backlog.md (13 bugs / 43 features / 15 Needs-ADR), docs/business/
   (BRIEF, POSITIONING, LAUNCH-GATES, ASSUMPTIONS, BETA-SCOPE.md).
4. Your memory entry "Newsletter Architecture Project" — recent session arc.
   Trust but verify any file:line claims against current code.
5. `git log --oneline -12` — note commit 220edb5 (ADRs 160–164) may be
   unpushed; `git push` if you want it on origin/main.

WORKING STYLE (how the prior sessions ran):
- State, before touching any file: which files change, what the change does,
  which ADR governs it (by number, or "none"), and what could break.
- Architecture decisions are written as ADRs in the repo BEFORE implementing,
  never settled only in chat. Business-side decisions go in
  docs/business/decisions/, not ADRs.
- One question at a time in interview/review passes; you decide each, nothing
  is written into an ADR until you've made the call.
- Never read all ADRs into the main session — delegate the sweep to a subagent.

IMMEDIATE QUEUE (finish these; details in HANDOFF.md):
1. Omni-channel: review/accept ADRs 160–164 (currently Proposed); write the 8
   dated addenda (ADR-001, 021, 062, 063, 101, 103, 121, 122); resolve the 3
   open decisions (ADR-001's fate, disabling an unlicensed channel, address-pick
   when a recipient has several rows per channel).
2. Run the backlog-sequencer agent (now unblocked: interview closed, ADRs
   written, BETA-SCOPE.md exists), then do the Cowork timeline pass.
3. (Optional) Promote/apply the two code-slimmer fixes: the Settings weight
   editor ("applies immediately" but doesn't) and the content_card dropdown.

Do NOT touch the 15 Needs-ADR items unless I ask — they were deliberately left
open across multiple review passes.
```

---

## Account migration — what carries over, what doesn't

| Carries over (on disk, account-independent) | Does **not** carry over |
|---|---|
| The whole git repo, all commits, all docs & ADRs | Desktop-app **session histories** under the old account |
| `.claude/agents/` and `.claude/commands/` (custom agents & slash commands) | The conversational context inside those sessions |
| Your on-disk memory folder for this project | — |

**So:** the only thing at risk is the *unwritten* context still living in old-account
sessions. This file + the queue below capture it. After 2026-09-26 the old
account lapses — finish the OPEN sessions (below) before then, or make sure their
state is written to disk (it now is, here).

*Optional / separate concern:* the git remote is
`github.com/drmsGit/newsletter-reference-implementation`. Switching Claude
accounts does **not** require changing the GitHub remote; move the repo to a
business GitHub org only if you want to, as a separate step.

## Current state (as of 2026-09-04)

- Branch `main`, working tree clean. **1 unpushed commit:** `220edb5`
  (ADRs 160–164, proposed).
- ADRs: `docs/architecture/ADR/` — 75 records to 154 (sparse) + proposed 160–164.
- Interview source: `docs/architecture/interview-prep/Omni-Channel — design interview.md`
  (closed 25/25).
- Strategy/decision log: `docs/playbook-strategy.md`. Queue: `docs/backlog.md`.
  Business: `docs/business/` incl. `BETA-SCOPE.md` (now committed).

## Open threads to finish before 2026-09-26

1. **Omni-channel ADR follow-through** (from session "Omnichannel Interview › backlog"):
   - ADRs **160–164 are `Proposed`** → review and accept (or amend).
   - **8 dated addenda** owed to Accepted ADRs (append-only, never rewrite Decision):
     001, 021, 062, 063, 101, 103, 121, 122.
   - **3 decisions still open:** ADR-001's fate (edit vs. superseding boundary ADR);
     disabling an unlicensed channel; which address to pick when a recipient has
     several rows for one channel.
   - Push `220edb5` if you want it on origin.
2. **Backlog sequencer + timeline** (from "Cowork newsletter architecture brief"):
   the `backlog-sequencer` agent was built but never run — it was blocked on
   *interview closed + ADRs written + BETA-SCOPE.md*, all of which now exist.
   Run it, then the Cowork pass that turns the ranked graph into weeks/milestones.
3. **Code-slimmer fixes (optional, small)** (from "Code Review with code-slimmer"):
   `docs/architecture/code-slimmer-report.md` is written but two in-scope fixes
   were never promoted to the backlog or applied — the Settings weight editor
   (help text says changes apply immediately; they don't) and the `content_card`
   dropdown.

Everything else in the session list is finished (see the chat summary for the
full 27-session classification).
