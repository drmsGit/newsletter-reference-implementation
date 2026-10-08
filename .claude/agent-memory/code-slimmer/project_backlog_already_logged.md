---
name: backlog-already-logged
description: Delivery/provider issues already recorded in the queue (docs/queue/) — do not re-report them as new findings in a code sweep
metadata:
  type: project
---

The queue (`docs/queue/`; `docs/backlog.md` until 2026-09-27) already
holds these. Re-raising them is noise.

**Why:** the backlog is the queue of record and its Done archive carries the
reasoning behind past fixes. A "finding" that is already logged reads as though
the sweep did not check, which costs more trust than it buys.

**How to apply:** grep `docs/queue/tasks/` **and** `docs/queue/completed/` for
the file, symbol or symptom before writing any finding (`backlog search` does
not cover `completed/`). Verify the item is still open — items do get fixed.

Confirmed present as of 2026-08-21:
- **P0-02** — a recipient can be mailed after opting out in `freeze` mode;
  `send_send_instance` never re-checks consent, and the bare `except ValueError`
  at `delivery/service.py:383-387` swallows the decision layer's guard. Bundled
  with replacing that broad catch with typed domain exceptions (was P3-03).
- **P1-05** — `verify_signature` fails **open** when `RESEND_WEBHOOK_SECRET` is
  unset (`providers/adapters/resend.py:65-72`).
- **Machine auth (P0)** — every JSON router is unauthenticated; explicitly
  includes `POST /provider/events` bypassing the signed webhook route.
  Prerequisite for Mode B, ADR-142.
- **P2-04** — the send loop's per-recipient recipient load, per-slot decision
  queries, per-recipient commit and blocking 15s `httpx.post`. Parked inside the
  "Bulk send: batching strategy + send-timing model" 📋 item. **This covers the
  send-loop N+1 — do not report it as a fresh query finding.**
- **`httpx2`** pinned in `requirements.txt` while the code imports `httpx`.
- Concurrency has a 📋 item noting `send_send_instance`'s `with_for_update()` is
  the project's one ad-hoc answer with no convention.

Held by queue tasks as of 2026-10-08 (verify status before relying on it):
- **task-306**: the repository's front door. Root `project_tree.txt`,
  `HANDOFF.md`, README, LICENSE, `CODE-REVIEW-BRIEF.md`, untracked agent
  folders. Does **not** cover `backend/project_tree.txt`.
- **task-237**: raw SQL `text()`/`DDL()` sites, Jinja escaping, `random`,
  `subprocess`, `FileResponse`/`StaticFiles` paths in `main.py`.
- **task-109**: `DecisionSlotDB.max_results` is dead config. **task-114**:
  `outcome_delta` has no producer.
- **task-71**: realistic seed content; the curly-quote CSV is handled by the importer.
- **task-104**: per-task approval form; plans another drop-a-file registry copy.
- **task-246 / task-136**: privacy/erasure unbuilt, which is why `app/privacy/` is empty.
- The `httpx2` pin from 2026-08 is fixed (`requirements.in` names `httpx`).

Related: [[seams-do-not-flag]], [[full-sweep-2026-10-08]]
