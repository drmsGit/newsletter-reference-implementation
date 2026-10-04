---
id: TASK-272
title: >-
  The header manifest still declares envelope inline, a second source beside its
  field definitions
status: To Do
assignee: []
created_date: '2026-10-04 11:40'
labels:
  - backend
dependencies: []
type: chore
ordinal: 200090
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Found 2026-10-04 while building task-271 (field labels). The adr-author agent flagged it, and the user asked for a task.

**What is there.** `storage/modules/email/header.json:7-8` still declares `"envelope": true` inline on `subject` and `preheader`. `storage/fields.json` declares the same `envelope: true` on both definitions. `_variable` in `backend/app/modules/registry.py:168` resolves the two as `envelope=bool(spec.get("envelope", declared.get("envelope", False)))`: the definition wins, and the manifest is the fallback when the definition says nothing.

**Why it matters, though nothing is wrong today.** The two sources agree, so behaviour is correct. But [[ADR-177 — A Field Is Defined Once, Required Per Module]] point 3 makes `envelope` "a property of the field", and the fallback is still a second source:
- A new field whose definition forgets `envelope` but whose manifest says `true` quietly becomes an envelope field from the manifest.
- A manifest that disagrees with its definition is silently overruled instead of being told.

ADR-177's addendum of 2026-10-04 (task-271) closed exactly this for `label`: a manifest that labels a field is now refused at discovery, and the module is skipped with a warning. `envelope` is the one other definition attribute the registry still reads from a manifest; `required` and `source` are rightly per (module, field).

**Probable shape, for the worker to confirm.** Remove the two inline keys from `header.json`. Read `envelope` from the definition only. Refuse a manifest that declares it, as `label` is now refused. Then decide whether ADR-177 point 3 already covers the refusal or the 2026-10-04 addendum needs a line (through the adr-author agent).

Tests that touch this:
- `backend/tests/test_channels.py` asserts `subject.envelope is True` on the header manifest. It should keep passing from the definition alone.
- In the same file, `test_the_declaration_is_what_decides_not_a_hardcoded_name` plants an envelope field through `fields.json`, not the manifest, so it already follows the one-source rule.
- `envelope_module_type` (`registry.py:303`) finds the envelope module by reading these flags and must keep answering `header` for email and None for push.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Whether a field is an envelope field is read from storage/fields.json only
- [ ] #2 A manifest that declares envelope on a field is refused at discovery, as one that labels a field is
- [ ] #3 Email's envelope module is still header and push still has none, proven by the existing tests passing unchanged
<!-- AC:END -->
