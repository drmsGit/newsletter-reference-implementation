---
type: interview-prep
status: open
topic:
  - architecture
  - review
  - baseline
created: 2026-07-04
modified: 2026-07-04
source:
  - claude-baseline-review-2026-07-04
depends_on:
  - "[[ADR-010 — Newsletter Content Source of Truth]]"
  - "[[ADR-011 — Store Reusable Content Only]]"
  - "[[ADR-012 — Content Records Represent Communication Units]]"
  - "[[ADR-013 — Content Reference Instead of Content Copy]]"
  - "[[ADR-020 — Campaign Equals Newsletter]]"
  - "[[ADR-021 — Variants Are Human Created Versions]]"
  - "[[ADR-030 — Separate Global and Repeatable Structures]]"
  - "[[ADR-040 — Introduce Override Layer]]"
  - "[[ADR-093 — Audience Intelligence Is Derived, Not Authoritative]]"
  - "[[ADR-123 — Audience Ownership Depends on Reuse]]"
---

# Interview Prep — Content, Campaigns, Audience

Baseline review generated 2026-07-04 by a fresh read of the codebase (not a diff review). Each item is a checkbox — check it off once discussed, and fill in the **Resolution** line with the decision made (fix now / accept as-is / backlog).

## Content

- [x] **Q1.** Why does content versioning store a free-form JSON blob (`ContentVersionDB.content` with keys like `headline_medium`/`body_medium`) instead of versioning `ContentRecordDB.title`/`body` directly, and why do the two schemas diverge?
    **A:** The version table's JSON schema and the record's flat columns were never reconciled — editors can update `title`/`body` via `update_content_record` without ever creating a version, so "current record" and "latest version" can disagree. `backend/app/content/service.py:271-301`, `db_models.py:6-12,43-51`. Related: [[ADR-012 — Content Records Represent Communication Units]], [[ADR-128 — Version Content for Auditability and Restoration]].
    **Resolution:** act/fix. Divergence is intentional in principle (not every save should version) but the record is missing the actual content fields today, forcing a "create version" step just to enter real content. Redesign: move full CMS content onto `ContentRecordDB.content` (JSON, same shape as `ContentVersionDB.content`); keep `title`/`description` as metadata columns; "create version" becomes a freeze/snapshot action, not a content-entry step. Logged to [[backlog]] (Features).

- [x] **Q2.** `update_content_record_by_id` mutates title/body in place with no version bump — how does this square with ADR-013's requirement that catalog updates propagate safely to active campaigns?
    **A:** Nothing guards it. Rendering reads the live mutable record directly (`rendering/service.py:107-121`), so an in-place edit is immediately visible to any composition referencing that record, with no audit trail of what changed. `backend/app/content/router.py:52-57`.
    **Resolution:** act/fix. Confirmed by re-reading `resolve_content_for_module`/`resolve_renderable_content`: static modules have zero version-awareness (always live), and decision-slot version pinning is optional/manual, never automatic. Need preview-mode (live record, for builder review) vs. send/snapshot-mode (latest frozen `ContentVersionDB` only, error "contains unpublished content" if none exists — no silent draft fallback) with a "publish all" convenience action. Logged to [[backlog]] (Bugs), ranked above the Content Q1 schema redesign since it's a send-correctness issue.

- [x] **Q3.** Why is `list_content_records` an unbounded `.all()` query with no pagination, and what's the risk as the catalog grows?
    **A:** No `limit`/`offset`/cursor param exists (`content/router.py:38-40`); every `GET /content/` call loads and serializes the entire table. Fine for a demo dataset, not for a real catalog.
    **Resolution:** ~~keep in poc~~ → act/fix (reopened during Audience Q6). Realistic POC demo data volumes (recipients, events) mean UX needs to hold up even in the POC. Folded into one standardized cross-module pagination effort — see [[backlog]] (Features).

- [x] **Q4.** Why does `get_content_record_by_id` hand-roll its own Pydantic mapping instead of reusing a shared mapper the rest of the module uses?
    **A:** Inconsistent with `to_content_version`/`to_category_relation` helper pattern elsewhere (`service.py:162-169,260-268`) — this is duplicated ad hoc mapping logic in two places, a maintenance risk if the model gains fields. `router.py:43-49`.
    **Resolution:** act/fix. Extract a shared `to_content_record` mapper, same pattern as `to_content_version`/`to_category_relation`. Logged to [[backlog]] (Bugs), ranked below the send/draft correctness bug — small cleanup, not urgent.

