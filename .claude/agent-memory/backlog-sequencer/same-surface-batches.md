---
name: same-surface-batches
description: File-level batches, verified against the tree 2026-09-12. Line counts measured, not quoted.
metadata:
  type: project
---

Measured line counts: `app/frontend/router.py` 2927, `app/auth/service.py` 623,
`app/audience/service.py` 503, `app/delivery/service.py` 433, `app/auth/router.py` 281,
`app/providers/service.py` 209, `app/snapshots/service.py` 169, `app/insight/service.py` 169,
`app/decision/service.py` 99.

**B1 — `app/delivery/service.py`, one function.** P0 consent gate, P1 parent-status
aggregation, typed exceptions replacing `except ValueError` (:383-387), per-delivery
artifact package, N+1 batching. All inside `send_send_instance()` :296-433.
Crosses ADR-163 / ADR-162 / ADR-161.

**B2 — `app/auth/` cluster.** Gate 4b disclosure (`service.py:310-311` -> `router.py:63-76`),
`+`-address quoting (`router.py:79,107-112`), enumeration oracle (`router.py:51-81`, 0 loc
after 4b), `auth_enforced` default (`dependencies.py`), CSRF, login-code rate limiting,
double session resolution (`main.py:227` + `dependencies.py:94`), session/login-code
cleanup (ADR-154), `current_user` 3-loc deletion. Gates 4 and 4b in one load.

**B3 — `app/frontend/router.py` (2927 loc, busiest file).** CSRF tokens across 43 write
routes, signal-weight write (:220) and display (:81), pagination, subject/preheader
handling, image picker, AI progress. The CSRF pass is the reason to batch: it touches
every write route once.

**B4 — recipient/consent surface (ADR-163 migration footprint, 10 files).**
`app/recipients/{models,service,db_models,router}.py`, `app/decision/service.py`,
`app/audience/service.py`, `app/templates/{recipients,recipient_detail}.html`,
`scripts/seed_demo_data.py`, `scripts/reset_all_data.sql`.

**B5 — snapshot/artifact surface.** `app/snapshots/{service,models,db_models}.py` +
seed script. Atomicity bug + `html_*` -> `artifact_*` + storage medium + `render_context`
gaps (overrides, merge-context). Crosses ADR-062 / ADR-005 / ADR-162.

**B6 — settings grid.** `app/settings/service.py`, `app/insight/{service,signals}.py`,
`app/frontend/router.py`, `app/templates/settings.html`. Weight no-op (+3 loc), half-life,
channel weights (ADR-164 §10), spend cap, model selection.

**B7 — providers surface.** `app/providers/{router,service}.py` + adapters.
Unauthenticated `POST /provider/events` (:17-32), webhook fail-open, click attribution
(`service.py:100-139`), aggregate-feedback table (ADR-164 §4). Crosses ADR-103's
addendum boundary (per-recipient events only).

