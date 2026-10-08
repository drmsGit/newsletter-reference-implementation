---
name: seams-do-not-flag
description: Surfaces in backend/ that are reachable only dynamically or exist as deliberate seam examples — verified live, never report as dead code
metadata:
  type: project
---

These surfaces have zero (or near-zero) static references **by construction**.
Verified live in this repo (table refreshed 2026-10-08). Do not report them as unused.

**Why:** the product of this codebase is the seams — an adopter drops in their
own strategy, provider, template or AI adapter. The declared design rule is one
worked example per seam, so an example with no caller is doing its job. A
finding that turns out to be one of these spends the reader's trust.

**How to apply:** before calling anything dead, check this list, then rule out
dynamic discovery with a grep for the *string* name, not the symbol. Any
AST/Vulture-style pass will list the plugin classes below as unused — expected.

| Surface | Discovered by |
|---|---|
| `app/decision/strategies/*.py` (`TopScoreStrategy`, `RecipientTopScoreStrategy`) | `pkgutil` in its `registry.py` |
| `app/rendering/renderers/*.py` (`EmailRenderer`, `PushRenderer`) | `pkgutil` + `issubclass(ChannelRenderer)` |
| `app/ai/tasks/*.py` | `pkgutil`, a module-level `META: TaskMeta` marks a task |
| `app/approvals/actions/*.py` (`send_fire`, `content_ready`, `ai_subject_apply`) | `pkgutil`, declared action marker |
| `storage/channels/*.json` | `app/channels/registry.py` glob |
| `storage/modules/<channel>/*.json` + `*.html` | `app/modules/registry.py` rglob (was `email_modules/` before 2026-09) |
| `app/templates/*.html` | string names in `TemplateResponse(...)` |
| `app/delivery/providers/`, `app/ai/adapters/` | string-keyed factories; `MockProvider` + `MockAIProvider` are deliberate defaults |
| SQLAlchemy models | `Base.metadata.create_all`; `main.py`'s model imports exist for this |
| FastAPI routes | decorator registration; JSON routers are ADR-142 public surface |
| `app/auth/policy.py` route table | matched on route template at runtime |

Also intentional, confirmed 2026-10-08 — do not flag:
- **`list_all_*` (`campaigns`, `content`, `audience`)** — ADR-172 point 4's
  escape hatch, counted by `tests/test_brand_boundary.py` `SPANNING_FUNCTIONS`.
  Zero callers is acceptable; only the comment claiming callers is stale.
- **`request_login_code`** (`auth/service.py`) — sync form for scripts/tests,
  docstring forbids HTTP use. Test-only by design.
- **Test-only public functions with a documented role** (`audience_arithmetic`,
  `is_consenting`, `channel_affinity`, `set_channel_available`,
  `audit.failure_count`, `audit.events_by_actor`, `approvals list_actions`) —
  API surface or test hooks, not residue.
- **`app/automation/` and `app/privacy/`** — `.gitkeep` only, explained in the
  MOC (accepted-but-unimplemented ADRs; privacy = task-136).
- **`app/database.py` default DSN with a password** — the docker-compose dev
  database, task-288.
- **Ruff B023 at `ai/adapters/mock.py`** — lambda called inside the loop; false positive.
- **Ruff B008** — FastAPI `Depends`/`Query` defaults; false positive.

The 2026-08-21 note about `app/providers/adapters/mock.py` (0-byte) is resolved:
the file is gone.

Related: [[review-only-never-edit]], [[full-sweep-2026-10-08]]