- [x] **Q5.** Two hierarchy mechanisms exist — `CategoryDB.parent_category_id` (inline FK) and `CategoryRelationDB` (many-to-many edge table) — why both, and what happens on conflicting or cyclic data?
    **A:** No cycle check exists in `create_category_relation` (`service.py:172-188`), and nothing keeps `parent_category_id` in sync with `category_relations` rows — a category could have different "parents" in each mechanism simultaneously.
    **Resolution:** act/fix. `CategoryDB.parent_category_id` is leftover from an earlier (wrong) implementation; `CategoryRelationDB` already fully covers it and is what the graph view actually uses. Drop the redundant column, keep only `CategoryRelationDB`. Deliberately no new restrictions: multi-parent children and parent-to-parent relations stay allowed (real business need + room for AI-discovered relations later). Do add a cycle guard against direct/transitive parent_child loops. Logged to [[backlog]] (Bugs).

- [x] **Q5b (addendum).** Should the category model go fully flat — no main/sub distinction, hierarchy/"level" emerging dynamically from relations, usage frequency, and scoring — instead of a human-defined parent/child structure? Or keep parent/child and add a system/AI recommendation layer on top (e.g. "system recommends this become a main category")?
    **A:** [[ADR-080 — Human-governed Taxonomy Before AI Selection]] already decided this: humans define categories/subcategories/relations, AI ranks and recommends *within* that structure, not the other way around. A fully emergent/scored hierarchy would invert that decision. Also, multi-level hierarchies are already achievable via chained `parent_child` edges under the Q5 fix above (a "main category" is simply one with no incoming parent_child edge) — so the flat model's main flexibility promise is largely already available without abandoning the human-governed structure.
    **Resolution:** keep in project — parent/child structure stays, per ADR-080. The AI-recommendation-on-taxonomy idea is real but separate future work; logged to [[backlog]] (Features) tied to Phase 3C (signal layer), not current priority.

- [x] **Q6.** What happens to category assignments / module instances referencing a deleted content record or category?
    **A:** No delete endpoint exists yet, and no FK declares `ondelete="CASCADE"`/`SET NULL`. If a row were ever deleted directly, orphaned `content_category_assignments`/`content_versions`/`module_instances.content_record_id` rows would remain with no integrity enforcement.
    **Resolution:** act/fix (partial) + needs ADR (partial). Deleting something with relations should raise a confirmation error surfacing what it's connected to, not silently cascade — logged to [[backlog]] (Bugs). But the deeper question — can categories/content ever be truly deleted given they carry historical preference/engagement value, or should they only be archived with decaying influence — isn't resolved; logged to [[backlog]] § Needs ADR and cross-referenced into the Phase 3C open question in `docs/playbook-strategy.md` §7.

- [x] **Q7.** Can the same content/category pair be assigned twice, and does that matter for `score`?
    **A:** Yes — `assign_category_to_content` (`service.py:241-257`) has no duplicate check, unlike `audience`'s `add_member`. Calling it twice with different scores creates two rows and duplicate entries in `list_categories_for_content` output.
    **Resolution:** act/fix. No duplicates allowed — reject or upsert on `(content_id, category_id)`. Logged to [[backlog]] (Bugs).

## Campaigns

- [x] **Q1.** Why does `create_campaign` auto-create an initial `VariantDB` inside the same call rather than as a separate explicit step?
    **A:** Operationalizes [[ADR-020 — Campaign Equals Newsletter]] and [[ADR-021 — Variants Are Human Created Versions]] — a campaign with zero variants isn't renderable. Tradeoff: two independent `db.commit()` calls (`campaigns/service.py:45,55`) rather than one transaction, so a failure between them leaves a variant-less campaign.
    **Resolution:** keep in project (auto-creating the initial variant) + act/fix (transaction atomicity). A campaign without a variant can't exist by design, but the two independent commits should be wrapped in one transaction so a mid-failure can't violate that invariant. Logged to [[backlog]] (Bugs).

