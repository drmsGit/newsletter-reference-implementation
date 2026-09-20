# React session brief

**Paste the block below into a fresh session.** Written 2026-09-20, at the end
of the backend phase that made the SPA buildable.

**Why a separate session at all.** Not tidiness. The backend session that
prepared this read `backend/app/frontend/router.py` closely for two days — and
that file is the thing the SPA replaces. A session carrying it in context will
port its structure instead of building against the API boundary, which is the
specific failure the 2026-09-19 external review warned about:

> "Build the React frontend against the intended JSON/API boundary rather than
> reproducing the internal structure of the Jinja UI."

The inventory and this brief are the handover. The router is not.

---

## ▶️ Paste this

```
Build the React manager client for the Newsletter Blueprint at
/Users/diedeslembrouck/Projects/newsletter-reference-implementation — a
vendor-neutral reference architecture for email marketing systems (FastAPI
modular monolith + Postgres), published as a playbook + starter package. The
backend is done and the boundary work that had to precede a client is
complete.

READ FIRST, in this order, and nothing else to start:
  1. docs/react-screen-inventory.md   — what to build, what each screen needs,
                                        which three gaps block the first screen
  2. docs/architecture/ADR/ADR-170 — The Manager Client Is a Plain React SPA,
                                     Not Next.js.md   (Accepted)
  3. docs/architecture/ADR/ADR-168 — The Manager SPA Authenticates With Its
                                     Session Cookie.md (Accepted)
  4. docs/architecture/ADR/ADR-171 — Nothing Required to Run This Platform Is
                                     Commercial.md    (Accepted — constrains the
                                     component library)
  5. CLAUDE.md                        — working rules, ADR conventions

DO NOT read backend/app/frontend/router.py. It is the Jinja UI the SPA
replaces, it has a deletion date, and reading it leads to porting its
structure rather than building against the API. Everything in it that was a
backend RULE has already been moved into the services; what remains there is
presentation. If you think you need something from it, the answer is in
docs/react-screen-inventory.md or it is a gap worth logging.

The backend contract is backend/main.py's OpenAPI schema. Generate the typed
client from GET /openapi.json rather than transcribing types by hand —
ADR-170's whole Positive is that the contract cannot silently fork.

Working rules that matter here:
  - Architecture decisions are ADRs, written BEFORE implementing. An accepted
    ADR is not an implementation plan — hold a final-design pass first.
  - State before touching any file: which files change, what the change does,
    which ADR governs it (by number, or "none"), what could break.
  - One question at a time; I decide; nothing goes into an ADR until I have.
  - Don't invent ADR numbers — `ls docs/architecture/ADR/` and take the
    highest.
  - Never `git checkout --` a file with uncommitted work.
  - Never read the .env file. If you need something from it, ask.
  - Run the backend test suite from backend/: venv/bin/python -m pytest tests/ -q
    (635 passing as of 2026-09-20).

Start by confirming the three blocking gaps in the screen inventory are still
open, then propose a build order. Do not scaffold anything until I have agreed
the order.
```

---

## What the new session is walking into

**The backend phase is complete.** Between 2026-09-19 and 2026-09-20:

- **ADR-172** written, accepted and built across seven stages: the JSON plane
  now has a brand boundary in both directions, `brand_id` is a required
  argument on every brand-owned service function, and forgetting it is a
  `TypeError` rather than a leak.
- **Both P1s** from the external code review are closed and mutation-verified.
- **Every category-B rule** — logic that lived only in the Jinja router — has
  moved behind the service boundary: the brand boundary, the approval gate, the
  channel check, the AI spend guards, the content merge, the decision-slot
  config, send-test.
- **ADR-150** amended (`recipients.consent` is brand-scoped), **ADR-170** and
  **ADR-171** accepted, **ADR-162 point 3** built (the `artifact_*` rename,
  done before the typed client so it would not have to be done after).
- **567 → 635 tests.**

**The one open dependency ADR-170 names**: every page view runs four or five
`SELECT`+`UPDATE`+`COMMIT` cycles against the same `auth_sessions` row. A Jinja
page is one request; a React screen is five to fifteen, and this is write
amplification rather than read. **Not a blocker for scaffolding. A blocker for
judging the client under load.** Logged in `docs/backlog.md`.

## Decisions already taken, so the new session does not reopen them

| | |
|---|---|
| **Framework** | React + Vite, SPA. Not Next.js. ADR-170. |
| **Auth** | Session cookie + `X-CSRF-Token` header. Not a bearer token. ADR-168. |
| **Brand** | A person's working brand rides in the session; the SPA sends **no** `X-Brand` header. ADR-166 pt 8 / ADR-172 pt 1. |
| **Approving** | A person may; a machine may not, and is refused at the route. ADR-168 addendum. |
| **Client types** | Generated from the OpenAPI schema. ADR-170. |
| **Licensing** | Nothing required to run the platform may be commercial. ADR-171 — this constrains the component library and has a test. |

## Still open, and genuinely the new session's to decide

- **Which generator** produces the typed client. ADR-170 leaves it open on
  purpose: "a scaffold-time choice that a record made before the scaffold would
  be guessing at".
- **Styling approach and component library.** Constrained by ADR-171 and by the
  brand/theming split already decided in `docs/backlog.md` — the management UI
  gets a small palette applied through CSS custom properties, while email keeps
  a full designer-owned `brand.css`. The outgoing session's recommendation was
  **shadcn/ui on Tailwind**: MIT, copied into the repo rather than depended on,
  which is the posture ADR-171 asks for rather than merely permits. That is a
  recommendation, not a decision.
- **Test tooling.**
- **Whether the design pass happens before or after the scaffold.** The
  outgoing recommendation: a screen inventory (done), then the library, then a
  design pass on **three screens only** — approvals inbox, campaign builder,
  audience — because those three cover every interaction pattern in the app and
  the rest are variations. A design tool asked for forty screens will produce
  forty, most of which will never be built.
