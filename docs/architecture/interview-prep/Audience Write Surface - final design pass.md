---
status: decided
date: 2026-10-06
---
# Audience Write Surface — final design pass

**Status: decided, 2026-10-06 (task-293), with the user, one question at a
time. Nothing here is built yet. The rule logic is recorded in
[[ADR-188 — Audience Rules Are Flat, and May Read Engagement History]]; the
work is filed as task-295 to task-298.**

Raised by the user on 2026-10-06: the React client could show an audience
(its reach and arithmetic, task-213) but not create or edit one. Creating a
group, its rules and its hand-added people existed only on the Jinja pages,
which the React client replaces. The same gap the content screens had before
task-274, handled the same way: [[Content Write Surface - final design pass]]
is the precedent.

## Already decided, not reopened

- [[Manager Workflow - design interview]] Cluster 4: the system suggests and
  the manager adjusts (4.1; suggestion starts on the campaign screen, the
  audience screen offers "Suggest from campaign"); an exclusion beats a
  hand-add (4.2, [[ADR-176 — A Negative Decision Outranks a Positive One]]
  point 1); trust comes from the arithmetic (4.3, built in task-213); every
  number is per channel (4.4); recalculating suggested rules is always manual
  (4.7).
- [[ADR-093 — Audience Intelligence Is Derived, Not Authoritative]]: rule
  membership is never stored. [[ADR-123 — Audience Ownership Depends on Reuse]]:
  groups here are temporary or campaign-specific; long-lived ones belong in
  the CRM.
- [[ADR-163 — Per-Channel Consent and Addressability]] and its 2026-10-06
  addendum: people who have not agreed are counted, never listed.

## Decisions

