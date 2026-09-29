---
id: TASK-233
title: >-
  An exclude block cannot reach a recipient who has no email address, including
  on a push send
status: To Do
assignee: []
created_date: '2026-09-29 13:23'
labels:
  - backend
dependencies: []
priority: p1
type: bug
ordinal: 100060
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Bug] — an exclusion segment silently fails to exclude, and on push it leaks.** Found 2026-09-29 while writing the [[ADR-176 — A Negative Decision Outranks a Positive One]] point 1 test (task-47), which failed against correct code until the fixture recipient was given an email address.

**The asymmetry.** A rule block's criteria resolve through `_recipients_for_criteria` → `find_by_criteria` (`backend/app/audience/service.py:402,241`), which ends in `_deduplicate_by_address` — and that helper drops any recipient with no usable address, by design: *"A recipient with no usable address is dropped here too — they are not addressable on this channel, which is precisely what stage 1 means."* Manual pins (`get_member_recipient_ids`) do **not** pass through that filter, and neither does `resolve_audience`'s final consent gate. So a recipient with no address can be pinned into a group and **no exclude block can remove them**, however exactly its criteria match.

**On push this is a live leak rather than a cosmetic one.** `_deduplicate_by_address` calls `resolve_emails`, which asks about **email** addressability regardless of the channel `resolve_audience` was given. **Verified 2026-09-29 against the dev database:** a push-only recipient (push token, push consent, no email address) pinned to a group with an exclude block matching their language is returned by `resolve_audience(db, group_id, "push")`. The push send can reach them, so the exclusion is ignored on the one channel where it costs something.

**Why it matters more now than yesterday.** Before ADR-176 point 1 a pin beat an exclude block by design, so this was invisible — the pin was supposed to survive. Point 1 makes the exclusion the safety, and the record's argument is that *wrongly including costs more than wrongly omitting*. An exclusion that quietly does not apply to part of the group is exactly the failure that record exists to prevent.

**Two separable defects, and they want different fixes.** (a) `_deduplicate_by_address` is an **addressability** stage (ADR-163 point 7) being applied inside a **membership** query — arguably `find_by_criteria` should not dedupe at all when it is resolving an exclude block, since dropping someone from an exclusion is the opposite of dropping them from a send. (b) The email hardcoding is a channel bug of the same family as the `resolve_audience` channel default (ADR-176 addendum 2026-09-27) and `modules/router.py`'s `channel="email"` (task-21).

**Unverified:** whether an *include* block has the mirror problem — a recipient with no email address may be unreachable by include criteria on a push send too, which would be a different failure (under-reaching rather than over-reaching) and is the reason not to fix (b) by simply threading the channel through without checking what else changes.
<!-- SECTION:DESCRIPTION:END -->
