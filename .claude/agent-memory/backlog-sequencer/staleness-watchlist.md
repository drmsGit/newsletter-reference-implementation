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

---

# Run 2 — 2026-09-27

## Resolved since run 1
1. Category picker — no longer listed 🔴.
3. Beta DoD #4 — LAUNCH-GATES gate 2 now carries a *historical note* correcting
   the `app/database.py` claim: "It does not — the suite collects and passes."
   **My run-1 watchlist item 3 was wrong and the repo corrected it.** Keep this.
7. 11 broken wikilinks — ✅ Done 2026-09-24.
4/5/6. POSITIONING/BETA-SCOPE/LAUNCH-GATES omni-channel staleness — all updated.

## Code-verified, run 2
1. **`docs/playbook-strategy.md` §5 has no Variant Editor entry.** Verified:
   `grep -c "Variant Editor" docs/playbook-strategy.md` = 0. The log ends at
   2026-09-24 (Manager Workflow). An interview that closed 2026-09-27 and
   produced 28 gaps and four owed ADRs is not in the live business record.
2. **§6 "Status at a glance" is dated 2026-09-12** — predates both interviews,
   19 screens, and the invalidation of four built client screens.
3. **The pagination Feature (L242) does not record its own repricing.** MW
   Cluster 2 Q10 moved it "from a latent scaling note to a blocker" and made it
   invalidate four built screens. L242 still reads as a mid-priority nice-to-have
   sourced from a July interview.
4. **L150 is unblocked and its text says it is blocked.** ADR-169 (L427,
   accepted 2026-09-19) names the unsubscribe surface as buildable on
   acceptance; L150 still says to wait for the flow question.
5. **`frontend/router.py` grew 1,488 lines while under a deletion date**
   (2,927 on 2026-09-12 -> 4,415 on 2026-09-27). L138 says to "freeze the Jinja
   UI for new features the same day" the sweep completes. The sweep completed
   2026-09-19.
6. **LAUNCH-GATES has no gate for the unsubscribe surface**, though L150 says
   RFC 8058 one-click unsubscribe is a hard requirement for bulk senders at
   Gmail and Yahoo and that it "blocks the beta's first send". L150 itself
   says it "probably deserves to be a launch gate of its own... not added
   there without the user's call." **Still not added. This is the strongest
   candidate for a missing gate in the file.**
7. **Interview question-count discrepancy.** The run-2 brief said Manager
   Workflow closed 53/53. The interview's own Cluster 1 summary says question 5
   is "◐ partial at the user's request", and backlog L90 says "52 of 53
   answered; only Cluster 1 question 5 stays open, reopened at the user's
   request." Two sources agree against the brief.
8. **BETA-SCOPE §1-4 and the repo disagree about whether the React client
   exists.** §1 chose Definition A and lists the React frontend under "Out of
   scope for beta"; §5 is explicitly optional and "§1-4 above remain the
   decision unless this gets adopted". ADR-168, 170, 171, 173 are accepted,
   `frontend/` is built, two phases shipped and a third is paused. **§5 has
   been adopted in practice and never in writing.** This is the single largest
   scope contradiction in the docs and it is what makes "is X a launch concern"
   unanswerable item by item.
9. **`ContentOverrideDB`'s docstring is now contradicted by decision 2.6**
   (it names "a consistent headline across the personalized picks" as the
   intended use; 2.6 forbids exactly that), and
   **`campaigns/duplication.py`'s docstring is contradicted by 3.6**
   (it groups content overrides with "a record of something that happened").
   Both are built code the interview reversed. Neither file has been touched.
10. **ADR-161 point 7's rider is false** and has a dated addendum saying so
    (2026-09-24). Good — recorded, not stale. Noted so it is not re-flagged.

## Line-number drift measured 2026-09-27
- `delivery/service.py` test-send: backlog says :519, actual **:520**.
- `campaigns/duplication.py` override docstring: backlog says :147, actual **:143-152**.
- `frontend/router.py`: backlog says 4,419 loc, actual **4,415**.
- Verified exact: `content/service.py:101` (`CONTENT_FIELD_GROUPS`),
  `content/service.py:85` (`CONTENT_STATUSES`), `campaigns/db_models.py:115`
  (`max_results`), `campaigns/db_models.py:135` (`content_record_id` nullable=False),
  `campaigns/db_models.py:64,83` (`updated_at` on both tables).
- Verified absent: any `UploadFile` in `backend/app/`; `app/settings/router.py`;
  `app/ai/router.py`; `storage/fields.json`.

---

# Run 3 — 2026-10-08 (code-verified unless marked)

## Resolved since run 2
Run-2 items 3 (pagination repricing), 5 (router.py growth: now 3,982 and frozen),
9 (override/duplication docstrings: task-113, ADR-178 p5) — done.
Gate 4b CLOSED 2026-09-29 (timing oracle, task-5).

## Still open from run 2
- **task-56 text still says wait for the flow question**; ADR-169 point 1 says
  unsubscribe and DOI are routes. Third run flagging it.
- **LAUNCH-GATES still has no unsubscribe gate** (run-2 item 6).
- **BETA-SCOPE §2 still lists the React frontend as "not started"** (`:59`);
  §5 adopted in practice, never in writing (run-2 item 8).
- **Playbook §6 "Status at a glance" still dated 2026-09-12.**

## New, run 3
- task-67: provider choice + cap exist (`campaign_detail.html` provider select,
  `delivery/models.py` `SendPlanRequest.provider`, `settings/router.py:151` send
  cap). Remainder: no React plan-send screen.
- task-70: "currently an empty mock file" false — `providers/adapters/resend.py`
  is the worked inbound adapter with an event map; bounce/complaint opt-out built.
  Remainder: CRM relay (task-135/128), complaint-as-content-signal.
- task-65: its blocker `VariantDB.channel` exists (`campaigns/db_models.py:46`).
- task-207: "C2 has no router at all" false.
- task-124: (a) and (b) answered by ADR-180 and built; (c) + spend-cap TOCTOU
  (`ai/service.py:89`) remain.
- task-104: point 1 answered (address dedup = exclusion stage 1,
  `delivery/exclusion.py:150-165`); its description also carries a glued-on
  Done entry (AI task registry, done 2026-09-18) — migration artifact.
- task-237: ADR-190 addendum 2026-10-08 settles template escaping, `random`, shell
  use; raw SQL (S608) explicitly left to review = task-237's remaining core.
- task-90: "Phase 3B isn't built yet" false (playbook §6: 3B done).
- task-71: realistic content exists as `scripts/seed_content_chatgpt.csv` +
  importer; `seed_demo_data.py:146` still writes placeholders.
- task-162 (Done 2026-07-12) left "dedup before sending" open; now built (stage 1).
- **ADR-188 has no 2026-10-08 addendum** (only 2026-10-06), contrary to a brief.
- **CODE-REVIEW-BRIEF.md is stale** (2026-09-19 content: "Jinja UI", known-issue
  list of items since fixed, test count, `docs/backlog.md` pointer). Not a task.
- task-105 deferred mypy (gradual) and Vulture (once by hand); no task holds them.
- Queue mode letters (Mode A/B/C) are NOT stale: ADR-140 addendum p2 keeps dated
  records, including the queue, as written.
