---
id: TASK-199
title: two missing DB constraints of a kind already fixed elsewhere.
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
priority: p2
type: bug
ordinal: 506300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug] — P2, two missing DB constraints of a kind already fixed elsewhere.** **(a) `ContentCategoryAssignmentDB` has no unique constraint on `(content_id, category_id)`** (`content/db_models.py:33-38`) — the duplicate check at `content/service.py:366-375` is check-then-insert with no DB backstop, a TOCTOU. The identical race was already closed for audience members (`uq_audience_group_members_group_recipient`) and for `RecipientPreferenceDB`, both Done 2026-07-12; content was missed. *~4 loc; keep the SELECT as the fast path and add `except IntegrityError`.* **(b) `create_content_version` computes `version_number` read-then-insert with no unique constraint** (`content/service.py:411-429`) — two concurrent publishes produce two rows with the same number, after which `resolve_renderable_content`'s `ORDER BY version_number DESC ... .first()` picks one **arbitrarily**, and **ADR-128** makes versions the audit answer to "what exact content did this recipient receive?". Directly comparable to `uq_module_instances_variant_position`, added for the identical ambiguity. *~6 loc.* **Risk on both: `create_all` does not add constraints to an existing table, and duplicates may already exist — run `SELECT content_id, category_id, count(*) FROM content_category_assignments GROUP BY 1,2 HAVING count(*) > 1` first.** **Sequencing on (b):** low risk today because publish is a manual click, but the "publish all" Feature (Features section) would make concurrent publishes routine — do this before that ships, not after. Source: code-slimmer sweep 2026-08-21, Cluster 3 C1 + C5. **DONE 2026-09-14.** Both constraints declared on the models and added to the database by `scripts/migrate_0006_content_unique_constraints.sql` — `create_all` never alters an existing table, so the migration is the real change. **The duplicate check this entry demanded was run first**, as instructed: zero duplicates against 315 assignments and 100 versions, and the row counts are printed by the script's verification block so an empty result can never be mistaken for an empty table. Rehearsed twice on a scratch database cloned from the real content tables, then applied. **(a)** keeps the SELECT as the fast path and answers a lost race identically — a caller cannot tell whether it raced or simply asked twice. **(b)** retries on conflict rather than raising, bounded at three attempts, because a `while True` turns a constraint violation into a hung request. **The tests reproduce the interleaving rather than hoping to hit it:** the racing write is made from a second session inside a patched `commit`, which is precisely the window between the read and the insert. Mutation-checked three ways — the telling one being dropping the constraint from the **database** while the models still declare it, which fails both tests and proves they exercise the constraint rather than the declaration.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 630, section "Done", position 63 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
