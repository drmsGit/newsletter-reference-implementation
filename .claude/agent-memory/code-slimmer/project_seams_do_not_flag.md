---
name: seams-do-not-flag
description: Surfaces in backend/ that are reachable only dynamically or exist as deliberate seam examples — verified live, never report as dead code
metadata:
  type: project
---

These surfaces have zero (or near-zero) static references **by construction**.
Verified live in this repo. Do not report them as unused.

**Why:** the product of this codebase is the seams — an adopter drops in their
own strategy, provider, template or AI adapter. The declared design rule is one
worked example per seam, so an example with no caller is doing its job. A
finding that turns out to be one of these spends the reader's trust.

**How to apply:** before calling anything dead, check this list, then rule out
dynamic discovery with a grep for the *string* name, not the symbol.

| Surface | Discovered by |
|---|---|
| `app/decision/strategies/*.py` | `pkgutil.iter_modules` in `registry.py` — `top_score.py`, `recipient_top_score.py` are the plugin system |
| `storage/email_modules/*.json` + `*.html` | `EMAIL_MODULES_DIR.glob()` in `app/email_modules/registry.py` |
| `app/templates/*.html` | string names in `TemplateResponse(...)` |
| `app/delivery/providers/`, `app/ai/adapters/` | string-keyed factories; `MockProvider` + `MockAIProvider` are deliberate defaults |
| SQLAlchemy models | `Base.metadata.create_all` — no direct import is still a table |
| FastAPI routes | decorator registration |
| `app/auth/policy.py` route table | matched on route template at runtime |

Two more established during the 2026-08-21 delivery/providers sweep:

- **`app/delivery/router.py` (5 JSON routes) and `app/providers/router.py` are
  not dead.** No in-repo caller, no test — but they are the documented public
  API surface (`docs/architecture/Code/delivery.md`) and ADR-142 makes
  machine-triggerable JSON actions a deliberate product feature. Report drift in
  their schemas, never their existence.
- **The JSON routers being unguarded by `enforce_policy` is known and
  deliberate-for-now**, explained in a comment in `main.py` and logged in
  `docs/backlog.md` as the machine-auth P0. See [[backlog-already-logged]].

Genuinely dead, found 2026-08-21 and reported (not yet actioned):
`app/providers/adapters/mock.py` is a 0-byte file, never imported, created empty
in commit `cd13064`. It is *not* an instance of the mock-default pattern.

Related: [[review-only-never-edit]]
