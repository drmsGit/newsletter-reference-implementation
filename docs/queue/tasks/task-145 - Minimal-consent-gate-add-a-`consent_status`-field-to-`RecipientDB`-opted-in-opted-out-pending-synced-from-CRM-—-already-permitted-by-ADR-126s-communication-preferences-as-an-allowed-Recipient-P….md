---
id: TASK-145
title: >-
  Minimal consent gate: add a `consent_status` field to `RecipientDB`
  (opted-in/opted-out/pending, synced from CRM — already permitted by ADR-126's
  "communication preferences" as an allowed Recipient P…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
  - frontend
dependencies: []
type: feature
ordinal: 500900
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Feature]** Minimal consent gate: add a `consent_status` field to `RecipientDB` (opted-in/opted-out/pending, synced from CRM — already permitted by ADR-126's "communication preferences" as an allowed Recipient Projection field), plus a consent-sync log to detect CRM↔platform drift. Filter non-consenting recipients at **audience-resolution time**, before decision/rendering run at all, not as a late gate before the provider call — driven by both a legal reason (GDPR processing scope, needs real legal review) and a cost reason (avoid paying for AI/token-driven decisioning on recipients who'll never receive anything). Closes a real gap providers can't be trusted to close themselves (some, e.g. Selligent, ignore opt-outs on API-triggered sends). Ranked high — resolves the previously-deferred, highest-priority item from the technical review's Recipients Q1. Source: `docs/business-interview-baseline.md` §F1 (via `/business-review`). **Done 2026-07-15** — `RecipientDB.consent_status` column (`opted_in`/`opted_out`/`pending`, `ConsentStatus` enum, default `pending`); only `opted_in` clears the gate. New `ConsentSyncLogDB` append-only table records every CRM→platform sync (asserted value, platform-value-before, applied flag) so drift is auditable. New endpoints: `POST /recipients/{external_id}/consent` (apply+log a CRM assertion), `GET /recipients/consent/drift` (recipients whose live status diverges from the CRM's last assertion — the "CRM says no, platform still says yes" case), `GET /recipients/consent/sync-log`. **The gate itself lives at audience-resolution time**: `audience.find_by_criteria` now filters to `consent_status='opted_in'` before any decisioning/rendering, and `execute_decision_slot` refuses (400) to run per-recipient decisioning for a non-consenting recipient (belt-and-suspenders behind the audience filter, honoring the cost reason). Consent badge surfaced on the recipients list + detail UI. Seed recipients set to `opted_in` so the end-to-end demo still works. Verified live: opted-out recipient excluded from a criteria preview (3→2), decisioning refused for the opted-out recipient but succeeded for opted-in ones, a simulated failed-sync flagged by the drift endpoint, sync log correct, UI badges render. Note: the late send-path (`send_send_instance`) is deliberately **not** gated — per the design, filtering happens at audience resolution, not as a pre-provider-call gate; a full bulk send-from-audience-group flow (which would resolve its audience through the now-gated path) still doesn't exist. **Bonus fix in passing:** `backend/scripts/reset_all_data.sql` still referenced `categories.parent_category_id` (dropped last session in Content Q5), so the documented reset/reseed script had been un-runnable since — corrected the `categories` INSERT; the script now restores a clean baseline again (which is how the live DB was returned to documented baseline after verification). **⚠️ REVERSED BY DESIGN 2026-09-12 — done, then superseded, not a defect.** [[ADR-163 — Per-Channel Consent and Addressability]] §1 **replaces `RecipientDB.consent_status` entirely** with append-only consent events, latest-wins per `(recipient, channel, purpose)` — a single column cannot carry the source and timestamp that make consent provable, cannot survive an erasure in the minimised form [[ADR-154 — Erasure and Retention]] requires, and cannot express five channels × three purposes without a migration per combination. `ConsentSyncLogDB` **survives** as a separate table (ADR-163 §4: consent events record what the *person* permitted; the sync log records what happened in a *conversation with the CRM* — a failed sync is not a consent change). The verified footprint of the column removal is ten files: `app/recipients/{models,service,db_models,router}.py`, `app/decision/service.py`, `app/audience/service.py`, `app/templates/{recipients,recipient_detail}.html`, `scripts/seed_demo_data.py`, `scripts/reset_all_data.sql`. Note this is the most safety-critical path in the system and its regression test cannot currently run — see the `app/database.py` engine-at-import defect.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 519, section "Done", position 9 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
