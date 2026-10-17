---
id: TASK-405
title: >-
  A module dropped in while the manager app is open is offered under its file
  name, then reported as one that does not exist, until a page reload
status: To Do
assignee: []
created_date: '2026-10-17 17:34'
labels:
  - frontend
dependencies: []
type: bug
ordinal: 100400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Surfaced 2026-10-17 by the trailer pre-production checks (a side session's results file, docs/design/trailer/PREPRODUCTION-CHECKS.md section 5.1, with sections 5.0 and 9 item 3): a block dropped into storage/modules/email while the manager app was open, on a scratch database. Re-checked on main (cf3fab0) by reading the code.

**What happens.** Two sources feed the editor's module picker and its module panel, and they go stale on different clocks. The composition's `accepted_module_types` comes from the server on every load (backend/app/campaigns/service.py:1434-1437, from `list_manifests(channel)`). The manifests come from `useModuleManifests` (frontend/src/api/resources.ts:927-937), cached with `staleTime: Infinity`, with the comment "Manifests are files the backend reads at startup. Cached until a page reload". That premise is stale for new files: the modules registry compares the folder's newest modification time on each request and rescans when it changed (backend/app/modules/registry.py:404-420, read through `list_manifests` at :434), so a dropped file is served on the very next request without a restart; the checks confirmed it on the running app, and the strategy registry does the same (backend/app/decision/strategies/registry.py:48-69). Once the composition reloads, the picker lists the new type, but takes its name from the manifest map and falls back to the type id (frontend/src/screens/VariantEditor.tsx:450-453), so it is offered as `quote`, not "Quote". Adding it works. The module's panel then finds no manifest and prints "This channel has no module called quote, so it cannot be edited or rendered." (VariantEditor.tsx:504-514), and the stack row reads `quote · Typed in`. That message is false: the module exists, and the preview renders it. A page reload fixes everything (label, fields, hints).

**Why it matters.** This is exactly the moment the project's "drop a file and it is there" claim is shown (trailer scene S13), and the viewer, or a developer trying it for the first time, reads a failure that is not one. The checks' honest sequence for the film is "files, build, reload the page, then Quote in the list", which is the workaround the film would have to carry. The asymmetry is the cause: ids are fresh, labels and fields are not. The strategy list has the same cache (resources.ts:1616-1621) and fails quietly instead, by simply not offering the new strategy until a reload; the content-fields read too (resources.ts:1218). The AI-task and provider lists live in the settings read, which is not cached that way and refetches on focus, which is why those two appear without a reload.

**A recorded decision is reversed here.** task-334 item 1 (docs/queue/completed) wrote the page-reload boundary into the comments on purpose, "keep in POC", from the 2026-10-09 interview review, Client Q2, on the reasoning that manifests do not change under a session. New evidence: with the drop-a-file story they do. Read that item before changing the cache, and update its comments, which this task makes wrong. No ADR governs the cache.

**Where the fix could land, not decided.** (a) When the composition names a type the cached manifests lack, refetch the manifests once, then the picker and panel agree; the smallest, and the cache stays. (b) Drop `staleTime: Infinity` for manifests and refetch on window focus as the settings read does; simpler, with a larger, repeated read of field lists. (c) Keep the cache and offer only types that have a manifest, which hides a fresh module until a reload and is the worst answer for the story. Say in the task notes whether the strategy list and the content fields get the same treatment.

Not a duplicate: task-334 only changed the comments; TASK-398 is about labels in reasons and help text, not about this.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 With the editor open, a module file dropped into storage/modules/email is offered under its label, and once added shows its fields, without a page reload
- [ ] #2 The message that a channel has no module called X appears only when the server lists no such module
- [ ] #3 The comments that say manifests are read at startup and cached until a reload say what holds now
- [ ] #4 A client test: a composition that names a type the cached manifests lack leads to a refetch, then the label and fields show; it fails without the fix
- [ ] #5 The task notes say whether the strategy list and the content fields get the same treatment, and why
<!-- AC:END -->