**B8 — `app/database.py`, six lines, two backlog items from different scopes.**
The hard-coded password (in-beta, BETA-SCOPE's deployment-bundle exception) and the
engine-at-import defect (out-of-beta, the test-DB Needs-ADR) are lines 4 and 6 of the
same file. Batch regardless of scope; touching it twice is the only wrong answer.
`requirements.txt` `httpx2` and the `Secure` cookie flag ride along as the same
"publishable repo" pass.

---

# Run 2 batches — 2026-09-27

Measured 2026-09-27: `app/frontend/router.py` **4,415** loc (was 2,927 on
2026-09-12 — it grew ~1,500 lines while carrying a deletion date).

**M1 — the content-catalogue field model migration.** ONE decision, ONE
migration, ONE release. The human suspected this and it is correct — 1.8, 2.4,
2.8, 2.9 and 2.10 are five decisions and one migration.
Members: VE-3 (`content/service.py:101`), VE-10 (create `storage/fields.json`;
collapse `CONTENT_FIELD_GROUPS` + `scripts/import_content_csv.py:33-41`),
VE-11 (`modules/router.py:10` `ModuleVariableOut`), VE-13 (`rendering/service.py:37`
`_RICH_TEXT_FIELD`), VE-14 (`rendering/service.py:162` `cms` boolean too coarse),
VE-2 (`storage/modules/email/hero.json` + data migration, L362), VE-9's `type`
descriptor, Feature **L176** (email's six fields hardcoded in `content.html`,
`content_detail.html` and both routes), MW Cluster 2's maintenance item.
Crosses: no existing ADR — it needs the new one. Files: `content/service.py`,
`content/models.py`, `modules/router.py`, `rendering/service.py`, `storage/`,
`scripts/import_content_csv.py`, two templates, `frontend/router.py`.

**M2 — override integrity.** VE-15/20 (refuse override on slot-bound module,
`overrides/service.py`, `rendering/service.py:286`), VE-16/28 (duplication copies
the configuration half, `campaigns/duplication.py`), VE-19 (`reason` as code,
`overrides/db_models.py`), VE-17 (reach-count query, new).
Crosses the unwritten edit-vs-override ADR. **VE-15/20 must precede VE-4/5.**

**M3 — response-model under-exposure sweep.** MW Cluster 5 names this as a
pattern and explicitly says "worth a sweep rather than three one-line fixes":
`ModuleVariableOut` drops `label`/`envelope`; `PendingActionDetail` drops
`subject_type`/`subject_id` (MW-6); `SendInstance` exposes 8 of 15 columns and
none of the three counts. Add VE-23 (render response carries no per-module state)
and MW-13 (`resolve_audience` discards its arithmetic).
**`ModuleVariableOut` is in both M1 and M3** — so M3 should follow M1.
Phase 0's schema-honesty pass caught bare dicts and missed under-exposure.

**M4 — the list-route contract.** MW-5 (filtering + pagination everywhere),
MW-7 (approvals filters), MW-10 (resolutions, 96k rows), Feature L242,
MW-18 (campaign state view needs it). One envelope, applied once, to content,
campaigns, audiences, recipients, approvals, resolutions.

**M5 — `campaigns/duplication.py`.** VE-27 (`duplicate_variant` — the *primary*
creation action per 5.1, and it does not exist), VE-16/28 (overrides),
VE-29 (context-sensitive `content_mode` default, `KEEP` within a campaign),
MW-11 (`duplicate_campaign` must accept a facet-value mapping).
Crosses the facet ADR (175) and the unwritten override ADR.

**M6 — `audience/service.py` + one router.** MW-12 (no JSON route for
suggestion, though `suggest_include_blocks_for_campaign`,
`campaign_category_scores`, `create_suggested_group_for_campaign` and
`recalculate_suggested_blocks` all exist), MW-13 (arithmetic),
MW-15 (channel defaults to email — bug), MW-16 (delivery-history criteria),
plus Cluster 5's "always recalculate, `freeze` is the mode that should never be
used" (both the function default and the column default currently say `freeze`),
plus the Q2 pin-vs-exclude reversal. Crosses ADR-093.

**M7 — `campaigns/db_models.py` + `campaigns/service.py`.** VE-7/8 (optimistic
concurrency + actor, L360), VE-22 (version marker — *a marker, not a render pin*),
VE-25 (`variants.status` accepts any string, `campaigns/service.py:191`),
VE-4/5 (`max_results` + ranked picks, `db_models.py:115` and :135).
One schema pass. **VE-22 and VE-7 are adjacent, not the same.**

**M8 — the asset subsystem + the snapshot storage medium.** L364 says to answer
them together; `SnapshotDB` already has `artifact_storage_type` /
`artifact_location` / `artifact_size`, and `snapshots/service.py:106` names the
open question. Also folds in the long-standing snapshot atomicity P2. Crosses
ADR-162 §3, ADR-101, and the new "nothing hard-deleted" Needs-ADR.

**Still valid from run 1:** B2 (`app/auth/`), B4 (recipient/consent), B6
(settings grid — now gated on C2), B7 (providers).

---

# Run 3 batches — 2026-10-08

Measured 2026-10-08: `frontend/router.py` 3,982 loc (frozen, shrinking);
`audience/service.py` 1,581; `campaigns/service.py` 1,386; `content/service.py`
1,384; `auth/service.py` 1,318; `delivery/service.py` 1,301. B1-B8 and M1-M8 are
largely closed; do not reuse them without checking.

- **R1 recipient-facing frame + first-send compliance**: task-56 (public routes,
  consent write, `delivery/providers/{base,resend,mock}.py` headers), task-301
  (frame in `rendering/service.py`, per-brand profile), task-108 (decorative
  marker), task-94 (`brand.css` per brand, `rendering/service.py:36-44`).
  task-112 only for the logo. Crosses ADR-169, ADR-163, ADR-086 addendum, ADR-160 p6.
- **R2 decision resolution**: task-109, task-220, task-234 (+ task-126 B, task-87,
  task-83). `campaigns/db_models.py`, `rendering/service.py` `resolve_content_for_module`,
  `decision/`. Crosses ADR-083/086/176.
- **R3 overrides**: task-225, task-226, task-60 (`overrides/service.py:37-72`),
  task-114 + task-130 (same trust-loop question). Crosses ADR-040/041/178/186.
- **R4 consent / suppression / recipient data**: task-135, task-231, task-246,
  task-128, task-104 points 2-3. `recipients/{db_models,consent,service,router}.py`,
  `delivery/exclusion.py` stage 3, audience exclude kind. Crosses ADR-163/154/176.
- **R5 data lifecycle**: task-117, task-136, task-85, ADR-153 retention, ADR-154
  erasure (`app/privacy/` empty).
- **R6 AI layer `app/ai/`**: task-102 (`ai/service.py:89`), task-74, task-75,
  task-77, task-124(c) spend-cap TOCTOU, task-125, task-68; task-100 when React
  gets an Assistive action. Crosses ADR-140/141/144.
- **R7 test harness**: task-304 (`tests/test_consent_gates.py` fixture), task-302
  (Playwright), task-106 (benchmark + query-count smoke tests).
- **R8 pre-review hygiene**: task-237 remainder, task-238, plus orphans with no
  task: gradual mypy, one-off Vulture (task-105 deferred both), README (one line),
  no LICENSE, stale CODE-REVIEW-BRIEF.md, root `project_tree.txt`.
- **R9 data-in interview**: task-119, task-294, task-120, task-84, task-128.
