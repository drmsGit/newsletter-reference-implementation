# ADR Drift Report

**Date:** 2026-06-22
**Scope:** Full codebase review against all ADRs in `docs/architecture/ADR/`
**Method:** Read-only audit — no fixes applied, only drift flagged

---

## Findings

### ADR-005 — Separate Snapshot State from Recipient Delivery Artifact

**ADR says:** Four distinct concepts must exist — Snapshot State, Decision Resolution, Merge Context, and Delivery Artifact. Merge Context (recipient-level personalization values) must be stored alongside delivery to allow reconstruction.

**Drift:**
- No `MergeContext` model or table exists anywhere in the codebase.
- The delivery service sends a single shared HTML file to all recipients in a `SendInstance`. There is no per-recipient rendering path combining Snapshot + Resolution + Merge Context.
- There is no way to reconstruct what personalization values (e.g. firstname, language, preferred category) were active at send time for a given recipient.

**Files:**
- `backend/app/delivery/service.py:109–165` — single HTML sent to all executions in a send instance
- `backend/app/snapshots/db_models.py` — no `merge_context`, no resolved content metadata, no per-recipient artifact

---

### ADR-030 — Separate Global and Repeatable Structures

**ADR says:** Global structures contain email-level metadata (subject, preheader, header-level info). Repeatable structures contain modular rows and blocks.

**Drift:**
- `CampaignDB` and `VariantDB` have no `subject` or `preheader` fields.
- The `SendInstance.name` field is reused as the email subject at send time.

**Files:**
- `backend/app/campaigns/db_models.py` — no `subject` or `preheader` on `CampaignDB` or `VariantDB`
- `backend/app/delivery/service.py:164` — `subject=send_instance.name`

---

### ADR-040 / ADR-041 — Override Layer / Override Precedence

**ADR says:** Overrides must be stored separately from catalog content and merged during preview or rendering. Resolution order: override value → referenced catalog value → fallback.

**Drift:**
- Overrides (`headline_override`, `body_override`) live inside `ModuleInstanceDB.module_data` as a JSON blob alongside structural config (`module_type`, `position`, etc.).
- No dedicated override table or model exists.
- Structural config and content overrides are indistinguishable programmatically within `module_data`.

**Files:**
- `backend/app/campaigns/db_models.py:45` — `module_data = Column(JSON, nullable=True)`

---

### ADR-051 — Delivery Package Includes More Than HTML

**ADR says:** A delivery package must contain rendered HTML, subject, preheader, campaignId, variantId, snapshotId, delivery metadata, and audience information.

**Drift:**
- `DeliveryProvider.send()` accepts only `(recipient_id, subject, html)`.
- Campaign ID, variant ID, snapshot ID, preheader, and audience info are absent from the delivery payload.

**Files:**
- `backend/app/delivery/providers/base.py:12–18` — `send` method signature
- `backend/app/delivery/service.py:155–162` — call site

---

### ADR-062 — Snapshot Stores Final Render State

**ADR says:** A snapshot must include: final HTML, resolved content data, content references, overrides, metadata, render timestamp, provider/export metadata.

**Drift:**
- `SnapshotDB` stores only: `variant_id`, `recipient_id`, `html_storage_type`, `html_location`, `html_size`, `created_at`.
- Resolved content references, override state, content version IDs, and provider metadata are not stored.
- A snapshot cannot independently reconstruct what content or overrides were active at render time without re-querying mutable tables.

**Files:**
- `backend/app/snapshots/db_models.py` — entire model

---

### ADR-086 — Decision Slots Fail Gracefully

**ADR says:** If no suitable content is found, the Decision Slot may be hidden. If no meaningful content remains after slot resolution, the email must not be sent.

**Drift:**
- Both strategies raise `ValueError("No matching content record found")` when no content is found — this is an uncaught exception, not graceful degradation.
- No concept of "hide the slot" or "skip the module" exists in the rendering layer when a strategy finds no content.
- The rendering fallback renders a visible `<p>No content resolved.</p>` placeholder rather than suppressing the slot.

**Open question:** Should strategies return `None` to signal "no content found", and should the rendering layer suppress the module silently in that case?

**Files:**
- `backend/app/decision/strategies/top_score.py:52` — raises `ValueError`
- `backend/app/decision/strategies/recipient_top_score.py:48` — raises `ValueError`
- `backend/app/rendering/service.py:61–70` — fallback renders visible placeholder

---

### ADR-101 — Provider Capabilities Are Explicit

**ADR says:** Provider capabilities must be explicitly declared — both core (send, delivery status, bounce, complaint) and optional (click tracking, open tracking, etc.).

