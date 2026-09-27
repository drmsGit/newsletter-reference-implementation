---
id: TASK-118
title: >-
  Should the content catalogue's field set be the union of every module
  manifest's declared variables?
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - needs-adr
  - backend
dependencies: []
ordinal: 300200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
📋 **Should the content catalogue's field set be the union of every module manifest's declared variables?** Proposed by the user 2026-09-25 during [[Variant Editor - design interview]] question 1.3, with a worked example, and recorded as interview question 2.8. **The technical premise is verified**: `ContentRecordDB.content` is `Column(JSON, nullable=False, default=dict)` — one column, no per-field columns, no validation — so a module introducing new variable names needs **no migration, ever**, and manifest discovery already walks every file at startup. **The codebase independently reached the same conclusion and recorded it as a stopgap**: `CONTENT_FIELD_GROUPS` (`backend/app/content/service.py:101`) hardcodes the per-channel field list and its docstring says the manifests are *"where it belongs"*, blocked only on "a flat list of the content keys a channel reads" — which is precisely this union. A duplicate of its email half in `backend/scripts/import_content_csv.py:33-41` collapses with it. **Four things need deciding before it is an ADR:** `required` stops being a property of a field and becomes one of *(module, field)*; `label` has the same problem; the authoring form grows with the module library, so the union needs a grouping discipline rather than a flat list; and exact-name union is also exact-name collision with no namespacing. **One tension to settle explicitly:** the 2026-09-22 ruling that *"we shouldn't rely on reading the module json"* was about deriving **which channel a field belongs to**; this derives **which fields exist**. Both can hold, but the manifests are filed per channel, so the union makes the channel derivation available whether or not it is used. **This is a content-catalogue decision surfaced by the editor interview, not an editor decision**, and it changes what the interview's Cluster 2 form questions are asking about.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 412, section "Needs ADR", position 2 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
