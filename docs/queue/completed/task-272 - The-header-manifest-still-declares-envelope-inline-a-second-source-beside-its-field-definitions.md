---
id: TASK-272
title: >-
  The header manifest still declares envelope inline, a second source beside its
  field definitions
status: Done
assignee:
  - '@claude'
created_date: '2026-10-04 11:40'
updated_date: '2026-10-04 11:46'
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
- [x] #1 Whether a field is an envelope field is read from storage/fields.json only
- [x] #2 A manifest that declares envelope on a field is refused at discovery, as one that labels a field is
- [x] #3 Email's envelope module is still header and push still has none, proven by the existing tests passing unchanged
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Remove the inline envelope keys from header.json.
2. In registry._variable, read envelope from the definition only. Replace the label-only refusal with one tuple of definition-only keys (label, envelope) that a manifest field entry may not carry. Governed by ADR-177 point 3 (envelope is a property of the field) and the 2026-10-04 addendum's refusal rule; no ADR change.
3. Tests (rename test_field_labels.py to test_field_definitions.py): a manifest declaring envelope is not offered; envelope comes from the definition even if a manifest omits it; email's envelope module is still header and push has none. Mutation-check, full suite.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Built 2026-10-04.
- header.json no longer declares envelope.
- registry._variable reads envelope from the definition only; the manifest fallback is gone. One tuple, DEFINITION_ONLY = ("label", "envelope"), replaces the label-only check: a manifest field entry carrying either is refused and that module is skipped at discovery.
- No ADR change. ADR-177 already calls envelope a property of the field (line 29, point 3 table), and the refusal mirrors its 2026-10-04 addendum point 3.
- tests/test_field_labels.py renamed to test_field_definitions.py, adding: refusal parametrised over label and envelope; no shipped manifest repeats a definition; the envelope still comes from the definitions (header for email, none for push). test_channels envelope tests unchanged and passing.
- Mutation-checked against 4 mutants, each caught. Backend 1230 passed.
- Checked live: the variant editor's envelope area still shows "Subject line" and "Preheader (inbox preview)".
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Whether a field is an envelope field now comes from storage/fields.json alone. The header manifest no longer repeats it, and the registry refuses a manifest that declares envelope, as it does a label. Verified by new tests mutation-checked against 4 mutants, the unchanged envelope tests, the full backend suite (1230) and a live look at the editor's envelope area.
<!-- SECTION:FINAL_SUMMARY:END -->
