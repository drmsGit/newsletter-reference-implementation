---
type: code-module
module: frontend
topic:
  - architecture
  - frontend
created: 2026-07-27
modified: 2026-07-27
---

# frontend

> Part of [[MOC - System Overview]].

## Purpose

The frontend module owns **the server-rendered admin UI** — the Jinja/Bootstrap
pages a manager uses to drive everything: author content, compose campaigns, run
decisions, build audiences, plan and fire sends. It is **one file with 57
routes** (`frontend/router.py`), each a thin handler that calls a service
function and renders (or redirects to) a template. It holds **no business logic
and no database** of its own — it's the presentation layer over every other
module, using the **post/redirect/get** pattern throughout.

Because per-route pages would be 57 notes that rot, this page is a **route index
table grouped by feature** instead. The source of truth is the decorators in
`frontend/router.py`; the JSON API equivalents are in Swagger (`/docs`).

## Key files
- `backend/app/frontend/router.py` — all 57 UI routes (~59 functions)
- `backend/app/templates/*.html` — the Jinja templates they render

## Data model
**None.** Reads/writes go through the other modules' services.

## Depends on →
**Every other module.** `frontend` imports [[audience]], [[campaigns]], [[content]], [[decision]], [[delivery]], [[email_modules]], [[insight]], [[overrides]], [[recipients]], [[rendering]], [[settings]], [[snapshots]] — it's the top of the dependency graph (nothing depends on it). See [[Module dependency map]].

## Depended on by →
*Nothing* — it's the presentation leaf.

---

## Route index

`GET` routes render a page; `POST` routes mutate then redirect (post/redirect/get). `{x}` = path param.

### Home & platform
| Method | Path | Does |
|---|---|---|
| GET | `/` | Dashboard / landing |
| GET · POST | `/ui/settings` | View / update runtime config ([[settings]]) |
| GET · POST | `/ui/send-test` | Single-recipient live send test (pick provider, optionally render a real variant) → [[delivery]] |

### Recipients
| Method | Path | Does |
|---|---|---|
| GET | `/ui/recipients` | List recipients (with consent badge) |
| GET | `/ui/recipients/{recipient_id}` | Recipient detail + live per-category signals |

### Content
| Method | Path | Does |
|---|---|---|
| GET | `/ui/content` | List content records |
| GET | `/ui/content/{id}` | Content detail |
| POST | `/ui/content` | Create record |
| POST | `/ui/content/{id}/edit` | Edit record |
| POST | `/ui/content/{id}/delete` | Delete (tiered guard) |
| POST | `/ui/content/{id}/publish-version` | Freeze a content version |
| POST | `/ui/content/{id}/assign-category` | Assign a category (with score) |
| POST | `/ui/content/{id}/categories/{assignment_id}/delete` | Remove a category assignment |

### Categories & graph
| Method | Path | Does |
|---|---|---|
| GET | `/ui/categories` | List categories |
| GET | `/ui/categories/{id}` | Category detail |
| POST | `/ui/categories` | Create category |
| POST | `/ui/categories/{id}/delete` | Delete category |
| POST | `/ui/categories/relations` | Add a parent/child relation (cycle-guarded) |
| POST | `/ui/categories/{id}/relations/{relation_id}/delete` | Remove a relation |
| GET | `/ui/graph` | The category graph visualization |

