---
type: adr
status: accepted
topic:
  - architecture
  - decision
  - ai
created: 2026-06-01
modified: 2026-06-05
source:
  - interview-2026-06-01
depends_on:
  - "[[ADR-010 — Newsletter Content Source of Truth]]"
  - "[[ADR-079 — Dynamic Resolution Outside Builder]]"
enables:
  - "[[ADR-081 — AI Ranks Within Governed Candidate Sets]]"
---


## Status

Accepted

## Context

AI-based content selection can become unpredictable if it can freely choose from all available content.

The architecture needs business control over which content may be selected.

## Decision

Content selection must be based on a human-governed taxonomy.

Humans define:

- categories
- subcategories
- category relations
- content scoring
- relevance boundaries

AI may use this structure for ranking and recommendation.

## Consequences

### Positive

- business control remains intact
- less black-box behavior
- better content governance
- safer automation

### Negative

- taxonomy maintenance is required

## Addendum 2026-10-04 — A category score is a whole number from 1 to 10, enforced for every caller

The Decision above says humans define "content scoring". In the code, that is `ContentCategoryAssignmentDB.score` (`backend/app/content/db_models.py:62`). It is an integer, defaults to 10, and says how strongly one record belongs to one category. Three consumers read it:

- `top_score` ranks a slot's candidates by it, highest first (`backend/app/decision/strategies/top_score.py:51`).
- `recipient_top_score` adds it, weighted, to the recipient's preference score (`backend/app/decision/strategies/recipient_top_score.py:110-113`).
- The signal layer scales each contribution by it as `base_weight * (assignment.score / 10)` (`backend/app/insight/service.py:164`). A score of 10 therefore gives a full contribution.

Nothing enforces a range today, and the three write paths disagree:

- `assign_category_to_content` refuses only zero (`backend/app/content/service.py:732-737`). Its comment calls the 0-10 range "a POC-only convention, not enforced here".
- The JSON API's `ContentCategoryAssignmentCreate` accepts any integer (`backend/app/content/models.py:114-116`).
- The Jinja assign form allows 1 to 100 (`backend/app/templates/content_detail.html:339`).
- The CSV import clamps to 0-10 (`backend/scripts/import_content_csv.py:155`), which lets through the zero that the service refuses.

Most records score between 5 and 10. One record scored 100 would come first in every slot that can reach it. Every engagement with it would also count ten times over in the recipient's profile. A score is a human judgement on a bounded scale, and without the bound it works as an override.

The question came up while designing the React content write surface (task-274), the screen where categories are assigned. The user answered it in that design interview on 2026-10-04, one question at a time. This section records the answers.

**1. A category score is a whole number from 1 to 10.** 1 means the record barely belongs to the category. 10 means it squarely belongs. The server enforces this for every caller: the JSON API, the Jinja form and the CSV import. A value outside the range is refused, not clamped. So the CSV import's clamp goes, and the import refuses an out-of-range score instead of correcting it. The import writes `ContentCategoryAssignmentDB` rows directly (`backend/scripts/import_content_csv.py:151-157`) and does not call `assign_category_to_content`. A check placed only in the service would therefore never see imported rows. Where the check sits, so that all three callers pass through it, is a question for the final design pass.

**2. Existing rows outside 1-10 are reported for a person to fix. They are never changed silently.** The range applies to every write from now on. Rows already stored outside it are listed for a person to correct, and nothing rewrites them automatically. Clamping them afterwards would be the same silent correction that point 1 refuses at write time.

**3. A score is changed in place on an existing assignment, through a small new route.** Today the only way to change a score is to remove the assignment and add it again. In the JSON API that is `DELETE /{content_id}/assignments/{assignment_id}` (`backend/app/content/router.py:547-560`) followed by `POST /{content_id}/categories` (`backend/app/content/router.py:332`). Adding the same category a second time is refused while the first assignment exists (`backend/app/content/service.py:750-751`). Between the two calls the record is out of that category, and a slot resolving in that gap would not see it. The new route updates the score on the existing assignment, so the gap disappears. It enforces the same range as point 1.

**4. The record's content screen says what categories are for.** It carries this sentence: "Categories build each recipient's interest profile. For finding content, facets will follow." Categories are the affinity vocabulary this record governs, and [[ADR-179 — What Enters the Catalogue, and What a Machine May Take From It]] says the same. Labels for finding content belong to facets, per [[ADR-175 — Facets Are the Manager's Own Taxonomy, Not the Engine's]] and its addendum of 2026-10-04. That addendum lets the bind picker read categories but never write to them. Stating this where categories are assigned stops a manager from filing records under a findability label just because no other vocabulary exists yet. Creating categories stays off the record screen: that screen assigns categories from the vocabulary and never adds to it.

**This is not a supersession.** The Decision above stands unchanged. Humans still define content scoring. This section fixes the scale scores are given on and requires every write path to respect it.

**Two code comments describe the state this addendum ends.** One is in `assign_category_to_content` (`backend/app/content/service.py:732-735`), which calls the range an unenforced POC convention. The other is at `backend/app/insight/service.py:163`, which describes the score as 0-10. Both become wrong once this is implemented.

The interface belongs to [[Content Write Surface - final design pass]], not to this record: how a score is entered and changed, and how the report of out-of-range rows is shown.

## Related ADRs

### Depends On

- [[ADR-010 — Newsletter Content Source of Truth]]
- [[ADR-079 — Dynamic Resolution Outside Builder]]

### Enables

- [[ADR-081 — AI Ranks Within Governed Candidate Sets]]
