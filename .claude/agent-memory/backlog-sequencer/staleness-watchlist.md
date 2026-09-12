---
name: staleness-watchlist
description: Contradictions and stale claims found 2026-09-12. Code-verified ones are marked; the rest need a human check.
metadata:
  type: project
---

## Code-verified

1. **Category picker is built; the backlog still lists it 🔴.**
   `app/templates/decision_slot_detail.html:123` is a name-based multi-select over
   categories, and :131 says "no need to type IDs" — exactly the Feature's ask.
   `playbook-strategy.md` §6 already marks 2D ✅ done. The stale 🔴 entry propagated
   into BETA-SCOPE.md's out-of-scope list. Human call: close the Feature entry.

2. **Two Done claims are reversed by ADRs accepted 2026-09-12.**
   - Done: "Minimal consent gate: add a `consent_status` field to `RecipientDB`" —
     ADR-163 §1 removes that column.
   - Done: "Add `subject`/`preheader` fields to `CampaignDB`/`VariantDB`" —
     ADR-162 §1 moves both into module fields.
   Neither is a defect. Both are Done-and-superseded, and the archive does not say so.
   (The signal-weight editor no-op remains the third, already-flagged Done correction.)

3. **Beta definition-of-done #4 cannot pass today.** It requires a clean-container
   `pip install -r requirements.txt && pytest`. `requirements.txt` line 8 is `httpx2`,
   and `app/database.py` builds a PostgreSQL engine at import (line 6), so four test
   modules cannot even be collected in a fresh runtime. Both are one-line fixes in
   files BETA-SCOPE already pulls in-scope for other reasons.

## Needs a human check

4. **POSITIONING.md is stale in a load-bearing way.** It says "The omni-channel
   interview that would settle it is deferred." It closed 2026-09-12, and ADR-165 makes
   channel-neutral orchestration the formal core scope. Its rule 2 — "no claim that
   cannot be demonstrated in the repo today" — is now the live question: does *designed
   and accepted, not built* clear it? Gate 1 gates 4C gates beta, so this is the
   highest-leverage stale line in the docs. BETA-SCOPE §3's advice ("should not be
   adopted as the headline claim while omni-channel is undesigned") was written against
   a condition that no longer holds.

5. **BETA-SCOPE.md §2/§3 describe the interview as underway** ("cluster 2 nearing
   completion, two questions left"). Closed 25/25. §3's open question — "worth deciding
   whether to sequence the Gate-2 fix after the interview lands instead of fixing the
   consent gate twice" — is now answerable rather than open.

6. **LAUNCH-GATES.md Gate 2 still calls the omni-channel interview "deferred"**
   and offers running it first as an argument. That argument is spent; the shape is in
   ADR-163 §7/§8.

7. **The 11-broken-wikilink count is disputed.** `.claude/agent-memory/adr-drift/`
   records a full 2026-08-21 sweep of 75 records finding exactly one broken link, fixed
   the same day, 0 outstanding. The backlog still cites 11. Six ADRs (160-165) have been
   added since, so the audit is also stale in scope (75 -> 81). Re-run adr-drift before
   scheduling that session; do not assert either number.

8. **Roadmap §6 "Status at a glance" is dated 2026-08-02** and predates the security
   review, the code-slimmer sweep and the omni-channel ADRs. Treat its ✅ marks as
   asserted, not verified.

## Caveat carried on every line number here
Line numbers come from backlog text and code-slimmer reports written between 2026-08-07
and 2026-08-21. Drift is likely; verify before editing. Numbers checked live on
2026-09-12: `frontend/router.py` 2927 loc, `delivery/service.py` 433 loc,
`decision_slot_detail.html:123`, `app/database.py:4,6`.
