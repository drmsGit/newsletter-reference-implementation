---
id: TASK-56
title: >-
  Subscribe (double opt-in) and unsubscribe do not exist as surfaces, and
  `List-Unsubscribe` is never sent.
status: Done
assignee:
  - '@claude'
created_date: '2026-09-27 13:56'
updated_date: '2026-10-09 11:43'
labels:
  - backend
dependencies: []
type: feature
ordinal: 200900
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature] — the most concrete piece of the missing flow layer, and it blocks the beta's first send. Raised by the user 2026-09-18.** **Subscribe (double opt-in) and unsubscribe do not exist as surfaces, and `List-Unsubscribe` is never sent.** Verified 2026-09-18: `unsubscribe` exists only as a *string* — an engagement event type (`app/recipients/db_models.py:182`) and a consent source. There is no public unsubscribe route, no landing page, no DOI confirmation flow, and the Resend adapter's payload is `from / to / subject / html` with no `List-Unsubscribe` or `List-Unsubscribe-Post` header (`app/delivery/providers/resend.py:40-64`). One-click unsubscribe (RFC 8058) is a **hard requirement for bulk senders at Gmail and Yahoo**, so this is not a lifecycle nicety — it is a deliverability failure with a delay on it, the same shape [[ADR-106 — Bounce and Complaint Feedback Is Mandatory]] warns about. Scope per the user: **global opt-out plus per-channel**, email-only in practice. **Do not build it as a one-off script** — it is the first consumer of the flow/journey question in Needs ADR, and the shape of that answer decides where it lives. Probably deserves to be a launch gate of its own in `docs/business/LAUNCH-GATES.md`; **not added there without the user's call.**
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 160, section "Features", position 9 in that section (top = do next). The description is the original entry, verbatim.

2026-10-08 queue cleanup (backlog-sequencer run 3, verified by hand): not blocked any more. This entry says not to build unsubscribe as a one-off because it is the first consumer of the flow/journey question. ADR-169 has since answered that question, and its point 1 says unsubscribe and double opt-in are routes, not flows, and need no mechanism at all. So this can be built as routes now. Still true: there is no unsubscribe route, no double opt-in and no List-Unsubscribe header (backend/app/delivery/providers has none). task-301, the visible footer, needs the route for its link. The recipients/db_models.py line cited here has drifted.

2026-10-09: interviewed, recorded and built (commit 2e5f08a; CI green; records fd97368).

Interview, seven questions answered by the user one at a time, recorded in ADR-191 (Unsubscribe Is a Per-Message Token, a Confirm Page and One-Click):
1. Unsubscribe first; double opt-in split off as task-324.
2. A random token per sent message, stored with it; no secret.
3. Opening the link shows a page; only a POST opts out (the button, or a mail client's one-click).
4. The default scope is marketing on the message's channel from the sending brand. "Everything" (all brands, all channels, marketing only) is offered only while a company setting is on, and it starts off.
5. A plain footer line now, until task-301's designed footer.
6. A new launch gate 10, added and closed today.
7. English now, all recipient-facing text in one module.
The 2026-09-18 note "do not build it as a one-off" was answered by ADR-169 point 1: a route, not a flow.

Built:
- Migration 0041 adds delivery_executions.unsubscribe_token (unique, indexed).
- New package backend/app/subscriptions/:
  - texts.py holds the footer line and the pages, escaped;
  - service.py holds footer_for (mints the token at send time, for email and marketing only), unsubscribe (idempotent; the default scope, or everything only while offered) and PUBLIC_BASE_URL;
  - router.py serves GET (a page) and POST (button or one-click) /unsubscribe/{token}. It is public and kept out of the API schema.
- policy.py has a new sentinel, RECIPIENT_TOKEN, with an exact test, and an explained exemption in the CSRF guard test.
- The send loop records the footer inputs in the delivery record, and reconstruction reuses them.
- email_document renders byte for byte as before when there is no footer.
- The Resend adapter adds the List-Unsubscribe and List-Unsubscribe-Post headers from the envelope.
- The company setting is GET/PUT /settings/unsubscribe, audited.
- frontend/vite.config.ts proxies /unsubscribe.
- backend/.env.example documents PUBLIC_BASE_URL.

Tests: backend/tests/test_unsubscribe.py has 12 tests:
- the token, footer and record on a sent email;
- the rebuilt message's hash matches;
- the Resend headers;
- the page changes nothing;
- the button scopes to the sending brand only;
- one-click opts out;
- a repeated click writes nothing;
- an unknown token returns 404 and learns nothing;
- "everything" is not offered by default;
- when offered, "everything" covers every brand and channel but not transactional;
- one-click never means "everything";
- the next send excludes the person.
Mutation check: 10 of 10 caught. Full suite: 1577 passed; tsc and ESLint clean.

Live check, on scratch data: "SCRATCH task-56 unsubscribe" campaign and recipient 41 (SCRATCH-task56-…), sent with the mock provider; the send returned "sent". Opening the real link showed the page for "Default" with one button, and consent stayed opted_in. Clicking the button showed the confirmation, and the latest consent event is opted_out with source "unsubscribe".

Not done, by decision: double opt-in (task-324); the designed footer (task-301); translation; a React toggle for the company setting (the API exists). Whether an unsubscribe also writes a negative interest signal (ADR-132) is not decided.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Every marketing email can now be unsubscribed from. It carries a per-message token, a visible footer link and the RFC 8058 one-click headers. Opening the link shows a confirm page, and only a POST opts out: the sending brand by default, or everything from the company when the off-by-default setting offers it, with transactional messages never touched. Decided in a seven-question interview (ADR-191). Launch gate 10 was added and closed. Verified by 12 tests (10/10 mutants caught), the full suite, CI green and a live check on scratch data.
<!-- SECTION:FINAL_SUMMARY:END -->
