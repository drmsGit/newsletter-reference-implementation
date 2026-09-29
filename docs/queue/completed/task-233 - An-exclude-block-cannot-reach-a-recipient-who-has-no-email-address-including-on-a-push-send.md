---
id: TASK-233
title: >-
  An exclude block cannot reach a recipient who has no email address, including
  on a push send
status: Done
assignee: []
created_date: '2026-09-29 13:23'
updated_date: '2026-09-29 13:52'
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

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Fixed 2026-09-29, commit de3e007. 688 tests passing.

THE UNVERIFIED HALF WAS THE LARGER ONE. The entry ended asking whether include blocks had the mirror problem. They did, and worse: find_by_criteria called is_consenting_filter(brand_id) with no channel, so it defaulted to email. A push-only recipient matched by an INCLUDE block resolved into nothing — rule-based push audiences did not work at all, only pins did, and the resolver returned [] rather than raising, so nothing said so. Verified against the dev database before the fix.

Fix (a): find_by_criteria takes a required channel keyword and gates consent on it. Required rather than defaulted, on the ADR-176 addendum's own reasoning about resolve_audience — a convenience default on a membership question is fail-open. _recipients_for_criteria, count_for_criteria and the two Jinja call sites thread it; the Jinja ones pass DEFAULT_CHANNEL explicitly with the existing 'email is correct here rather than merely preserved' reasoning.

Fix (b): _deduplicate_by_address is deleted from the audience layer. Addressability filtering and address deduplication are now stage 1 of run_exclusion_stack, where ADR-163's 2026-09-12 addendum point 3 placed them — the helper's own docstring cited that placement while sitting somewhere else, for seventeen days, with no failing test. The dropped duplicate carries a recorded Exclusion naming the recipient that covered the address (point 8), which the old silent 'continue' could not. Earliest id wins, deterministically.

THE RIDER I NEARLY BROKE. That same addendum point 3 carries a rider: the audience preview must run the same addressability stage or a displayed count over-reports. Removing the filter from the resolver regressed against it. Honoured by having the group-detail screen run run_exclusion_stack over the resolved set and report reachable and unreachable as two numbers — the stricter reading, since it is the send's own answer rather than a second implementation that can drift. Smoke-tested: the page returns 200 and renders '1 recipient(s) net' beside '1 unreachable' for a group holding one of each.

Accepted cost, stated in the ADR-163 addendum: a resolved audience now counts people the send will drop, and prepare_send_from_audience materialises an execution for each before stage 1 excludes it. That buys the recorded reason, and means the recipient cap is checked against the planned set rather than the reachable one — the conservative direction for a guardrail.

Three regression tests, each mutation-checked against the specific thing it guards (test_audience_api.TestExclusionReachesTheUnaddressable, TestPushCriteriaAskAboutPush, and test_consent_gates.TestAddressabilityIsAnsweredAtSendTime). The old dedup tests were rewritten rather than deleted: test_consent_gates' header had predicted this move in writing — 'the assertion must hold before and after; only its implementation site moves' — and it did.

ALSO REMOVED, found in passing: suggest_include_blocks_for_campaign's per-suggestion 'count'. Its docstring said it was there 'so the manager sees the impact before accepting', which is a real requirement that was never wired to a screen — both callers take criteria and label and discard the rest. Threading a channel through to compute a discarded number would have been work in service of dead code. Whoever builds that screen calls count_for_criteria with the channel in hand.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Membership queries no longer filter by reachability. find_by_criteria takes a required channel and gates consent on it; addressability and address deduplication moved to stage 1 of the exclusion stack, where ADR-163's 2026-09-12 addendum point 3 had placed them seventeen days earlier. Closes both faces: an exclude block now reaches a pinned unaddressable recipient, and an include block now finds a push-only recipient on push — the latter meant rule-based push audiences did not work at all. That addendum's preview rider is honoured by the group screen running the real stack and reporting reachable and unreachable separately. Verified by 688 passing tests including three new mutation-checked regressions, and a smoke test of the rendered page.
<!-- SECTION:FINAL_SUMMARY:END -->
