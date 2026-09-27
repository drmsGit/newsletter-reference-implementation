---
id: TASK-134
title: >-
  Transactional sends — consent model, sending reputation, and whether they
  reuse the email modules.
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
updated_date: '2026-09-27 14:29'
labels:
  - needs-adr
  - backend
dependencies: []
type: decision
ordinal: 301800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
📋 **Transactional sends — consent model, sending reputation, and whether they reuse the email modules.** Surfaced 2026-07-31 (user). The architecture today only does *marketing* communication: every send passes the consent floor (`CONSENTING_STATUS = "opted_in"`), and content comes from the governed catalogue. Transactional mail (order confirmations, password resets, booking details, masterclass signups) breaks all three assumptions at once, and **this may be a dealbreaker rather than a nice-to-have** — "why adopt a new system if it only handles marketing?" Three linked questions, none decided:

  **(a) Consent.** Transactional mail goes to people *without* marketing opt-in, by design. Does the model need **two distinct permissions** (marketing consent vs. a transactional/legitimate-interest basis) rather than the single `consent_status` gate in [[ADR-122 — Minimal Consent Model Required]]? Note the hazard already recorded in `docs/playbook-strategy.md` (Decision Log 2026-07-11, item 4): **some providers, e.g. Selligent, ignore opt-outs entirely on API-triggered sends because they classify them as transactional** — so "the provider will sort it out" is exactly the assumption this architecture exists to avoid. Also to settle: hard bounce / spam-complaint suppression almost certainly must still apply to transactional (a dead address is dead either way), while a *marketing* opt-out must not block a password reset — meaning the suppression gate and the consent gate are not the same gate. Interacts with the suppression/opt-out data-model item below.

  **(b) Sending reputation — and it is a THREE-way split, not two.** *Corrected 2026-08-02 (user), after sign-in codes made the third category concrete.* Marketing and transactional should not share reputation: complaint rates on marketing degrade delivery of mail people actually need. But **system-internal** mail — to the company's own operators, not to customers — is a third category again, and must not ride on transactional either. Its failure mode is unique and circular: if transactional delivery degrades a customer misses a receipt, but if system delivery degrades **nobody can sign in, including the person who would fix whatever caused it**. Transactional volume and complaint exposure are still customer-driven and outside the company's control, so sharing with it reintroduces the risk. So: **marketing customer / transactional customer / system internal**, three senders. Options per stream: a **separate provider**, or at minimum a **separate verified domain or subdomain**. The provider layer is already an adapter ([[ADR-100 — Provider Layer as Send and Feedback Adapter]]) and from-address is selectable per send, so the seam exists; what is undecided is whether "which stream a send belongs to" becomes a first-class concept rather than a manual from-address choice. See the system-mail channel Feature for the third stream, which now has running code.

  **(c) Do transactional emails reuse the existing modules, or get their own?** The real fork, because it decides how variables work:
  - **Reuse the marketing modules** — **PRO:** far less work, one module library, one rendering path. **CON:** needs a **global variable solution that is not limited to catalogue fields** — a transactional payload arrives as arbitrary JSON from an external system (order number, seat row, reset link), so rendering must interpret JSON directly rather than resolve content records. That is a genuine extension of the merge-context concept in [[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]], not a small addition.
  - **Dedicated transactional modules** — **PRO:** variables become straightforward, since a module is written against a known payload shape. **CON:** you need **a module per email type** (each has different fields), and you **cannot combine JSON payload + catalogue content** in one email — which matters if you want the decision engine to add recommendations for a recipient who *does* have marketing opt-in.

  **Open sub-question:** should a transactional email to an **opted-in** recipient be allowed to carry decision-engine recommendations? Tempting (high open rates), but it mixes streams and risks the reputation separation in (b). Plausible answer is **"we deliberately don't do this"** — while noting an adopting company may want it anyway, so the honest question is whether they can **integrate it themselves at a documented seam** rather than whether we ship it.

  **Timing:** potentially a stage-2 feature, but flagged as a possible dealbreaker for adoption, so the ADR should at least establish the *direction* (especially the consent model in (a), which is hard to retrofit) even if the build waits. Ties to: [[ADR-122 — Minimal Consent Model Required]], [[ADR-004 — Privacy Operations as a First-Class Architectural Concern]], [[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]], [[ADR-100 — Provider Layer as Send and Feedback Adapter]], [[ADR-131 — Email Module Templates Use MJML as Source Format]], and the suppression item below. Source: user, 2026-07-31.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 473, section "Needs ADR", position 18 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
