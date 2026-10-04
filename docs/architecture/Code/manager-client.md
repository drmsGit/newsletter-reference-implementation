---
type: code-module
module: manager-client
topic:
  - architecture
  - frontend
created: 2026-10-04
modified: 2026-10-04
---

# manager-client

> Part of [[MOC - System Overview]].

## Purpose

The manager client is **the React single-page app a manager works in**: the
approval inbox, campaigns and the variant editor, content, audiences,
deliveries, monitoring, decision slots and settings. It lives in the top-level
`frontend/` directory — **not** `backend/app/frontend/`, which is the older
Jinja UI documented in [[frontend]]; the two share a name and nothing else.

It owns **no business rules and no data**. Every screen is a consumer of the
JSON API, typed against the backend's OpenAPI schema, so a rule the client
needs is a rule some route already answers — the client never re-derives one
([[ADR-177 — A Field Is Defined Once, Required Per Module]]'s point about the
envelope scan is the standing example).

Decided in [[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]]
(a plain React SPA built with Vite, React Router as a library, session-cookie
auth, a generated API client, MJML staying server-side) and
[[ADR-173 — The Manager Client's Runtime Dependencies]] (react-aria-components
with plain CSS; openapi-typescript, openapi-fetch and TanStack Query; Vitest and
Testing Library; a contract script instead of CI).

## Key files
- `frontend/src/main.tsx` — the one `QueryClient` (refetch on window focus, one
  retry) and `<BrowserRouter basename="/manager">`.
- `frontend/src/App.tsx` — the route table, declared by hand. `/sign-in` is
  public; everything else sits under `RequireSession` and the `Shell`. `/` is
  the approval inbox ([[ADR-169 — Operational Flows Are Sequenced Variants, Not a Canvas]]).
- `frontend/src/api/` — the HTTP layer:
  - `client.ts` — the single openapi-fetch client, same-origin (`baseUrl: ''`),
    plus the middleware that adds `X-CSRF-Token` to every unsafe method
    ([[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]]).
  - `schema.d.ts` — **generated**, never edited: `npm run generate:client`.
  - `session.ts` — `HttpError`, the session query, the two-step sign-in, brand
    switch and sign-out.
  - `resources.ts` — the `keys` object, the `read()` helper and every query and
    mutation hook.
- `frontend/src/screens/` — one file per screen; the variant editor's parts
  (`CatalogueModule`, `SlotSettings`, `Fence`, `Preview`) sit beside it without
  routes of their own.
- `frontend/src/components/` — the shared pieces listed under *Conventions*.
- `frontend/src/shell/` — `Shell` (layout, sign-out), `Nav` (the screens and
  their `g` keys), `BrandSwitcher`.
- `frontend/src/shortcuts/Shortcuts.tsx` — the keyboard shortcut registry.
- `frontend/src/branding.ts` — the product name, from one constant, pending
  task-29.
- `frontend/vite.config.ts` — base path `/manager/`, dev server on port 5173,
  and `API_PREFIXES`, the backend paths the dev server proxies to `:8000`.

## How it talks to the API

- **Types come from the running backend.** `npm run generate:client` reads
  `http://127.0.0.1:8000/openapi.json`; `npm run check:contract` regenerates and
  fails if `schema.d.ts` changed — run it after any API change and commit the
  regenerated file with it.
- **`read()`** (`api/resources.ts`) returns a response's data or throws an
  `HttpError` carrying `status`, `detail` and, for a 422, per-field messages
  (`fields`), which `fieldError()` puts on the form field that caused them.
- **Query keys** are resource-named and carry no brand: switching brand
  invalidates everything instead
  ([[ADR-172 — The Working Brand Is Resolved Once and Carried Into Every Query]]).
- **Writes state the version they edited.** Composer writes go through
  `useComposerWrite`: queued one after another per entity kind, each sending
  `If-Match` with the `updated_at` it read, so a stale save is refused with 409
  rather than overwriting somebody else's (task-110). `SaveState` turns a 409
  into "somebody else changed this — load their version".
- **Session**: a 401 sends the manager to `/sign-in` (`routes/RequireSession.tsx`);
  the CSRF token is re-read with the session on every load.

## Conventions

- **React Aria components, plain CSS** (`index.css`). `DataTable` (a React Aria
  `Table`, no client-side sorting or paging), `Choice` (a `Select`, with an
  optional indent per option), `CategoryChoice` (the category hierarchy, read
  only), `ScreenState` (loading / no permission / not found / failed, said
  once for every screen).
- **Lists are paged on the server** ([[ADR-185 — Lists That Grow With Data Are Paged in One Envelope]]):
  `Pager` and `useOffset()` keep `offset` in the URL; `SearchBox` keeps `q` in
  the URL, runs on Enter, and resets the offset. Filters live in the URL too,
  so a filtered list can be shared or reloaded.
- **Editor fields save on blur** (`AutosaveField`), only when the value changed
  (design pass D1). Typing in a catalogue field writes an override
  ([[ADR-186 — In the Composer an Override Is the Default and a Catalogue Edit Is Explicit]]).
- **Keyboard first.** `useShortcut(keys, description, handler)` registers a key
  while a component is mounted; the overview on `?` reads the same registry,
  so it cannot drift. `g` plus a letter goes to a screen; `/` focuses a list's
  search; holding Alt or Ctrl shows the hints. A key handled locally is listed
  with `handler: null`. Nothing fires while typing in a field.

## Running and testing

- **Dev:** `npm run dev` serves http://localhost:5173/manager/ and proxies API
  paths to the backend on `:8000`. A backend path missing from `API_PREFIXES`
  fails `backend/tests/test_dev_proxy.py`.
- **Tests:** `npm test` (Vitest, jsdom, Testing Library). `src/test-utils.tsx`
  gives `renderWithProviders` (a fresh query client and an in-memory router),
  `stubFetch` — keyed by method and path, and **throwing on any route it was not
  given**, so a screen that starts calling something new fails loudly — plus
  `jsonResponse` and `page()` for the paged envelope.
- **Types:** `npx tsc -b`; `npm run build` runs it before bundling.

## Invariants & decisions
- **The client holds no rule the server does not answer.** Field labels, what is
  required, which module carries the envelope, what a category filter means —
  all come from routes. A client that computed one would be a second copy in
  another language.
- **`schema.d.ts` is generated.** An API change without the regenerated file is
  a contract break that `check:contract` exists to catch.
- **Served under `/manager` while the Jinja UI owns `/`.** When
  `backend/app/frontend/router.py` is deleted, the base path becomes `/` in
  three places: `vite.config.ts`, `main.tsx`'s basename and `SPA_MOUNT` in
  `backend/main.py`.

## ⚠️ Change-impact — if you touch this, also check…
- **A new backend route prefix** → add it to `API_PREFIXES` in `vite.config.ts`
  (the dev-proxy test fails otherwise).
- **Any API model or route change** → `npm run generate:client`, then
  `npm run check:contract`; commit `schema.d.ts` with the backend change.
- **A new shortcut** → register it with `useShortcut`, so the `?` overview lists it.
- **The product name** → `branding.ts` only (task-29).