**Drift:**
- `DeliveryProvider` base class defines only a `send` method.
- No `CAPABILITIES` enum, no `supports_bounce_feedback()` or equivalent interface exists.
- The factory returns a `MockProvider` with no capability contract.
- There is no way for the delivery layer to check whether a provider supports bounce or complaint feedback before use.

**Files:**
- `backend/app/delivery/providers/base.py` — base class
- `backend/app/delivery/providers/factory.py` — factory

---

### ADR-106 — Bounce and Complaint Feedback Is Mandatory

**ADR says:** Bounce and complaint feedback from providers is mandatory infrastructure.

**Drift:**
- Neither the mock provider nor the base class defines a bounce or complaint callback interface.
- The provider event ingestion path (`ingest_provider_event`) accepts generic `event_type` strings with no enforcement that bounce/complaint event types are handled.
- No suppression list exists.
- No delivery gate checks suppression or complaint status before sending.

**Files:**
- `backend/app/delivery/providers/mock.py` — no bounce/complaint interface
- `backend/app/providers/service.py` — generic event ingestion, no enforcement

---

### ADR-110 / ADR-111 / ADR-112 / ADR-113 — Insight Layer and Signals

**ADR-110 says:** The Insight Layer transforms engagement events into reusable signals (recipient, content, composition, audience). It does not make decisions.

**ADR-111 says:** Decision systems consume signals, not raw events.

**ADR-112 says:** Signals must lose influence over time via time-based decay.

**ADR-113 says:** Operational Signals and Historical Signals must be separated.

**Drift — all four ADRs are effectively unimplemented:**
- No `Signal` model or table exists anywhere in the codebase.
- `insight/service.py` applies engagement events directly to `RecipientPreferenceDB` scores — no intermediate signal object is created or stored.
- `RecipientTopScoreStrategy` queries `RecipientPreferenceDB` directly — it consumes mutable preferences, not derived signals.
- No time-based decay logic exists anywhere in the codebase.
- No separation between operational and historical signals exists.

**Files:**
- `backend/app/insight/service.py` — applies delta directly to `RecipientPreferenceDB`
- `backend/app/decision/strategies/recipient_top_score.py:40–56` — queries `RecipientPreferenceDB` directly
- `backend/app/recipients/db_models.py` — `RecipientPreferenceDB` has no timestamp on scores and no decay field

---

### ADR-128 — Version Content for Auditability and Restoration

**ADR says:** Decision resolutions and send-time artifacts must reference the specific `ContentVersion` used, not the live `ContentRecord`. Versions are created on publish/approve actions, not on every save. Versions are immutable.

**Drift:**
1. When a module has a direct `content_record_id` (no decision slot), `render_content_card` reads from the live mutable `ContentRecordDB.title`/`body` fields — not a pinned version.
2. `ContentRecordDB` has no `published_at` field and no version state transition logic; the `body` field is mutable with no guard.
3. `ContentVersionDB.content` uses a different JSON schema (`headline_medium`, `body_medium`, etc.) than `ContentRecordDB` (`title`, `body`). These are two schemas for conceptually the same content with no documented sync path between them.

**Files:**
- `backend/app/rendering/service.py:107–121` — `resolve_renderable_content`, version=None path reads live record
- `backend/app/content/db_models.py:7–13` — `ContentRecordDB` with mutable `body`
- `backend/app/content/db_models.py:33–42` — `ContentVersionDB` with divergent JSON schema

---

## ADRs Not Flagged

The following ADRs appear structurally respected at the current implementation level:

| ADR | Title |
|-----|-------|
| ADR-010 | Newsletter Content Source of Truth |
| ADR-012 | Content Records Represent Communication Units |
| ADR-013 | Content Reference Instead of Content Copy |
| ADR-020 | Campaign Equals Newsletter |
| ADR-021 | Variants Are Human Created Versions |
| ADR-022 | Delivery Type Is Independent From Composition |
| ADR-031 | Newsletter Composition Stores Structure Not Content |
| ADR-050 | Delivery Layer is Part of the Reference Architecture |
| ADR-053 | Maintain Minimal Delivery Execution History |
| ADR-055 | Separate Delivery Execution from Engagement Events |
| ADR-060 | Rendering as Independent Layer |
| ADR-061 | Snapshot Based Final Rendering |
| ADR-083 | Personalization Happens Inside Variants Through Decision Slots |
| ADR-084 | Decision Slots May Resolve One or Multiple Content Records |
| ADR-085 | Decision Resolution Should Be Optionally Explainable |
| ADR-100 | Provider Layer as Send and Feedback Adapter |
| ADR-103 | Provider Events Are Normalized Into Internal Events |
| ADR-121 | Minimal Recipient Model |
