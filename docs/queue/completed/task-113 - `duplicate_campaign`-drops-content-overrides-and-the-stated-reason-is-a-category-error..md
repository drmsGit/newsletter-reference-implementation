---
id: TASK-113
title: >-
  `duplicate_campaign` drops content overrides, and the stated reason is a
  category error.
status: Done
assignee:
  - '@claude'
created_date: '2026-09-27 13:57'
updated_date: '2026-10-02 20:00'
labels:
  - backend
dependencies: []
type: bug
ordinal: 206600
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Bug] — a duplicated variant renders differently from its original, silently. Found 2026-09-26 closing [[Variant Editor - design interview]] question 3.6.** **`duplicate_campaign` drops content overrides, and the stated reason is a category error.** `backend/app/campaigns/duplication.py:147` groups content overrides with resolutions, snapshots, send instances and content versions — *"each of those is a record of something that happened, and a copy has no history — reproducing them would fabricate decisions, publications and sends"*. That reasoning is right about the other five and wrong about this one, because **an override is dual-natured**: it is a record of what happened (`overridden_by`, `reverted_at`, `outcome_delta`) **and** live configuration that `get_active_content_override` reads on every render. Dropping it means the copy produces different output from the original with nothing said — worst in exactly the duplicate-to-repeat workflow (the weekly newsletter) where a manager duplicates *because* they want the same thing again. **The fix draws the line inside the row rather than around it**, which keeps the docstring's instinct: copy `field_overrides`, `system_content_record_id` and `reason`; do not copy `outcome_delta` or `send_instance_id` (they measure a send that happened) or `reverted_at`; set `active = True`; **copy only rows that are already `active`**, since a reset row is purely history and reproducing it would fabricate precisely what the docstring warns about. **`overridden_by` becomes the person duplicating, not the original author** — carrying the name forward attributes an act they did not perform in a campaign they may not know exists, which is the same fabrication arriving through the field the docstring did not consider. Note that this file already reasons per-field about decision slots (copying name, type, strategy and `max_results` but not `candidate_filter`), so the discrimination is an established pattern here rather than a new one.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Final-design pass 2026-10-02. Governing: ADR-040/041 (overrides are live configuration), ADR-178 point 5 (never on a decision slot), ADR-150 (overrides.manage is its own permission), ADR-153 (audit). Interview: Variant Editor Q3.6, Q5.1, Q5.6.
1. In `_copy_variant_into` (`backend/app/campaigns/duplication.py`, shared by duplicate_campaign and duplicate_variant): for each copied module that is still overrideable (bound to a record, no slot), copy the source module's ACTIVE override. Copy field_overrides, system_content_record_id (remapped to the copied record under COPY) and reason. Set active=True and overridden_by=the duplicator. Leave outcome_delta, send_instance_id and reverted_at empty. Reset (inactive) rows never carry.
2. LAYOUT unbinds the module, so its override is dropped and counted in overrides_not_carried. Reports and both JSON responses gain overrides_carried / overrides_not_carried (DECISION, user).
3. Carrying requires overrides.manage on the TARGET brand, else DuplicationForbidden (403), naming the count and offering LAYOUT. Same pattern as COPY needing content.manage there (DECISION, user). The check lives in the service, so all three callers get it. principal and enforced become required keyword arguments with no default, because a default of 'unenforced' is the check a caller forgets.
4. overridden_by comes from the principal: a user's email, 'integration:<name>' for an integration, and a fixed label with auth off. It is never taken from the client.
5. Fix duplicate_campaign's docstring, which lists overrides among 'records of something that happened' (the category error the task names).
6. Callers: JSON campaign + variant routes and the Jinja duplicate route (`backend/app/frontend/router.py:1280`, body edit only; the frozen route list is unchanged). Update the existing test call sites with principal=None, enforced=False.
Not touched: how overridden_by is set on POST /overrides/ (client-asserted). Raised with the user separately.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 400, section "Features", position 66 in that section (top = do next). The description is the original entry, verbatim.

Built 2026-10-02. _carry_override / _require_override_grant / override_author in `backend/app/campaigns/duplication.py`, called from the shared _copy_variant_into, so campaign and variant duplication carry overrides identically. The permission gate runs before any row is written; duplicate_campaign used to flush the campaign before selecting variants, so the gate was placed ahead of that flush, and a test pins the placement (a gate after the flush fails it). principal and enforced are required keyword arguments with no default; all callers updated (both JSON routes, the Jinja duplicate route body, test call sites). Responses gain overrides_carried / overrides_not_carried. The campaign screen says how many overrides came across and in whose name, and its 403 wording now covers the override refusal. Tests: 8 new in TestActiveOverridesCarry, 11 mutants, all caught. Full suite 1009 passed, rc=0; frontend 35 passed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Duplication now carries active content overrides: edit, applied-to record (remapped under cross-brand COPY) and reason; never history (outcome_delta, send_instance_id, reverted_at, reset rows). The person duplicating becomes the author, taken from the authenticated principal. LAYOUT drops them and counts it. Carrying needs overrides.manage on the target brand, else 403 (user decisions). Verified: 8 tests, 11 mutants caught, suite 1009 passed.
<!-- SECTION:FINAL_SUMMARY:END -->
