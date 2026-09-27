---
id: TASK-128
title: >-
  Recipient/consent sync to the sending provider (Resend Contacts/Audiences) —
  evaluate whether it's needed at all before designing.
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
updated_date: '2026-09-27 14:29'
labels:
  - needs-adr
  - backend
dependencies: []
type: decision
ordinal: 301200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
📋 **Recipient/consent sync to the sending provider (Resend Contacts/Audiences) — evaluate whether it's needed at all before designing.** Surfaced 2026-07-26 (user, post-Resend-outbound). **Premise correction first:** the outbound adapter posts to Resend's *transactional* `/emails` endpoint, which needs **no** pre-synced audience list — so "we must sync users to Resend before we can send" is **not** true for the current send path. Provider-side contact sync only becomes necessary if we decide the *provider* should own something the architecture currently owns internally: managed unsubscribe/suppression lists, provider-hosted unsubscribe links, or Resend *Broadcasts*. Since the architecture already holds `consent_status` on `RecipientDB` (consent gate, done 2026-07-15) and follows a **data-minimization** principle (per `docs/playbook-strategy.md`), the default should be to keep consent authoritative *inside* the architecture and sync the **minimum** (email + permission) outward only if a provider feature forces it — not to mirror full contact records into the ESP. Two sub-questions to settle if/when this is actually needed: **(1) Sync timing** — push email+permission to the provider eagerly on recipient create, lazily just-before-send, or via an async job? (leaning: not before it's proven necessary; if needed, lazy/pre-send keeps the provider's copy minimal and current, and avoids syncing people who never get emailed — consistent with the consent-gate's "don't spend on recipients who won't receive" reasoning). **(2) CRM spike** — stand up a small free CRM (HubSpot free tier; German/EU alternatives to evaluate for the GDPR-bound persona: weclapp, CentralStationCRM, or Zoho-EU) and test both CRM→Resend and CRM→architecture connections. **Evaluation: keep as Needs-ADR, do NOT implement in POC yet.** Reasons: (i) not required by the current transactional send path, so it's not blocking the "real send" demo; (ii) building provider-side contact sync or a CRM connector conflicts with the established "architecture + one worked example, don't ship maintained ESP/CRM plugins" strategy until a real adopter need forces it (same reasoning as the inbound-adapter Feature); (iii) the consent source-of-truth question (CRM vs architecture vs provider) is exactly the kind of decision that should be recorded as an ADR before code, per `docs/CLAUDE.md` review rule 3. If we do a CRM spike, scope it as **throwaway research** (does the connection work, what's the minimal field set) not a maintained integration, and prefer sub-question-1's minimal email+permission sync over mirroring full contact profiles. Source: user, 2026-07-26.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 457, section "Needs ADR", position 12 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
