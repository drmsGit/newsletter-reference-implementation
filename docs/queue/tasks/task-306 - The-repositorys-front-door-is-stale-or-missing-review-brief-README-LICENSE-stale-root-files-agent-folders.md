---
id: TASK-306
title: >-
  The repository's front door is stale or missing: review brief, README,
  LICENSE, stale root files, agent folders
status: To Do
assignee: []
created_date: '2026-10-08 22:27'
updated_date: '2026-10-08 22:46'
labels:
  - docs
dependencies: []
type: docs
ordinal: 200600
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Docs — what an outside reader meets first is stale or missing, and nothing in the queue covered it.** Found by backlog-sequencer run 3 on 2026-10-08 and verified by hand the same day; filed at the user's request, ahead of a possible external code review. None of this is a feature. Its weight is that it shapes how a reviewer spends their time, and the brief currently steers them wrong.

**1. `CODE-REVIEW-BRIEF.md` (repo root) is the most important part, and it misleads.**
- "Prepared 2026-09-19". Its last commit, on 2026-10-05, only changed the product name (task-29).
- It describes "a server-side Jinja UI" (line 10). The React client (ADR-170) is now the surface, and the Jinja UI is frozen (`docs/playbook-strategy.md:393`).
- It says "567 passing" (line 100). Hardcoding a count is what the no-live-counts rule exists to stop; say how to run the suite instead.
- It points to "`docs/backlog.md`, Bugs section" (line 75). That file has been a signpost to the queue since 2026-09-27.
- **Its "Already known — no need to re-find" list (lines 55-75) names items that, by the sequencer's report, have all been fixed since.** These include the sign-in timing oracle (gate 4b closed 2026-09-29), `brand_id=None` meaning every brand, platform-level `recipients.consent`, `delete_brand`'s guard, `record_auth_failure` keying, the append-only audit table (now a database trigger, task-25) and `sending_brand_id`. As written, it asks a reviewer to skip exactly the fixes worth verifying. Check each against `docs/queue/completed/` when rewriting.
- It does not mention CI (ADR-190, `.github/workflows/ci.yml`), the hashed dependency locks (ADR-189), the queue (`docs/queue/`, Backlog.md), or what changed in October (machine principals and `MACHINE_READS`, audit write-time checks, the approval inbox's actions).
- **What the rewrite should hold:**
  - what to review;
  - what is deliberate (keep and refresh lines 36-54);
  - what is **open and known**, from the queue: task-56 (no unsubscribe, no `List-Unsubscribe`, and task-301's missing footer) is the first compliance finding a reviewer would raise; task-237's remainder (the raw SQL strings and the file-serving paths in `backend/main.py`) is exactly what a reviewer hunts;
  - **recently fixed, please verify**, which is the inverse of today's list.

**2. `README.md` is one line (`# Tarrow`).** A reader needs:
- what this is: a reference architecture and implementation, not a product;
- its status: a local proof of concept, with installation and deployment deliberately not started;
- how to run it locally: Docker Compose for Postgres, the venv from the hashed locks, migrations, the two dev servers, and the mock email provider by default;
- where the reasoning lives: the `docs/` Obsidian vault, `docs/architecture/ADR/`, and the playbook.

Prose carries the product name literally (CLAUDE.md), and `scripts/rename_product.py` renames it with the rest.

**3. There is no `LICENSE`, yet CLAUDE.md calls this "open-source".** Choosing a licence is a business decision (`docs/business/decisions/`, not an ADR), and it may need two answers: one for the code, and one for the playbook and docs, which are the published material. It interacts with the provisional, not legally cleared name and with the planned move to the product's own GitHub account (the naming decision's 2026-10-05 entry). The repository is private today, so nothing is exposed without a licence yet. Record the decision, or an explicit deferral with its reason, before anyone outside reads it.

**4. Two stale files at the root.**
- `project_tree.txt`, last changed 2026-06-23, describes a tree that no longer exists.
- `HANDOFF.md` (about 500 lines) carries its own "Stale since 2026-09-20 — do not start a session from this file" banner. It is on `rename_product.py`'s `DATED` list as a record of a date.

Decide for each: delete, regenerate, or move out of the root as a dated record. A reviewer opening the root sees both before the README.

**5. Untracked agent configuration appeared on 2026-10-08:** `.agents/skills/` (nine folders mirroring this repo's `.claude` commands), `.codex/agents/`, and `AGENTS.md`, which is identical to `CLAUDE.md` after its first three lines. Their origin is not recorded in the queue or the docs. Decide whether they ship:
- **Committing them** supports other coding agents. But `AGENTS.md` becomes a second copy of every project rule, so say how it stays in step: generated from `CLAUDE.md`, a symlink, or a test that compares the two.
- **Ignoring them** keeps one source.

Either way, decide before a reviewer clones the repository. Untracked files are invisible to gitleaks and to `rename_product.py`'s scan, which both read tracked files only.

Sequenced as batch R8 (pre-review hygiene) with task-237 and task-238. Not on the beta's critical path under BETA-SCOPE Definition A; its value is to whoever reads the repository next.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 CODE-REVIEW-BRIEF.md describes the system as it is (React client, CI, dependency locks, the queue), hardcodes no test count, lists open known issues from the queue (including task-56 and task-237) and recently fixed items to verify, and points to docs/queue instead of docs/backlog.md
- [ ] #2 README.md states what this is, its status, how to run it locally, and where the docs and ADRs are
- [ ] #3 A licence decision (or a reasoned deferral) is recorded in docs/business/decisions/, and a LICENSE file matches it if one was chosen
- [ ] #4 project_tree.txt and HANDOFF.md are each deleted, regenerated or moved as dated records, by decision
- [ ] #5 .agents/, .codex/ and AGENTS.md are committed or ignored by decision; if committed, how AGENTS.md stays in step with CLAUDE.md is stated
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-08, from the code-slimmer sweep (note-only findings that a reader of the repository meets):
- Stale live counts in the code map. docs/architecture/Code/MOC - System Overview.md:51 says "~14 modules, 70 files, 125 routes", and :140 and :163 say "57 routes in one file" for the Jinja router (83 route decorators on 2026-10-08). The module pages carry route counts too (content.md:41, campaigns.md:41). This breaks the no-live-counts rule. Reword without numbers, for example "the Jinja admin UI, frozen, in one file".
- Two empty package folders a reviewer sees before any explanation: backend/app/automation/ and backend/app/privacy/ hold only .gitkeep. The MOC explains them, but a one-line README.md in each, naming its ADR (automation: ADR-142; privacy: ADR-154, and task-136 for the lifecycle decision), would answer the question where it arises.
- tests/test_jinja_freeze.py says no ADR records the retirement of the Jinja UI. A reviewer will ask; the brief should say how and when Jinja goes, or that it is undecided.
<!-- SECTION:NOTES:END -->
