---
id: TASK-123
title: >-
  System email: transport, templating, triggering — and which provider may be
  selected where.
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - needs-adr
  - backend
dependencies: []
ordinal: 300700
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
📋 **System email: transport, templating, triggering — and which provider may be selected where.** Surfaced 2026-08-02 (user), during the security-base build. Sign-in codes made system mail real, and four questions came with it that the architecture has no answer for. **(1) Should a separate transport be *forced*?** The user asked whether companies must use SMTP for system mail, may freely point it at the marketing sender, or are forced with code as the escape hatch. **Suggested fourth option: allow it, default safely, warn loudly** — `SYSTEM_MAIL_PROVIDER`/`SYSTEM_MAIL_FROM` already exist, the default is mock, and startup warns when system mail falls back to the marketing sender. Same idiom as ADR-152's write-only credentials and ADR-144's PII default: safe by construction, deliberate opt-out, never silent. Forcing contradicts the "adapt it to your setup" posture, and some deployments genuinely cannot use SMTP (cloud providers commonly block outbound port 25). **(2) Do self-hosting companies have an SMTP option?** Yes, and the worry dissolves once you notice **SMTP is a transport, not a hosting model**: a self-hosted Postfix/Exim, a Microsoft 365 or Google Workspace relay (the most likely real answer for a Mittelstand company, which already has one), or a transactional service's SMTP endpoint all speak it. One adapter serves self-hosted, cloud and SaaS-relay identically — which is exactly what makes it a good universal fallback. Caveat to document: ports 587/465 rather than 25, and SPF/DKIM/DMARC on the system subdomain. **(3) Should an SMTP/Strato provider appear in the campaign "send from" menu?** Resolved in principle — **the API-vs-SMTP framing and the gating rule are now recorded in [[ADR-101 — Provider Capabilities Are Explicit]] (addendum, 2026-08-02)**. Short version: capabilities describe the configured *provider instance*, not the protocol, because an ESP's SMTP relay still fires webhooks while generic host SMTP does not; combined with [[ADR-106 — Bounce and Complaint Feedback Is Mandatory]], a provider that cannot report bounces may not be selected for a marketing send. **What remains is the build:** capabilities are documented per adapter but not declared in a form the send path can read, and the provider selector still offers every registered name. That enforcement point is the actual work here. **(4) How are system emails built, and who triggers them?** Not from the content catalogue: [[ADR-012 — Content Records Represent Communication Units]] describes editorial content, and a login code is not one. Suggested: **dev-owned Jinja templates in the repo**, with a small set of substitutable values (product name, sender, locale) rather than a WYSIWYG — the inverse of ADR-140 §4's reasoning, since a manager should not be able to edit the email that lets people in. On triggering, [[ADR-142 — Autonomous Workflows and the Automation Boundary]] already gives the spine: **the platform owns the action, the orchestrator owns the flow** — so "send an approval notification" is a platform action and n8n decides *when*, rather than n8n composing and sending the mail itself. Otherwise every orchestrator reimplements the templates and sender config, and [[ADR-153 — Audit and Accountability]] loses the record. **Note how much of this is already implied** by ADR-101/106/012/142 — the ADR may be mostly a matter of stating the derivations and deciding (1). Source: user, 2026-08-02 (security base build).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 445, section "Needs ADR", position 7 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
