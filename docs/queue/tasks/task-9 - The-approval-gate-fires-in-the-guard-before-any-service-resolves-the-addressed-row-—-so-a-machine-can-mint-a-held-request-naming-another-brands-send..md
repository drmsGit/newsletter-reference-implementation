---
id: TASK-9
title: >-
  The approval gate fires in the guard, before any service resolves the
  addressed row — so a machine can mint a held request naming another brand's
  send.
status: To Do
assignee: []
created_date: '2026-09-27 13:56'
labels:
  - backend
dependencies: []
priority: p3
type: bug
ordinal: 100900
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Bug] — P3, and it is the residue of P1-02 rather than the hole itself.** **The approval gate fires in the guard, before any service resolves the addressed row — so a machine can mint a held request naming another brand's send.** `enforce_api_policy` raises `ApprovalRequired` once the caller is authenticated, authorised and has declared a brand; what it cannot check is whether the *resource named in the path* belongs to that brand, because the guard is generic and the path parameter means nothing to it. So a credential on brand A posting `/delivery/send-instances/{a brand-B id}/send` gets a 202 and a pending row branded A whose payload points at B. **Closed as of 2026-09-20, in three places, none of which is the guard:** `summarise` freezes the summary within the request's brand, `describe` resolves the review panel within it, and `execute` is handed the row's brand — so the approver sees "no longer present", the button is blocked, and approving refuses. Pinned by `test_a_held_request_naming_another_brands_send_discloses_nothing`. **What remains is noise, not risk:** a caller can still put a row in somebody's inbox that nobody can act on. **Fix, when it matters:** `APPROVABLE_ROUTES` already maps a route template to an action key; it could also name which path parameter is the subject and how to resolve it, letting the guard refuse an unreachable subject before queueing anything. That is a change to [[ADR-142 — Autonomous Workflows and the Automation Boundary]] §4's shape, not to [[ADR-172 — The Working Brand Is Resolved Once and Carried Into Every Query]], which is why it is logged rather than built.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 47, section "Bugs", position 9 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
