---
id: TASK-48
title: Email-era names in an omni-channel platform.
status: Done
assignee:
  - '@claude'
created_date: '2026-09-27 13:56'
updated_date: '2026-10-05 20:32'
labels:
  - backend
  - frontend
dependencies: []
priority: p3
type: chore
ordinal: 200100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Chore] — P3 for the code, P2 for the four that reach the schema. Measured 2026-09-20.** **Email-era names in an omni-channel platform.** Twelve email-shaped names reach the OpenAPI schema; nine are FastAPI's auto-named `Body_*_ui_*` Jinja form bodies and vanish with that plane. **Four genuinely mislead a generated client** and are tabled in `docs/react-screen-inventory.md` so the frontend session is told rather than left to infer: `Variant.subject`/`.preheader` (the columns were dropped by migration 0012 — they are synthesised, and a push variant has no envelope), `GET /email-modules` (takes a `channel` parameter defaulting to email, serves all of them), `RenderedVariant.html` (snapshots already went `artifact_*`; this did not), and `Recipient.email`/`.email_consent_status` (flattened cells of a per-channel address set and consent grid). **Separately, 25 internal definitions across 13 files** carry email-shaped names — `render_variant_html` and friends. Those are honest about what they do, never reach the frontend, and are a readability pass rather than a risk. **Do the four with the client, not before it:** each is a schema change, and the reason the `artifact_*` rename went first was that nobody had written the table above. Now somebody has.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Verify each claim against today's code. 2. Decide with the user, one question at a time. 3. Tests first, both planes and the client. 4. Mutation-check, suites, contract, live read.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 144, section "Features", position 1 in that section (top = do next). The description is the original entry, verbatim.

Verified 2026-10-05: three of the four schema items were already gone — no Body_*_ui_* form bodies in the schema; GET /email-modules became /modules?channel= (task-21); RenderedVariant.html became artifact_body. Left: Variant.subject/.preheader, Recipient.email/.email_consent_status, and 11 internal email-named functions.
Decided with the user: Q1 — Variant's subject/preheader become one `envelope` map keyed by the channel's declared envelope fields. Q2 — the user's rule for this task: **rename only what also holds non-email values or does non-email work**; 'email' or 'newsletter' in a name is fine when the thing is email. So Recipient.email / email_consent_status / ConsentDriftItem.email stay (they hold email values), and every internal function stays: render_variant_html, send_test_email, get_snapshot_html, email_document, resolve_email(s) are email-only (render_variant_html refuses a push variant), get_template_html and module_html are named for the HTML they return.
Built: Variant.envelope (dict, {} for push), VariantCreate.envelope optional, VariantUpdate.envelope optional — sent: replaces the envelope (blank clears a field); left out: untouched, so a rename no longer clears the subject (it did before when subject/preheader were omitted). create_variant_for_campaign/update_variant take envelope; the Jinja forms (email's) pass their subject/preheader as the envelope; VARIANT_UPDATED's audit detail is {name, envelope} on both planes. Client: useSaveVariant sends envelope only when changing it, the whole map; the editor's Envelope area reads variant.envelope[field.name] for the fields the manifest declares, so no channel field names in the client.
Validation: 10 envelope tests (8 rewritten/new on the JSON plane, 1 Jinja plane, plus an editor test showing a channel's own envelope field 'sender_name'), failing first; 11 mutants all caught. Backend 1331, client 182, tsc, contract. Live, read-only: Variant 1A's envelope shows its subject and preheader; /campaigns/3/composition answers envelope {} for the push variant and no subject key on either.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A variant now answers with `envelope`, a map of the fields its channel declares (email: subject and preheader; push: empty), and takes the same map on create and update — instead of email's subject/preheader on every variant. Leaving the envelope out of an update no longer clears it. The React envelope area reads the manifest's field names, so no email names remain in the client. By the user's rule (rename only what also holds non-email values), recipient email fields and the email-only internal functions stay. Verified by 10 tests, 11 caught mutants, both suites, the contract check and a live read of an email and a push variant.
<!-- SECTION:FINAL_SUMMARY:END -->
