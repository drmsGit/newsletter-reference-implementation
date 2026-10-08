---
id: TASK-305
title: A complaint is never used as a content-quality signal — only as an opt-out
status: To Do
assignee: []
created_date: '2026-10-08 22:21'
labels:
  - backend
dependencies: []
type: feature
ordinal: 203950
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Feature: a complaint as a content-quality signal, separate from the opt-out it already triggers.** Split out of task-70 on 2026-10-08, when task-70 was closed as built (queue cleanup after backlog-sequencer run 3, decided by the user).

task-70 asked for two distinct reactions to a spam complaint.
- (1) Opt the person out. This is built: a hard bounce or complaint opts the recipient out on the channel, purpose and brand that mailed them (`backend/app/providers/service.py:196-216`, ADR-106, ADR-163 addendum 2026-09-15).
- (2) Separately, feed the insight layer as a content-quality signal, as in "this content triggered a lot of complaints": an analytics reaction to the same event, not the same action as the consent update. This one is not built.

The insight layer deliberately leaves complaints out today. `backend/app/insight/service.py:15` says unsubscribe and complaint are handled on the consent path, not as a per-category signal, and only open and click are content-tied (`_CONTENT_TIED_EVENT_TYPES`). The Resend adapter already normalizes the event (`backend/app/providers/adapters/resend.py`, `RESEND_EVENT_TYPE_MAP`), so the input exists.

**What this needs before any build:**
- Whether the signal is per content record, per category, per campaign or per send. A complaint is about a whole email, not one module, so pinning it to a content record is a design choice, not a given. The per-category machinery of ADR-132 would attribute it to every category in the email.
- Whether it is shown, or only fed to scoring. A negative affinity of this kind is close to task-86's negative category-affinity idea, which was decided as a system proposal only; this probably follows the same rule.
- Volume. Complaints are rare by design, so any rate needs a floor before it means anything.

Parked idea, not urgent. Its value appears once real sends have complaint volume. Source: task-70 (user, via the Delivery, Providers, Recipients interview prep and the business-interview baseline section F2).
<!-- SECTION:DESCRIPTION:END -->
