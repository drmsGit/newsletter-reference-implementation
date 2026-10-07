---
id: TASK-300
title: 'Category interest takes several categories, each with its own score'
status: In Progress
assignee:
  - '@claude'
created_date: '2026-10-06 21:20'
updated_date: '2026-10-07 20:47'
labels:
  - backend
  - frontend
dependencies: []
type: feature
ordinal: 200384
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Raised by the user on 2026-10-06, using the new audience editor (task-297): a rule "language de, status active, category Nature at least 5" could not also take Wellness at least 5. A second rule holding only Wellness brings in every language and status, so "de and active and (Nature or Wellness)" needed two rules each repeating "de, active".

That contradicts [[ADR-188 — Audience Rules Are Flat, and May Read Engagement History]] point 1 ("a field takes one or more values"). The first build kept category interest single-valued in the server's check (backend/app/audience/service.py:204-222, normalise_criteria, task-295) and in the editor's rule form (frontend/src/screens/AudienceRules.tsx, task-297). Decided with the user on 2026-10-06 and recorded in the ADR-188 addendum of that date:
- several categories per field, OR inside the field;
- each category with its own minimum score (point 3 per category: above 0, 1.0 filled in);
- the shared condition stays in the rule;
- a third section "Everyone must also" (X and (Y or Z) across fields) is recorded as the next step, not built here.

It comes before task-298 so the engagement field lands on the corrected rule shape.

**Final design pass (where each part lands):**
- Stored shape: criteria.categories = a list of {category_id, min_score}. normalise_criteria (service.py:196-222, CRITERIA_FIELDS at :114) accepts the list, and still accepts the old category_id + min_score pair as input, normalising it to a one-entry list (the Jinja form at backend/app/templates/audience_group_detail.html:20-23 and existing integrations keep working, the way the optional If-Match did). Refusals name the entry: categories.N.min_score.
- Matching: find_by_criteria (service.py:578, :653-656) takes the list; a person matches when their operational signal clears the threshold in any one listed category (operational_signals_for_category once per category). The other callers follow: _recipients_for_criteria (:785-797), criteria_matches (:1470-1482) and the criteria-preview route (backend/app/audience/router.py:482-500, still single-category query parameters, passed as a one-entry list).
- A migration (next number in backend/scripts/, a .py like 0035) rewrites existing rules to the list form; the build reports how many.
- Suggested rules keep one category each: suggest_include_blocks_for_campaign (service.py:1339) writes a one-entry list, recalculate_suggested_blocks (:1424-1435) reads the category of a one-entry list, so suggestions are never merged and the delta stays per category.
- The preview's per-rule category_name (service.py:988; PreviewBlock in models.py) becomes the names of all listed categories.
- The Jinja rule form shows a one-category rule as today; a rule with more than one category is shown read-only there with a pointer to the manager client, so saving the old form cannot drop categories.
- The editor: the category part of a rule form becomes a list of rows, each a CategoryChoice and its score, with "Add a category" and a remove per row; the score is filled in at 1.0 for each new row.
- **A saved rule reads as one line** (the user, 2026-10-07, after seeing every rule open as a full form in task-297): e.g. "Language de · active · Nature at least 5 or Wellness at least 5", with the rule's name and the suggested badge, and an "Edit" that opens the form for that rule only; "Save rule" or "Cancel" closes it again. A new rule opens as a form. Spacing, borders and sizes stay with the layout session; this is how the editor behaves, not how it looks.

**Deliberately not touched:** the engagement field (task-298), related data (task-294), the "Everyone must also" section, nested groups.

**What could break:** rules written by integrations in the old shape (accepted and normalised); a Jinja edit of a multi-category rule (made read-only); anything reading criteria.category_id directly (service.py lines above, the template; checked with grep at build time).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A rule can hold several categories, each with its own minimum score above 0, matching anyone who clears any one of them
- [ ] #2 Existing rules are migrated to the list form and the old single-category input is still accepted
- [ ] #3 Suggested rules and Recalculate from campaign keep working per category
- [ ] #4 The editor adds and removes categories within one rule, each with a score filled in at 1.0
- [ ] #5 A saved rule shows as one line naming its conditions, and Edit opens the form for that rule only
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Server tests first: several categories (OR, a score each), the legacy pair normalised, refusals (no score, 0, unknown key, the same category twice, both shapes at once), suggested rules as one-entry lists, recalculate per category, the preview naming all categories, the migration rewriting the legacy pair with an audit entry and being idempotent.
2. service.py: normalise_criteria takes categories or the legacy pair; one reader (_category_terms) for both shapes; find_by_criteria matches any listed category; _recipients_for_criteria, criteria_matches, count, preview, suggest and recalculate read through it.
3. Jinja: the summary reads the list; a rule with several categories shows read-only with a pointer to the manager client (no edit form that could drop them).
4. migrate_0037 (.py, dry-run default, audited per rule), applied before the .py edits are live.
5. Client tests first, then AudienceRules.tsx: category rows (CategoryChoice + score, Add a category, remove), a saved rule as one line with Edit opening its form.
6. Mutation check, suites, contract, commit, live check on a scratch audience, finalize.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
To keep apart when building (found while writing the ADR-188 addendum): a rule's minimum score is the recipient's interest score (operational signal, ADR-132), a different scale from a record's category score, which ADR-080's 2026-10-04 addendum limits to whole numbers 1 to 10. The rule form's labels and hint must not suggest the 1-10 range.
<!-- SECTION:NOTES:END -->
