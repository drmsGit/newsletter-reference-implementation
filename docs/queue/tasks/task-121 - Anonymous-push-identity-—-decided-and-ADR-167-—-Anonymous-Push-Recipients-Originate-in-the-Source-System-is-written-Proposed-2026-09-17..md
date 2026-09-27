---
id: TASK-121
title: >-
  Anonymous push identity — decided, and ADR-167 — Anonymous Push Recipients
  Originate in the Source System is written (Proposed, 2026-09-17).
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
updated_date: '2026-09-27 14:33'
labels:
  - needs-adr
  - backend
dependencies: []
type: decision
ordinal: 300500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
📋 **Anonymous push identity — decided, and [[ADR-167 — Anonymous Push Recipients Originate in the Source System]] is written (Proposed, 2026-09-17).** Awaiting acceptance; the entry below is the working record the ADR was drafted from and stays until the ADR is Accepted, at which point this becomes an implementation item for the sync-path gap named in its Consequences. Raised by the user 2026-09-17, immediately after push became sendable: the largest push audience is people who are not logged in, so who are they in this platform?

  **Decided (user, 2026-09-17): the platform does NOT admit a recipient the CRM does not own.** An app install that wants push becomes a contact in the source system first — a device contact, an anonymous profile, whatever that system calls it — and reaches us through the ordinary sync with an `external_id` and a push address. **The device is therefore never anonymous to us.** When the person later signs in, the reconnect is the source system's work and we receive the updated record.

  **What that preserves, which is why it was chosen.** [[ADR-126 — Maintain Local Recipient Projection]] requires every recipient to carry an external identifier and forbids the projection from becoming "a system of record for customer data" — the code enforces it already (`recipients.external_id` is NOT NULL and UNIQUE, and the only production creation path is an upsert keyed on it). [[ADR-120 — CRM as Customer Source of Truth]] is untouched. And decisively, **[[ADR-165 — Core Scope Is Channel-Neutral Content Orchestration]] point 2 puts identity resolution systems outside the core** — the reconnect-on-login step is identity resolution, so it was never ours to do.

  **The accepted cost, stated rather than discovered:** a company with no CDP cannot do anonymous push without building that mint step somewhere. That is a real dependency and should be said out loud in the playbook.

  **Rejected, with the reason worth keeping.** *One shared "push anonymous" contact* (the Selligent shape) was rejected for a sharper reason than the user's own "we wouldn't have useful signals": `SignalContributionDB` aggregates per recipient, so every anonymous engagement would pile onto one row **and the decision engine reads that row**. It would not merely lose signal — it would feed the engine a corrupted affinity profile that grows with traffic. Adopting it would need an explicit rule excluding that contact from the signal layer. *One local recipient per device* was rejected because it makes the platform the system of record for a class of people ADR-126 forbids it to own, and drags in erasure-per-device (ADR-154 takes addressability rows with the identity) and merging, which ADR-165 says are not ours.

  **All three follow-up questions are closed (user, 2026-09-17). Recorded because the reasoning is the useful part:**

  1. ~~Sequential reassignment.~~ **Not a real case, and the mechanism says why.** The user: *"a phone number is irrelevant for us, for push, for apps"*, and a token is per-app-install — so a wiped device that is reinstalled mints a **new** token and the old one simply goes dead, which APNs reports and [[ADR-163 — Per-Channel Consent and Addressability]] point 2's mark-invalid path already handles. There is no path by which our system matches an abandoned token to a new owner. The one surviving case is a device handed over with the app still installed and signed in — accepted: *"we live with it; it's unlikely anyway"*, and it is not a push problem but the general one of somebody else holding your unlocked device, which no messaging system solves. **ADR-163 needs no addendum for this.**
  2. and 3. **Dissolved by the decision above rather than answered.** A device contact is simply a recipient whose only address is on the push channel — there is nothing extra for the source system to send and nothing for the platform to distinguish. Which turns them into one concrete implementation gap, below.

  **THE GAP, found 2026-09-17 by reading the code against the decision: the recipient sync path is email-shaped and cannot accept a device contact.** `create_recipient` (`app/recipients/service.py:169`) takes **`email` as a required positional**; it calls `record_consent` with no channel, so a synced contact is granted **email** consent whatever it actually agreed to; and it writes an email address row via `_upsert_email_address` and nothing else. A device contact — external id, a push token, no inbox — cannot be created through the only production path, and if it were, it would arrive holding a consent it never gave. Closing this means the sync path taking a channel and an address of that channel's shape, which is the same generalisation `resolve_send_addresses` and the exclusion stack already went through in step 5.

  **Do not build it before the ADR is written** — the decision above is an architecture decision and belongs in the repo first. Source: user, 2026-09-17.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 418, section "Needs ADR", position 5 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
