---
type: code-module
module: channels
topic:
  - architecture
  - channels
created: 2026-09-18
modified: 2026-09-18
---

# channels

> Part of [[MOC - System Overview]]. Architecture rationale: [[ADR-160 — Channel Model and Composition]], [[ADR-161 — Channel Execution Shapes]], [[ADR-162 — Channel Rendering and Artifacts]], [[ADR-165 — Core Scope Is Channel-Neutral Content Orchestration]].

## Purpose

The channels module owns **almost nothing, deliberately**: a file-discovered
registry of channel manifests read from `storage/channels/*.json`. ADR-161
point 7 splits the concerns — *provider `.py` = capabilities · module manifest =
fields and limits · channel = an attribute on the variant plus which manifests it
accepts* — leaving **cardinality** as the only genuinely channel-level fact. So a
manifest carries `label`, `description`, `max_modules`, `module_directory`, and
nothing else. Registering a channel is a manifest plus a provider adapter: two
files, no config step.

**"Channel is an attribute on the variant"** means `VariantDB.channel`
(`campaigns/db_models.py:43`), NOT NULL, indexed, **no server default**, never
updated after creation. Not on the campaign — one campaign carries email, push
and social variants. A channel-plan level between campaign and variant was
considered and rejected.

## Key files
- `backend/app/channels/registry.py` (134) — the whole registry: `ChannelManifest`, mtime-cached discovery, `get_channel` / `list_channels` / `is_registered` / `max_modules_for`
- `storage/channels/email.json`, `storage/channels/push.json` — push declares `max_modules: 1`, email `null`
- `backend/app/rendering/renderers/` — `base.py` (101, `RenderedArtifact` + `ChannelRenderer`), `registry.py` (77, pkgutil discovery keyed by `.channel`), `email.py` (49), `push.py` (87)
- `backend/app/modules/registry.py` (223) — manifests keyed `(channel, name)`, directory-per-channel with a declared-channel cross-check, `envelope_module_type`
- `backend/app/delivery/providers/base.py` — the single addressed interface plus `channels: frozenset[str]` and `supports()`
- `backend/scripts/migrate_0010_variant_channel.sql`, `migrate_0011_variant_header_module.sql`, `migrate_0012_drop_variant_envelope_columns.sql`
- `backend/tests/test_channels.py` (2514) — 21 named invariant classes; the class names are the behaviour checklist

## Public surface
`backend/app/channels/registry.py` — six symbols and nothing else:
- `DEFAULT_CHANNEL = "email"` — `:41`
- `ChannelManifest` — `:44`: `name`, `label`, `description`, `max_modules: int | None`, `module_directory`
- `get_channel(name)` — `:104`; `list_channels()` — `:109`; `is_registered(name)` — `:114`; `max_modules_for(name)` — `:125`

**The capability shape is deliberately NOT on the channel manifest** (ADR-161 point 6 — "all capabilities live in the provider file"). The provider declares what it carries: `delivery/providers/base.py:50-55`.

Note `DEFAULT_CHANNEL` exists **twice on purpose** — here and at `recipients/consent.py:33`. [[delivery]] and [[audience]] import the consent one; [[frontend]] imports this one.

## Data model
*No table of its own.* The channel columns live on other modules' tables:
- **`variants.channel`** — `campaigns/db_models.py:43`. No server default in the model *or* the DB: `migrate_0010` adds one only to backfill, then **drops it on purpose** so a caller that forgets a channel fails rather than silently producing an email.
- **`delivery_executions.channel`** — `delivery/db_models.py:87`. A deliberate plan-time denormalisation so the feedback path is not forced through execution → send instance → snapshot → variant.
- **`consent_events.channel`** — part of the `(recipient, brand, channel, purpose)` cell.
- **`recipient_addresses.channel`** — `recipients/db_models.py:106`; `is_primary` is a pin for pick-one channels only, fan-out channels ignore it.
- **`signal_contributions.channel`** — **nullable on purpose**: a declared preference happened on no channel at all, and storing `'email'` for it would invent an engagement.

**What was removed.** `VariantDB` used to carry `subject` and `preheader`. They are gone (`db_models.py:50-58`, ADR-162 point 1: "the variant holds no channel fields at all"). They moved into a **`header` module at position 0** whose manifest flags them `"envelope": true`. Two-step expand/contract: `migrate_0011` creates the module and copies, `migrate_0012` drops the columns, with its verification recorded in the header (9 variants, all 9 had a header module, every value byte-identical). Neither the read half (`rendering/service.py:168-200`) nor the write half (`campaigns/service.py:209-267`) names the module — both find it by the `envelope` flag.

**A push artifact is stored in the row, not on disk** (`snapshots/service.py:97-166`): `render_context["artifact"]`, `html_storage_type="inline"`, no file. The columns are still named `html_*` because they predate channels; the `html_* → artifact_*` rename is ADR-162 point 3's and is not done.

## Depends on →
- **Nothing.** stdlib plus the on-disk `storage/channels/`. Zero intra-app imports — it sits at the bottom of the graph on purpose.

## Depended on by →
- [[campaigns]] — cardinality and membership checks
- [[frontend]] — composer scoping, the send form, channel gates
- [[settings]] — `available_channels` / `channel_available` (lazy import)
- `backend/main.py` — the startup channel log

