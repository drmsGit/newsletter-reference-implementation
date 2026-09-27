---
id: TASK-70
title: >-
  Complete the inbound provider adapter layer (`providers/adapters/`, currently
  an empty mock file)
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: feature
ordinal: 202300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature]** **Required before public launch** (confirmed via `/business-review`, `docs/business-interview-baseline.md` §H1) — a real provider integration proves the "no vendor lock-in" pitch is real, not just a design promise; deliberately sequenced late (after remaining frontend work) since it costs real money. Also depends on this adapter layer existing first. Complete the inbound provider adapter layer (`providers/adapters/`, currently an empty mock file) — build the actual translation contract (e.g. an abstract base analogous to `DeliveryProvider` for outbound sends) that turns a raw provider webhook payload into the canonical `ProviderEventCreate` shape, since `ingest_provider_event` today just accepts an already-normalized payload directly with no real adapter behind it. Fits the "architecture + one worked example" strategy (per the provider-plugin-strategy decision in project memory) — this is the generic interface/contract any future custom connector would implement, not a vendor-specific plugin, so it doesn't conflict with the earlier decision to not ship maintained ESP/CRM plugins. **Must also own event-type normalization**: `event_type` is currently unconstrained free text with only a hardcoded `"click"` check giving it any meaning downstream (`insight/service.py`'s `EVENT_PREFERENCE_DELTAS`) — bounce/complaint (mandatory per ADR-106) are accepted into storage but never actually handled. Validation/normalization must be centralized in the adapter layer, not a single hardcoded enum, since the raw event-type vocabulary differs per provider (e.g. one ESP's `"hard_bounce"` and another's `"permanent_failure"` both need to normalize to the same canonical internal type). **Concrete reaction to bounce/complaint, now that the consent gate is resolved (see the consent-gate Feature above, from `docs/business-interview-baseline.md` §F1):** a bounce/complaint event should (1) update the recipient's `consent_status` (revoke/mark opted-out) and relay back to the CRM if there's no direct CRM↔provider webhook connection, since this platform is the only place positioned to notice; and (2) separately feed the Insight layer as a content-quality signal ("this content triggered a lot of complaints") — a distinct, analytics-flavored reaction to the same event, not the same action as the consent update. **Design approach, when this work starts:** favor (b) "fairly simple to adjust to your provider" over (a) "one contract that auto-fits every ESP generically" — real webhook payloads have enough genuine quirks (auth/signature schemes, batch-vs-single-event delivery, inconsistent field naming) that a fully generic auto-detecting layer would be over-engineering and fragile. Same pattern as the outbound side: a small, clean canonical contract (a `ProviderAdapter` interface mirroring `DeliveryProvider`) plus one well-documented worked example. Before finalizing the canonical event shape, pull real webhook API docs from a small, deliberately varied set of providers (not guess from memory, which may be stale) — suggested: one already referenced in the ADRs (Brevo or Resend), one classic/well-documented one (Mailgun or Postmark), and SES given it's common infrastructure for the target buyer. Enough variety to find genuine common ground without over-researching providers that'll never be used. Source: [[Interview Prep - Delivery, Providers, Recipients]] → Providers Q1, Q4; `docs/business-interview-baseline.md` §F2, §H1 (via `/business-review`).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 216, section "Features", position 23 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