1. **The group's page is the editor**, not a separate edit mode. "New
   audience" on the list asks for a name and description and opens the empty
   page. The rules are listed and edited in place, the hand-added people
   below, and the arithmetic (task-213) beside them updates after every
   saved change, on the chosen channel — the first switched-on one, with the
   switch visible (closes 4.4's open presentation question).
2. **What a rule says** — [[ADR-188 — Audience Rules Are Flat, and May Read Engagement History]]:
   language, status and category interest today; a category always with a
   minimum score (1.0 by default, never 0); every rule validated, unknown
   fields refused; values offered from what exists.
3. **Flat logic, multi-value fields** (ADR-188 point 1): values OR inside a
   field, fields AND inside a rule, rules OR across, exclusions subtract. No
   nested groups.
4. **CRM attributes and other related data** (sales, product) are a separate
   decision — task-294. The editor works with today's fields until then.
5. **People added by hand:** add one with the recipient search (the preview's
   picker, extracted), with an optional reason; who and when are recorded
   automatically (closes task-217). Remove one, audited. No expiry for now
   (task-107's expiry question stays open, if wanted at all; its "nothing can
   remove a member" is stale — removal exists). "Add by criteria" is not
   offered in the editor (a frozen copy of a rule's matches goes stale; a rule
   is live); its server route stays for the Jinja pages. The hand-added list
   shows each reason, who and when, and marks anyone an exclusion removes.
6. **"Paste people":** a text box; identifiers separated by new lines,
   commas, semicolons or spaces; matched by CRM identifier, or by email
   address when the entry holds "@"; one optional reason for the paste. A
   report before anything is added — "312 will be added, 8 are already in",
   "4 not found" (listed), "12 have not agreed to email" (added, will not
   receive) — then "Add 312". Nobody is created (the CRM owns people,
   ADR-120). Up to 5,000 per paste; bigger lists belong in the CRM as a
   segment (ADR-123). No CSV wizard.
7. **Engagement in a rule** (ADR-188 points 4 and 5): received, opened or
   clicked; a specific send, any send of a campaign, or any send; absolute or
   relative time. "Opened" is included — the company's call, and what
   reminders use. "Did not" is an exclusion, explained once in the editor.
   Closes task-215.
8. **Deleting a group:** an unused group is deleted after a confirmation,
   audited. A group any send uses — planned or sent — is refused with a plain
   explanation naming the sends ("Sent mail must keep its audience; remove it
   from planned sends first"). No archive or soft delete for now.
9. **Wording** (ADR-188 point 6): "Who's in" and "Leave out"; under "Leave
   out": "Leaves these people out even if a rule or a hand-add includes them.
   People who opted out are never sent to anyway: that's consent, not this
   list."; the "did not" hint ("To reach people who did not click, include
   who received it and leave out who clicked"). No blocklist or suppression
   wording.
10. **Saving and concurrent edits:** one version for the whole group — any
    change (name, a rule, a hand-add) moves it and every write states it
    (ADR-180 point 2); a second editor gets "Somebody changed this audience.
    Load their version". Name and description save on leaving the field; a
    rule saves with its own "Save rule" (a half-built rule would briefly
    change the live audience); adding or removing a person is immediate.
    Every write audited (ADR-153 point 4).

## Decided in this pass (follow from the answers; not asked)

- **"Received" means handed to the provider and not bounced** (the user,
  2026-10-06): excluded and failed deliveries never count, a bounce removes
  the person, and no confirmed "delivered" is required, since not every
  provider reports it.
- **A minimum score must be above 0.** "Never 0" (decision 2) covers a
  negative score too, which would match even more people (an unsubscribe
  contributes a negative signal, `backend/app/insight/signals.py`).
- **Rename merges:** `PATCH /api/audience-groups/{id}` today reuses the
  create model, so leaving out the description clears it. It becomes a
  partial update — only what is sent changes — like the content record's.
- **A rule's label can be cleared:** today a `None` label is skipped on
  update.
- **Existing rules with a category and no score** (they match everyone
  today) are fixed once by the migration that brings validation: they get the
  1.0 default, recorded in the audit log as a system change, and the build
  task reports how many there were. Changing their meaning silently would be
  worse than either alternative; the count lets the user see the size.
- **Values offered for language and status** come from a small read route
  listing the distinct values among the brand's recipients (counted, never
  listed, for people who have not agreed — ADR-163's addendum).
- **Permissions stay as they are:** `audiences.manage` for the group and its
  rules, `audiences.pin` for hand-adds (`backend/app/auth/policy.py`). Who
  may edit is unchanged; this is about how.
- **The suggested-rule badge and "Recalculate from campaign"** show on rules
  whose source is `suggested` and on groups with a source campaign, as the
  Jinja page does (4.7: manual).

## Where each part lands

| Part | Server | Client | Task |
|---|---|---|---|
| Hardening the writes | one version token (the group's `updated_at`, moved by any rule or member write) on every write; audit on every write; rename as a partial update; a typed criteria schema (refuse unknown fields; category requires a score > 0; language and status as lists); the migration fixing scoreless category rules; delete refused (409, naming the sends) when a send uses the group; member reason and added-by (migration); the paste route (preview, then add; by identifier or email; cap 5,000); the distinct-values route | — | build 1 |
| Engagement criteria | received / opened / clicked over `DeliveryExecutionDB` and `EngagementEventDB`; send, campaign or any; absolute and relative windows; in `find_by_criteria`, so the arithmetic (task-213) and the per-person lookup (task-214) follow; measured, indexed where needed | — | build 2 |
| The editor | — | "New audience"; the rules ("Who's in", "Leave out") with "Save rule", the category picker, value choices; the live arithmetic; the hand-added list with reasons and exclusion marks; add one (the extracted recipient picker); "Paste people"; delete; "Suggest from campaign", the badge, "Recalculate" | build 3 |
| Engagement in the editor | — | the engagement field (what, which mailing, when) and the "did not" hint | build 4 |

**Deliberately not touched:** consent and suppression (an exclusion is
editorial; task-231 stays blocked on task-135); expiry of hand-adds
(task-107); related data and CRM attributes (task-294); the Jinja pages
(they keep working through the same service).

## What could break

- **Existing scoreless category rules change meaning** (from "everyone" to
  "score ≥ 1.0") — deliberately, with a count reported.
- **Engagement rules read the fastest-growing tables.** Resolution cost rises;
  build 2 measures and indexes (task-106 is the benchmark task).
- **"Opened" over-counts** machine opens (Apple Mail Privacy) — the user's
  explicit choice; the editor does not hide it.
- **The version token is new on these routes.** The Jinja forms send none
  and stay accepted (no token, no check — the composer's rule).
- **Delete was a 500, becomes a 409** for a group any send uses.

## Build tasks

1. **task-295** — audience writes: version, audit, validated rules, safe
   delete, hand-add reasons, paste (backend).
2. **task-296** — audience rules can read engagement: received, opened,
   clicked (backend; closes task-215).
3. **task-297** — the React audience editor (frontend; depends on 295).
4. **task-298** — engagement in the audience editor (frontend; depends on
   296 and 297).
