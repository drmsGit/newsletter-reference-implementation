---
id: TASK-118
title: >-
  Should the content catalogue's field set be the union of every module
  manifest's declared variables?
status: Done
assignee: []
created_date: '2026-09-27 13:57'
updated_date: '2026-09-27 14:23'
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

2026-09-27: [[ADR-177 — A Field Is Defined Once, Required Per Module]] decides this question; the implementation is task-219. The interview session recommends marking this Done once task-219 exists — which it now does — so the thread from decision to implementation stays visible. Status change is the user's call.

Closed 2026-09-27. This sat in the Needs-ADR band, whose semantics are 'blocked on a design decision'. [[ADR-177 — A Field Is Defined Once, Required Per Module]] makes that decision, so it is unblocked — which is what Done means in this section.

The implementation is **task-219**, which exists; this was closed on that condition rather than on the ADR alone. 'The ADR is written' must not be read as 'the work is done', and the thread from decision to implementation runs through task-219, not through this entry.

What ADR-177 settled: field definitions centralise in `storage/fields.json`; a module manifest keeps which fields it uses and `required` for each and stays a drop-in pair; the storage key stays an explicit name rather than being derived from concept and size, because a rename would silently orphan content in an unvalidated JSON column. `CONTENT_FIELD_GROUPS` and the CSV importer's duplicate collapse into the new file.
<!-- SECTION:NOTES:END -->
