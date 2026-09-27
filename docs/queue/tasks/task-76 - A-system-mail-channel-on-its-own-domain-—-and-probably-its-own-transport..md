---
id: TASK-76
title: A system-mail channel on its own domain — and probably its own transport.
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: feature
ordinal: 202900
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature]** **A system-mail channel on its own domain — and probably its own transport.** Surfaced 2026-08-02 (user), during the security-base build. **Sign-in codes are the first system email, and they will not be the last:** approval notifications, AI-suggestion alerts and any other operator-facing message belong on the same channel. This is a **third** outbound category the architecture had not named — marketing customer / transactional customer / **system internal** — and it is not a flavour of transactional, because it is not customer-facing at all: no consent question, no unsubscribe semantics, almost no volume. See sub-point (b) of the transactional Needs-ADR item for the reputation reasoning. **Already in code:** `SYSTEM_MAIL_PROVIDER` (defaults to `mock`) and `SYSTEM_MAIL_FROM` in `app/auth/service.py`, with a startup warning when the sender falls back to the marketing one. Those helpers live in the auth module only because auth is currently the sole caller — **move them to a shared helper as soon as a second consumer appears**, or the second one will quietly reimplement them. **Still to do: (1)** verify a separate domain or subdomain for system mail and set `SYSTEM_MAIL_FROM`; **(2)** decide whether system mail should use a **different transport entirely**, not merely a different domain. The user's suggestion — the hosting provider's own SMTP, e.g. Strato — is a good fit and worth evaluating: it makes the channel genuinely independent of the ESP, so an ESP outage, suspension or quota cannot lock operators out of the platform, which a separate domain on the *same* provider does not achieve. Volume fits (a handful a day against shared-hosting limits of a few hundred), it is already paid for in the hosting package, and reputation is separate by construction. **Costs to weigh:** SMTP is a different transport from the HTTP adapters, so it needs a `DeliveryProvider` implementation (small — `smtplib` is stdlib); there is **no feedback loop** (no webhooks, no bounce events), which is fine for system mail but means a silently failing address goes unnoticed; and shared-hosting IP deliverability is variable enough to test rather than assume. Credentials follow [[ADR-152 — Secret and Credential Handling]] — environment, never the database. **Bonus worth noting for the playbook:** an SMTP adapter would be a *third* worked example of the provider contract, and arguably a stronger no-vendor-lock-in demonstration than a second SaaS ESP, because SMTP is the universal fallback every company already has and proves the contract is not API-shaped. Source: user, 2026-08-02 (security base build).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 228, section "Features", position 29 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