### Campaigns & composition
| Method | Path | Does |
|---|---|---|
| GET | `/ui/campaigns` | List campaigns |
| GET | `/ui/campaigns/{id}` | Campaign detail (variants, modules, slots, overrides, snapshots, prepare-send) |
| POST | `/ui/campaigns` | Create campaign |
| POST | `/ui/campaigns/{id}/variants` | Add variant |
| POST | `/ui/campaigns/{id}/variants/{vid}/edit` | Edit variant (subject/preheader) |
| POST | `/ui/campaigns/{id}/variants/{vid}/modules` | Add module instance |
| POST | `/ui/campaigns/{id}/variants/{vid}/modules/{mid}/edit` | Edit module (`module_data`) |
| POST | `/ui/campaigns/{id}/variants/{vid}/modules/{mid}/delete` | Remove module |
| POST | `/ui/campaigns/{id}/variants/{vid}/modules/{mid}/move` | Reorder module |
| POST | `/ui/campaigns/{id}/variants/{vid}/decision-slots` | Add a decision slot |
| POST | `/ui/decisions/slots/{slot_id}/edit` | Edit a slot's strategy/config (validated) |
| POST | `/ui/campaigns/{id}/variants/{vid}/overrides` | Add a field override → [[overrides]] |
| POST | `/ui/campaigns/{id}/overrides/{oid}/reset` | Reset an override |
| POST | `/ui/campaigns/{id}/variants/{vid}/snapshots` | Create a snapshot → [[snapshots]] |

### Decisions
| Method | Path | Does |
|---|---|---|
| GET | `/ui/decisions` | List decision slots / strategies |
| GET | `/ui/decisions/slots/{id}` | Slot detail + resolutions |

### Deliveries (plan & fire)
| Method | Path | Does |
|---|---|---|
| POST | `/ui/campaigns/{id}/snapshots/{sid}/send-instances` | **Plan a send** (audience → provider → timing) → [[delivery]] `prepare_send_from_audience` |
| POST | `/ui/send-instances/{sid}/send` | **Fire a send** → [[delivery]] `send_send_instance` |
| POST | `/ui/deliveries/process-due` | Fire all due scheduled sends (the scheduler seam) |
| GET | `/ui/deliveries` | List sends |
| GET | `/ui/deliveries/send-instances/{sid}` | Send detail (audience, provider, executions, trigger) |

### Audience groups
| Method | Path | Does |
|---|---|---|
| GET | `/ui/audience-groups` | List groups (net recipient counts) |
| GET | `/ui/audience-groups/{id}` | Group detail (rule-block stack + pins + net preview) |
| POST | `/ui/audience-groups` | Create group |
| POST | `/ui/audience-groups/{id}/edit` | Edit group |
| POST | `/ui/audience-groups/{id}/delete` | Delete group (clears blocks) |
| POST | `/ui/audience-groups/{id}/members` | Pin a recipient |
| POST | `/ui/audience-groups/{id}/members/{rid}/remove` | Unpin |
| GET | `/ui/audience-groups/{id}/criteria-preview` | Live count for a criteria payload |
| POST | `/ui/audience-groups/{id}/bulk-add` | Bulk-add by criteria |
| POST | `/ui/audience-groups/{id}/blocks` | Add an include/exclude rule block |
| POST | `/ui/audience-groups/{id}/blocks/{bid}/edit` | Edit a block |
| POST | `/ui/audience-groups/{id}/blocks/{bid}/delete` | Delete a block |
| POST | `/ui/campaigns/{id}/suggest-audience` | Seed a suggested group from a campaign's content |
| POST | `/ui/audience-groups/{id}/recalculate` | Re-derive suggested blocks (delta-only) |

## Invariants & decisions
- **Presentation only** — every route delegates to a service; no business logic here. If logic creeps in, it belongs in the owning module.
- **Post/redirect/get everywhere** — POSTs redirect (often with `?error=`/`?notice=`) so a refresh doesn't re-submit.
- **This table is hand-curated** (grouping + descriptions need human context), unlike Swagger which is generated. *Option (noted, not built): extend `gen_module_map.py` to also emit the raw route list for cross-checking, keeping the descriptions curated.*

## ⚠️ Change-impact — if you touch this, also check…
- **Adding/moving a route** → update this table (it can't auto-detect drift). The path is the anchor other pages link to (e.g. the plan/fire routes referenced from [[delivery]] and [[Flow - Send a campaign]]).
- **A service signature this calls** → 57 handlers are thin wrappers; a changed service function surfaces here first.
- **Templates in `backend/app/templates/`** → renamed templates break the matching route silently.
