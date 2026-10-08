---
id: TASK-308
title: >-
  Six copies of the drop-a-file registry, already drifted — one shared discovery
  helper
status: To Do
assignee: []
created_date: '2026-10-08 22:45'
updated_date: '2026-10-08 22:45'
labels:
  - backend
dependencies: []
type: chore
ordinal: 205650
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Chore: six copies of the drop-a-file registry, already drifted. One shared helper before task-104 adds a seventh.** Found by the code-slimmer sweep of 2026-10-08 (D2); file list verified by hand.

**Where the copies are.** Each of these defines its own `_discover`, `_dir_mtime` and `_ensure_fresh`:
- `backend/app/decision/strategies/registry.py`
- `backend/app/rendering/renderers/registry.py`
- `backend/app/ai/tasks/registry.py`
- `backend/app/approvals/actions/registry.py`
- `backend/app/channels/registry.py`
- `backend/app/modules/registry.py`

**How they have drifted.**
- They decide differently what counts as a plugin: two exclude filenames, two look for a marker in the module.
- Only `modules/` scans subfolders, so only it notices a deleted file. The others take the newest modification time among the files present, so deleting a file that was not the newest goes unnoticed until a restart. This is the slimmer's reading of the code, not tested at runtime; uvicorn's `--reload` would hide it for `.py` files.
- `approvals/` reloads modules during a scan. That once made it silently skip `content_ready.py` (fixed 2026-10-08 under task-206: base and registry are now skipped), which is exactly the kind of fix that lands in one copy and not the others.

**What to do.** Add a shared `backend/app/discovery.py` holding the modification-time cache and import-and-collect. Each registry keeps its own rule for what counts as a plugin, so the one-file-per-plugin pattern ADR-162 point 4 asks for stays as it is, and "the same shape" becomes literal rather than copied. The existing registry tests cover the behaviour. Add one test that deleting a non-newest plugin file is noticed.

Do it before task-104 adds the pre-send check registry.
<!-- SECTION:DESCRIPTION:END -->
