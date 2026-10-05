---
id: TASK-218
title: >-
  Hiding an element within a module: a manager leaves out e.g. the button or the
  body text of one module in a variant
status: Done
assignee:
  - '@claude'
created_date: '2026-09-27 14:20'
updated_date: '2026-10-05 21:31'
labels:
  - backend
  - frontend
  - needs-adr
dependencies: []
priority: p2
type: feature
ordinal: 200375
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**What this is (corrected 2026-10-05 with the user).** A manager composing a variant hides individual **elements inside a module** — for example Image Left with image, headline and button but no body text — so one module type gives several layouts, instead of building tens or hundreds of near-identical module types. It is **not** hiding a whole module.

**Where it comes from.** The user's brief for the editor, quoted in [[Manager Workflow - design interview]] (Cluster 3, around lines 1015-1040): *"options to override the content or to hide elements (like no button, no headline)"*. The interview named "hiding elements" in the editor's scope and flagged the open question for the editor interview: whether "no button" is expressible by clearing a field "depends on each template, which makes it a template convention rather than a guarantee". The [[Variant Editor - design interview]] never took it up; it covers only automatic hiding (a slot with nothing to show, ADR-086; a slot whose pick is already in the email, around line 399). When this gap was filed on 2026-09-27 it was worded as "`ModuleInstanceDB` has no visibility flag", which reads as hiding a whole module — a misreading of its own source, corrected here.

**What exists today, partly by accident** (verified 2026-10-05):
- The email templates guard optional parts with `{% if %}`: in `storage/modules/email/img_left.html` the image, body text and button render only when filled (`img_right`, `single_stack`, `hero` likewise). Leaving the body empty already gives "image, headline, button".
- The headline is unconditional and `required` in the manifest (`img_left.json`), so "no headline" is impossible.
- It is a per-template habit, nothing guarantees it, and a module type added later may not follow it.
- There is no way to say "hidden" as distinct from "empty": for a catalogue-bound module, emptying a field is an override with an empty value (`backend/app/overrides/service.py`, `set_override_fields`), which reads as missing copy, not as a decision — and whether the editor accepts an empty override is unverified.

**Needs a design interview before any build** (one question at a time, with the user). Likely questions: what an element is (one field, or a group such as button = label + link); who declares what may be hidden (the module manifest, so the template guarantees it — ADR-177 territory); whether a required field (the headline) may be hidden, and what the send-time required-field check (ADR-174 point 3) and slot candidacy then make of it; where the choice lives (on the module in the variant, or in the override); whether it applies to slot-filled modules; how the editor and preview show a hidden element; whether it copies with duplication.

Related: [[ADR-177 — A Field Is Defined Once, Required Per Module]], [[ADR-186 — In the Composer an Override Is the Default and a Catalogue Edit Is Explicit]], [[ADR-041 — Override Precedence]], [[ADR-086 — Decision Slots Fail Gracefully]].
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.

2026-10-05: rewritten with the user — the entry had turned 'hiding elements (no button, no headline)' into 'no visibility flag on a module'. Design interview started the same day.

Design interview held 2026-10-05 with the user, one question at a time:
Q1 each field is an element (no groups; a link may serve the button or the image).
Q2 the manifest marks fields 'hideable'; the manager's choice is a list on the module in the variant (toggle per hideable field), kept on re-bind, copied on duplicate; human only for now.
Q3 a hidden field reaches the template as empty, removed before the MJML compile (ADR-131); every hideable field sits inside an {% if %} that mentions it, checked at load. The user's detail: the hidden field is the visible one (button_label); the guard may keep 'button_label and button_url'.
Q4 required means required when shown: the send check, slot candidacy and the picker's note skip a hidden field.
Q5 hiding keeps the value; the editor folds a hidden field; the frame records what was hidden.
Q6 starting set: image_url, headline_medium, body_medium, button_label in Image Left/Right and Single Stack; headline_hero, button_label_hero in Hero Banner; none elsewhere.
Decided in the final design pass (not asked): its own people-only route PUT /campaigns/modules/{id}/hidden-fields; the load-time check reads the template with Jinja's parser; one required-when-shown helper for every check; old frames without the key mean none hidden.
Recorded: ADR-187, docs/architecture/interview-prep/Element Hiding - final design pass.md, playbook 2026-10-05. Build tasks: task-289 (manifests and templates), task-290 (the module's hidden fields, backend), task-291 (the editor).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Designed with the user (task-218 corrected from 'hide a module' to hiding fields within a module): each field is an element; the manifest marks hideable fields; the manager's choice is a hidden-fields list on the module in the variant, human only; a hidden field reaches the template as empty, removed before the MJML compile, with every hideable field guarded (an 'and' conjunct of its guard, checked at load); required means required when shown; hiding keeps the value. Recorded in ADR-187, addenda to ADR-177 and ADR-174, the Element Hiding final design pass and the playbook. Build tasks task-289, task-290, task-291.
<!-- SECTION:FINAL_SUMMARY:END -->
