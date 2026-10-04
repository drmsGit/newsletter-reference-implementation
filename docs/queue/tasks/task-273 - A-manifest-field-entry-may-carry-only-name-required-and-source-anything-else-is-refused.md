---
id: TASK-273
title: >-
  A manifest field entry may carry only name, required and source; anything else
  is refused
status: To Do
assignee: []
created_date: '2026-10-04 15:46'
labels:
  - backend
dependencies: []
type: chore
ordinal: 200095
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Proposed by Claude while finishing task-272 (2026-10-04); the user asked for it to be filed. task-271 and task-272 closed two second sources one key at a time. A manifest field entry may no longer carry `label` (task-271) or `envelope` (task-272): `DEFINITION_ONLY` in `backend/app/modules/registry.py:144`, checked in `_variable` (`:157`). Every other unknown key on a field entry is still silently ignored.

**What an allow-list would catch that a deny-list cannot.** A manifest field entry legitimately carries exactly three keys:
- `name`;
- `required`, a property of (module, field) under [[ADR-177 — A Field Is Defined Once, Required Per Module]] point 4;
- `source`, `content` or `module` (ADR-179's addendum of 2026-10-04, task-223), already validated by `_source` (`registry.py:131`).

Everything else is either part of the definition (`concept`, `size`, `type`, `note`, `channel`, `label`, `envelope`, which belong in `storage/fields.json`) or a typo. The typos fail quietly and in the wrong direction:
- `"requried": false` is ignored, so `declared.get("required", True)` (`registry.py:175`) makes the field required.
- `"sorce": "module"` is ignored, so the field is read from the content record instead of typed in the module.

Today every shipped manifest uses only those three keys on field entries (checked 2026-10-04 across `storage/modules/*/*.json`). So the change should refuse nothing that ships.

**Probable shape, for the worker to confirm.** Replace `DEFINITION_ONLY` with an allow-list `{name, required, source}` and refuse any other key, naming it. The registry already treats a refused manifest the same way everywhere: the module is skipped at discovery with a warning, and the rest stay offered. The message should say where the key belongs: "`storage/fields.json`" for a definition attribute, "unknown key, a typo?" otherwise.

**Open, not decided here.** Should the manifest's top-level keys get the same treatment? Those are `label`, `channel`, `description`, `cms`, `has_template` and `variables`, read in `_load_manifest` (`registry.py:187-207`); a typo such as `"cms "` there silently makes a catalogue module static. That widens the change from field entries to the whole file format. Decide it with the user, or leave it as a follow-up.

**Tests that pin today's rule.** `backend/tests/test_field_definitions.py` refuses `label` and `envelope` (parametrised) and checks that no shipped manifest repeats a definition. Both would become instances of the general rule, plus one typo case per legitimate key.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A manifest field entry with any key other than name, required or source is refused at discovery, naming the key, and the other modules stay offered
- [ ] #2 A misspelt required or source is refused rather than silently defaulting
- [ ] #3 Every shipped manifest still loads
<!-- AC:END -->
