---
id: TASK-349
title: Rename the envelope module from header to envelope
status: Done
assignee:
  - '@claude'
created_date: '2026-10-10 21:17'
updated_date: '2026-10-10 22:18'
labels:
  - backend
  - frontend
dependencies:
  - TASK-301
type: feature
ordinal: 200960
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** The email module that holds the subject and the preheader is code-named header: storage/modules/email/header.json and .html, with its fields marked "envelope": true in storage/fields.json. It renders only a hidden preheader span. The visible logo header decided in task-301 needs that name.

Decided by the user 2026-10-10 (task-301, ADR-193 point 6): rename the envelope module to envelope, so the visible module can be called header.

The final-design pass must settle what ADR-193 left open. Stored data names 'header':
- module rows in campaigns' variants;
- frames frozen in snapshots;
- delivery records that must stay readable as sent (ADR-183).

Either migrate them, or let every reader accept the old name too. Rewriting a frozen record changes what it says was sent, so choose with that in mind.

Also in scope: wherever code, the manager client or the docs say header for the envelope. Grep for module_type 'header' and the envelope module, and see the 2026-10-08 ADR-086 addendum's wording.

First of three build tasks from task-301: this, then the brand profile, then the visible header and footer modules.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The envelope module is called envelope in its manifest, its template and every code path
- [x] #2 Snapshots and delivery records made before the rename still read and reconstruct as sent
- [x] #3 The name header is free for the visible header module
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Final-design pass, 2026-10-10. Decided with the user after a finding: module_html writes data-module-type into every module's HTML (backend/app/rendering/service.py around :372). So rewriting frozen frames would change every sent email's bytes and break ADR-183's hash match. Frozen frames are therefore left exactly as they are, and old frames are read with the old name.

1. Rename the files storage/modules/email/header.json and header.html to envelope.json and envelope.html (git mv). Label: 'Envelope (subject and preheader)'. envelope_module_type() finds it by its envelope fields, so no code names it.
2. Frames, in backend/app/rendering/frame.py:
   - FRAME_VERSION becomes 2, and new frames say which module is their envelope.
   - is_frame() accepts versions 1 and 2. Today it accepts only the current one, so a bump alone would refuse every existing snapshot at send time.
   - In a version-1 email frame, a 'header' entry IS the envelope. Readers translate it for manifest and template lookups only; the HTML keeps data-module-type='header', so old emails render byte-identically.
   - The translation is keyed on the version, so it can never be confused with task-351's visible 'header' (a version-2 frame).
   - Touches what_rendered, render_frame/module_html (template lookup separate from the written name), missing_required_in_frame and _pick_for_slot.
3. Live module rows: migration 0043 renames module_instances.module_type 'header' to 'envelope'. Snapshots are untouched.
4. Tests first:
   - a v2 frame names 'envelope';
   - a v1 frame with 'header' renders data-module-type='header' with the preheader, counts as the envelope in what_rendered, and is still a frame;
   - the required-field check reads it;
   - live rows use 'envelope'.
   Frontend fixtures renamed for honesty.
5. Proof on real data: before the change, 9 sent dev deliveries had a 'header' frame; 1 reconstructed with hash_matches true and 8 already differed (templates changed since). After the change and the migration, the same 1 must still match and the 8 must be unchanged (scratchpad recon_probe.py).
6. Mutation-check, full suites, docs mentions (ADR-086 addendum wording stays dated), commit, CI.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-10, from writing ADR-193 (point 6 hazard, for the final-design pass): the renderer looks up each frozen frame entry's template by module_type (backend/app/rendering/frame.py around :269-278). So after the rename, an OLD frozen 'header' entry would resolve to the NEW visible logo header. Also, what_rendered (frame.py around :190-213) finds the envelope by its manifest attribute, not by name, so an old 'header' entry would then count as meaningful content and defeat the nothing-to-show floor. Either migrate the frozen entries, or map 'header' to the envelope when reading frames made before the rename.

2026-10-10, done (commit 0d2ef14), CI green.

Final-design decisions by the user: first 'migrate everything with a byte-identical proof'. Then, after the finding that module_html writes data-module-type into the HTML, 'leave frozen frames, read the old name'. Recorded in the ADR-193 addendum of 2026-10-10.

What changed:
- envelope.json and envelope.html, relabelled 'Envelope (subject and preheader)'.
- Migration 0043 renamed the live module_instances rows: 11 on dev.
- FRAME_VERSION is 2, and is_frame accepts (1, 2).
- For version-1 email frames, lookup_type and _frame_envelope map 'header' to the envelope for manifest and template lookups, what_rendered and missing_required_in_frame.
- module_html takes template_type, so the HTML keeps the frozen name.

Tests:
- backend/tests/test_envelope_rename.py, 6 tests; 3 failed first, and the 3 old-frame tests guard the change.
- 12 test files and 2 frontend fixtures renamed.
Mutations, each caught: only the current version is a frame, 1 failed; no translation, 2; the floor ignores the old name, 1; module_html ignores template_type, 1.
Suites: backend 1668, vitest 250, Ruff and tsc clean.

Dev-data proof: 9 sent deliveries are frozen with 'header'. The 1 that matched byte-for-byte before still does (hash_matches); the other 8 are unchanged. templates_match flipped for it because the template files changed (best-effort flag).

Living docs updated: Code/channels.md, react-screen-inventory.md, design/CONSTRAINTS.md. Dated records keep 'header'.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The email module holding the subject and preheader is now called envelope (files, live rows via migration 0043), which frees header for the visible logo module. Frozen snapshots are never rewritten: version-1 frames read their header as the envelope but still render under the old name, so every sent email reconstructs exactly as before (decided with the user, ADR-193 addendum). Verified by new tests (mutations caught), the full suites, green CI on 0d2ef14, and real dev deliveries: the one exact match still matches.
<!-- SECTION:FINAL_SUMMARY:END -->