- [x] **Q2.** `ModuleInstanceDB` has both `content_record_id` and `decision_slot_id` as independent nullable FKs — what stops both (or neither) being set, and what does rendering do?
    **A:** Nothing at DB or Pydantic level enforces mutual exclusivity. `rendering/service.py:196-205` checks `content_record_id` first and silently ignores `decision_slot_id` if both are set. `campaigns/db_models.py:37-53`, `models.py:50-55`.
    **Resolution:** act/fix. Considered a `type`+`id` polymorphic redesign, rejected as a known anti-pattern (loses real FK integrity, complicates joins, not worth it for only 2 reference kinds). Keep the two FK columns, add a mutual-exclusivity constraint (CHECK or validator) instead. Logged to [[backlog]] (Bugs).

- [x] **Q3.** `module_data` is a single untyped JSON blob mixing structural config with content overrides (e.g. `headline_override`) — how does this align with the Override Layer being separate from catalog content?
    **A:** It doesn't cleanly — already known drift (see ADR-drift-report). No schema boundary between structural config and overrides in the same column, no way to query "which modules have an active override" without inspecting arbitrary JSON keys. `campaigns/db_models.py:45`. Related: [[ADR-040 — Introduce Override Layer]], [[ADR-041 — Override Precedence]].
    **Resolution:** act/fix. Revisit ADR-040/041 and design one coherent, scalable override mechanism to replace both this JSON-blob approach and the disconnected `OverrideEventDB` table (see cross-cutting finding in [[MOC - Interview Prep Baseline]]). What reads as an acceptable incremental history to us would look inconsistent/illogical to an outside reviewer. Logged to [[backlog]] (Features), to be resolved together with the matching Overrides-cluster question.

- [x] **Q4.** Why is there no `subject`/`preheader` field on `CampaignDB`/`VariantDB` despite [[ADR-030 — Separate Global and Repeatable Structures]] calling for it?
    **A:** Confirmed gap — `send_instance.name` is reused as the subject at send time (`delivery/service.py:164`). The composition layer has no first-class place to edit subject/preheader.
    **Resolution:** act/fix. Not an oversight, just not reached yet — part of a larger "add missing first-class fields to content/campaigns" effort. Logged to [[backlog]] (Features).

- [x] **Q5.** `create_decision_resolution` accepts an arbitrary `content_record_id`/`content_version_id`/`recipient_id` with no existence validation — what happens on a bad ID?
    **A:** Depends entirely on whether the DB engine enforces FK constraints (often off by default in SQLite) — otherwise silently inserts an orphaned resolution row that later breaks rendering's join-based lookup. `campaigns/service.py:235-257`.
    **Resolution:** act/fix. No orphan row should ever be silently accepted — frequent silent orphans make later cleanup much harder. Validate referenced IDs exist (or enforce FK constraints properly) and error clearly otherwise. Logged to [[backlog]] (Bugs), flagged as possibly systemic across other `create_*` functions.

- [x] **Q6.** No uniqueness constraint on `(variant_id, position)` for modules — what happens with duplicate or gapped positions?
    **A:** Ambiguous render order dependent on undefined secondary sort stability; no reordering endpoint exists for a builder "insert between" UX. `service.py:110-146`.
    **Resolution:** act/fix. Already observed causing real problems in test mode. Positions should never be entered manually — always auto-generated (MAX + 1). Reordering swaps positions between two modules rather than allowing arbitrary values, so duplicates can never exist. Logged to [[backlog]] (Bugs), ranked high given confirmed real-world occurrence.

- [x] **Q7.** Nothing validates that `strategy_config`/`candidate_filter` shape matches what the named `decision_strategy` expects — what happens on mismatch?
    **A:** Not caught until resolution time. `update_decision_slot` blindly overwrites both fields (`service.py:149-164`); strategies defensively `.get()` missing keys, but per the drift report, unmatched candidates used to raise an uncaught `ValueError` rather than fail gracefully (see [[ADR-086 — Decision Slots Fail Gracefully]] — now fixed at the strategy level, see Decision cluster).
    **Resolution:** act/fix. Human-facing input should be as intuitive/mistake-proof as possible: once a strategy is selected, the config/filter structure locks to that strategy's shape — only values are editable, not structure. Logged to [[backlog]] (Features).

