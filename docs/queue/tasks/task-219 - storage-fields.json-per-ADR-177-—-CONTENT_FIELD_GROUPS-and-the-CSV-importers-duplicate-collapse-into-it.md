---
id: TASK-219
title: >-
  storage/fields.json per ADR-177 — CONTENT_FIELD_GROUPS and the CSV importer's
  duplicate collapse into it
status: To Do
assignee: []
created_date: '2026-09-27 14:20'
labels:
  - backend
dependencies: []
priority: parked
type: feature
ordinal: 208400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** The catalogue field set is defined once, centrally, and derived from rather than repeated. The interview settled three layers of field definition together:

| Lives where | Carries |
|---|---|
| `storage/fields.json` (**new, central**) | `concept`, `size`, `type`, `note`, `envelope` — what a field *is* |
| the module's own manifest (**unchanged, drop-in**) | which fields it uses, and `required` for each — a property of *(module, field)* |
| `ContentRecordDB.content` | the values, in one unvalidated JSON column, needing **no migration ever** |

The gaps, as each interview logged them:

| # | Gap | Where |
|---|---|---|
| 3 | Catalogue field set should derive from manifests | `content/service.py:101` |
| 10 | `fields.json` does not exist; `CONTENT_FIELD_GROUPS` and its duplicate collapse into it | `content/service.py:101`, `scripts/import_content_csv.py:33` |

And from the Manager Workflow interview: **Maintenance that falls out**, needing no ADR: `CONTENT_FIELD_GROUPS` reads from the manifests rather than repeating them, and the duplicate email field list in `backend/scripts/import_content_csv.py:33-41` goes with it.

Source: [[Variant Editor - design interview]] → What Cluster 1 produced, gap 3, and What Cluster 2 produced, gap 10 (Q2.8, 2.10, 2.4); [[Manager Workflow - design interview]] → What Cluster 2 produced.

**Decided:** [[ADR-177 — A Field Is Defined Once, Required Per Module]].

**Verified against the code 2026-09-27:** `storage/fields.json` does not exist. `CONTENT_FIELD_GROUPS` is hardcoded at `backend/app/content/service.py:101-108` (its own comment at `:95-100` calls the manifests its proper home), consumed at `:142,146` and referenced from `backend/app/content/models.py:38`. The same email keys are repeated as `CONTENT_KEYS` in `backend/scripts/import_content_csv.py:33-40`.

Related: task-118 (📋, the question this implements).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.
<!-- SECTION:NOTES:END -->