## Invariants & decisions
- **Registration ≠ availability.** On disk (`is_registered`) and turned on for this deployment (`settings/service.py:168-176`) are two gates, both checked. Deleting files is not how you manage a contract you do not hold.
- **`max_modules_for` fails closed**: an unregistered channel answers **1**, not unbounded — "guessing 'unlimited' for something nobody declared is the wrong direction to be wrong in."
- **Channel is fixed at creation.** `update_variant` does not touch it; duplication copies it.
- **Nothing renders a push as an empty email.** Three layers: `render_variant_html` *raises* when handed a non-email variant; `render_variant` raises for a channel with no renderer rather than falling back; the provider is refused up front if it cannot carry the channel. The comment at `rendering/service.py:83-90` records the actual incident — a push variant produced a 252-character empty shell with no error, and the send-test page mailed it to a real address reporting success.
- **Cardinality is declared, not coded in** — "nothing here knows what push is; it reads a number from a file" (`campaigns/service.py:308-311`). The push renderer deliberately does *not* assert it, because a variant predating a lowered limit is a real state.
- **A module must belong to its variant's channel** — "a dropdown is not a control; a hand-crafted POST never sees it."
- **The channel is derived from the variant, never passed** into `create_module_for_variant`: "a caller that can state the channel is a caller that can state the wrong one."
- **A misfiled *module* manifest stops the process at startup; a malformed *channel* manifest does not** — it is logged and skipped, so a typo in an unused channel cannot take down the ones in use. A deliberate asymmetry.
- **The envelope module sits at position 0 and bypasses the cardinality check** — an envelope module is not a content module, and push declares no envelope fields so is unaffected.
- **The send-instance name becomes a subject only as a fallback and only when the artifact has a body**, so a push payload never acquires a subject.
- **`ConsentDenied` is deliberately not swallowed in the send loop**, unlike `ValueError` — a consent refusal arriving there means the gate and the decision layer disagree about who may be contacted.
- **The readiness verdict was removed, deliberately** (`frontend/router.py:750-757`). A "ready" badge beside a draft asserts a status nobody granted, and `required` belongs to a *module's* manifest variable, not to the record — "a record with no headline cannot fill `single_stack` and fills `cta` perfectly well, so readiness is meaningless until a module is named." ADR-161's catalogue-readiness rider is a candidate filter for decision slots, not a record badge — "and an earlier version of this page made it one."

## ⚠️ Change-impact — adding a third channel, in order
1. **`storage/channels/<name>.json`** — picked up on mtime change.
2. **`storage/modules/<name>/*.json`** — at least one manifest whose declared channel matches its directory, or **startup dies** at `main.py:236`. Flag envelope variables `"envelope": true` and the whole subject machinery works untouched.
3. **A `ChannelRenderer` subclass.** Without it `render_variant` raises and every surface fails loudly rather than emailing something. Choosing `body` vs `fields` decides whether the snapshot goes to a file or inline.
4. **`recipients/consent.py:489` `ADDRESS_KEYS`** — **the easiest thing to miss.** The code will not fail; it falls back to the channel name and reports everyone unaddressable.
5. **A provider adapter** declaring `channels = frozenset({...})`, or rely on the mock. Check `PROVIDER_LABELS` and the from-address set too.
6. **Availability defaults to True** for anything registered — a new channel appears immediately in every picker. Decide before dropping the files.
7. **Consent rows** — nothing grants the new `(brand, channel, purpose)`, so the exclusion stack excludes everyone until consent is recorded. Correct, and will look like a bug.
8. **Content authoring fields are the one place the code is not yet generic**: `_channel_authoring_sections` is manifest-driven, but the route's form parameters are hardcoded per field name (`push_title`, `push_body`, …) and the merge is keyed on the literal `"push"`. A third channel needs new `Form()` parameters and a second branch.
9. If the channel is not "addressed"-shaped (a delegated/audience-sync channel), ADR-161 point 1 says it needs a **second provider interface** — which is not built.

## Known gaps
- **Three stale comments contradict migration 0012** and will mislead the next reader: `campaigns/service.py:141-143`, `renderers/base.py:50-56`, `delivery/service.py:568-569` all still say subject/preheader live on the variant. They describe the pre-0011 world.
- **ADR-162 point 3's artifact *set* is not built** — each renderer returns exactly one artifact. No package hash, no `body_text` alternative, no `multipart/alternative`. The two rendering entry points (`render_variant_html` and `render_variant`) are a transitional state, not a design.
- **Nothing marks a dead push token invalid**, because there is no inbound push adapter (`docs/backlog.md:49`). `AddressabilityDB.status` exists for it; nothing writes it for push, so a dead token stays active, the send reports success and the notification goes nowhere.
- **A personalised subject line is still not possible** (`docs/backlog.md:59`) — a benefit ADR-162 point 1 claims and does not deliver. The override picker requires a module that resolves content; the header module carries `module_data`, so it is refused. Needs an ADR-040/041 decision about whether the override unit is "a module that resolves content" or "a module with declared fields".
- **`modules/router.py:39,47` default `channel="email"`** — the only remaining implicit-email default in a registry caller.