## Audience

- [x] **Q1.** Why a dedicated `AudienceGroupDB`/`AudienceGroupMemberDB` table instead of reusing category/preference machinery?
    **A:** Matches [[ADR-123 — Audience Ownership Depends on Reuse]] — manual groups are static, campaign-specific segments (the "Audience Layer" holding pen), decoupled from category/preference machinery which serves content-targeting, not recipient-list purposes. `audience/db_models.py:6-27`.
    **Resolution:** keep in project. Categories/preferences answer "what content should this recipient see" (content ranking); audience groups answer "who receives this send at all" (recipient-list membership) — genuinely different concerns, correctly kept as separate mechanisms per ADR-123's CRM-vs-Audience-Layer boundary.

- [x] **Q2.** `find_by_criteria` lets a preference-score filter directly and permanently materialize into a static group — does that collapse [[ADR-093 — Audience Intelligence Is Derived, Not Authoritative]]'s derived/authoritative distinction?
    **A:** Yes — there's no "suggested, pending validation" intermediate step; `bulk_add_members` (`service.py:125-134`) commits recipients straight into a persisted group from a filtered query. Real drift worth a decision on whether 3B (system-suggested audiences) needs an approval step.
    **Resolution:** act/fix (partial) + keep in project (partial). ADR-093 doesn't actually apply here — this is a manager's own deliberate criteria-based action ("feel of control"), not an AI/automation suggestion, so no approval-step gap exists in the current flow; that layer is correctly deferred to Phase 3B once automation/AI actually proposes audiences. The real, immediate gap is the missing bulk-remove-by-criteria counterpart to bulk-add. Logged to [[backlog]] (Features).

- [x] **Q3.** `add_member`/`bulk_add_members` do a SELECT-then-INSERT with no unique constraint on `(group_id, recipient_id)` — what happens under concurrent adds?
    **A:** TOCTOU race — two concurrent calls for the same pair can both pass the "existing" check before either commits, producing duplicate membership rows. A unique index would make this safe-by-construction. `service.py:54-69,72-85,125-134`.
    **Resolution:** act/fix. Add a DB-level unique constraint on `(group_id, recipient_id)`. Logged to [[backlog]] (Bugs).

- [x] **Q4.** `find_by_criteria`'s preference JOIN has no `.distinct()` — can a recipient with multiple preference rows for the same category appear twice?
    **A:** Yes, in the criteria-preview response — harmless to actual DB state (bulk-add dedupes on its own) but misleading UX in the live preview. `service.py:112-118`.
    **Resolution:** act. Rather than dedup it away, surface *why* a recipient matches (which criteria) in the preview — same underlying need as the Q2 bulk-remove-by-criteria tracking. Needs some design thinking (not fully spec'd), folded into the same [[backlog]] Feature entry as Q2.

- [x] **Q5.** `AudienceGroupDB.name` is case-sensitively unique — what happens on near-duplicate names, and is `IntegrityError` handled?
    **A:** "Newsletter VIPs" and "newsletter vips" both succeed as distinct groups; a true duplicate insert raises an unhandled 500 rather than a clean 409 (`router.py:16-18`, `service.py:15-33`).
    **Resolution:** act/fix. Enforce case-insensitive uniqueness and handle `IntegrityError` with a clean 409. Logged to [[backlog]] (Bugs).

- [x] **Q6.** No pagination anywhere in this module — what's the fan-out risk for a large recipient base?
    **A:** `find_by_criteria`/`list_members` can scan/return the entire recipient table unbounded; the frontend's non-member diff is computed in Python (load-all-and-diff) rather than in SQL — an O(n) pattern per page view. `service.py:7-8,46-51,97-122`.
    **Resolution:** act/fix. One standardized offset/limit pagination mechanism across all data-heavy list endpoints (content, audience/recipients, versions, decision resolutions, events) — no genuinely different approaches needed at this project's scale. Also reopens and supersedes Content Q3. Logged to [[backlog]] (Features).

---
## Related
- [[MOC - Interview Prep Baseline]]
- [[MOC - Content Architecture]]
- [[MOC - Composition Architecture]]
