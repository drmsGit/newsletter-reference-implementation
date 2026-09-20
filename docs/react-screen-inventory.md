# React Screen Inventory

**Purpose:** what the manager client has to contain, what each screen needs from
the API, and what is missing. Derived 2026-09-20 from the 27 Jinja screens and
the JSON surface, by the session that spent two days inside both.

**This is an inventory, not a design.** It says what exists and what each screen
needs. It does not say what any of it should look like, how it should be laid
out, or what should be on one page versus two — those are the design pass's
questions and this document deliberately leaves them open.

**Read `docs/react-migration-inventory.md` first if you want the history.** This
one is the forward-looking half.

---

## The cut: what the SPA is for

The Jinja UI has 27 screens. **The SPA does not need all of them**, and deciding
that up front is worth more than any other decision here.

| Group | Screens | In the SPA? |
|---|---|---|
| **Core loop** | campaigns, campaign detail, content, content detail, audience groups, audience detail, deliveries, delivery detail, approvals, approval detail | **Yes.** This is the product. |
| **Supporting** | categories, category detail, decisions, decision slot detail, recipients, recipient detail | **Yes**, but they are read-mostly and can come second. |
| **Administration** | users, roles, integrations, settings | **Probably yes**, and last. Nothing else depends on them and they change rarely. |
| **Sign-in** | login, login verify | **Yes**, and first — nothing is reachable without it. |
| **Diagnostics** | send-test, graph | **Not in the first cut.** Send-test is an operator tool that belongs beside the deployment docs, and the graph is a ~400-line derived visualisation (inventory B25) that nothing depends on. |
| **Sub-pages** | campaign duplicate, variant suggestions, criteria preview | **Not screens.** They are dialogs or panels inside the screens above. |

That is **16 screens in the first cut**, not 27.

---

## Screen by screen

Each row says what the screen needs and whether the API can serve it today.
"Gap" means the endpoint does not exist; the C-numbers refer to
`docs/react-migration-inventory.md`.

### Sign-in — build first

| Screen | Needs | Status |
|---|---|---|
| Sign in | `POST /auth/session/request`, `POST /auth/session/verify` | ✅ built 2026-09-19 |
| Brand switcher (not a screen — a control in the shell) | `POST /ui/brand` equivalent | ❌ **gap C1.** `set_session_brand` has no JSON route. A cookie-authenticated SPA cannot change brand. **Blocks the shell, so it blocks everything.** |

### Core loop

| Screen | Needs | Status |
|---|---|---|
| Campaigns list | `GET /campaigns/` | ✅ |
| Campaign detail | campaign, variants, modules, decision slots, snapshots, sends | ✅ reads exist. **The screen itself is inventory B11** — the largest block of derived state in the Jinja router (overrideability, module limits from the channel manifest, audience counts per channel, providers filtered by channel). None of that is a *rule* — it is presentation the SPA computes for itself — but it is the biggest single design problem in the app. |
| Content list / detail | `GET /content/`, `GET /content/{id}`, `PATCH /content/{id}` | ✅ including the merge semantics (B19) |
| Audience list / detail | groups, members, blocks, `POST .../recalculate` | ✅ ; `GET .../criteria-preview` is **gap C11** and `POST .../bulk-add` by criteria is **gap C12** |
| Deliveries list / detail | send instances, executions | ✅ reads exist. **Planning a send is gap C8** — `prepare_send_from_audience` has one call site and it is the Jinja route. This is the largest capability gap in the product. |
| Approvals list / detail | `GET /approvals/`, `/{id}`, `/{id}/history`, approve, reject | ✅ built 2026-09-20 |

### Supporting

| Screen | Needs | Status |
|---|---|---|
| Categories list / detail | categories, relations, assignments | ✅ mostly; **unassign is gap C5**, **delete relation is gap C10** |
| Decisions list / slot detail | slots, resolutions, `PATCH` config | ✅ including partial edits (B16) |
| Recipients list / detail | `GET /recipients/`, `GET /recipients/{external_id}` | ✅ as of 2026-09-20 (the list route was raising `TypeError`) |

### Administration — last

| Screen | Needs | Status |
|---|---|---|
| Settings | twelve settings/AI service functions | ❌ **gap C2, the big one.** There is no `app/settings/router.py` and no `app/ai/router.py`. The entire settings surface is UI-only. |
| Integrations | create, issue, revoke, grant, deactivate | ❌ **gap C14.** Note `issue_credential` must **not** redirect — the secret exists in one response body only (ADR-166 pt 3), and the SPA needs the same property. |
| Users / roles | user and role administration | ❌ no JSON routes |

---

## What blocks the first screen

In order, and only three things:

1. **C1, the brand switcher.** One route. Without it the shell cannot work and
   every brand-scoped screen is stuck on whatever brand the session landed on.
2. **C8, planning a send.** Without it "deliveries" is a read-only list of sends
   the SPA cannot create, which is most of the product's point.
3. **C2, settings.** Not blocking the core loop; blocking a usable product.

Everything else in the core loop is already reachable.

---

## What the client is generated from

`GET /openapi.json` — FastAPI generates it, and ADR-170's Positive is that "the
contract cannot silently fork, because the client's types are generated from the
schema rather than transcribed from it."

**Two things were renamed before the generator ever ran**, deliberately, because
renaming afterwards means regenerating the client and touching every call site:

- `snapshots.html_*` → `artifact_*` (2026-09-20, ADR-162 point 3)
- nothing else is pending — that was the only known one

**Before generating, check the schema is honest.** Several routes return bare
dicts rather than declared response models (`process-due`, `process-expired`,
`send-test`, `suggest-subject`), so the generator will type them as `object`.
That is a small, mechanical piece of work and it is much cheaper now than later.

---

## Things the SPA must not reimplement

These were moved behind the service boundary between 2026-09-19 and 2026-09-20
precisely so the client does not have to know them. If a screen finds itself
doing any of the following, something has been missed:

- deciding which brand a row belongs to, or filtering by brand
- deciding whether a person may approve a particular held action
- deciding whether a channel may be used
- merging content fields, or deciding whether an empty field means "clear it"
- refusing an AI suggestion before it spends tokens
- deciding whether a send may be fired

The client's job is to show what the API returns and to say what the user did.

## Related

- `docs/react-migration-inventory.md` — what the Jinja router contains
- [[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]]
- [[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]]
- [[ADR-171 — Nothing Required to Run This Platform Is Commercial]] — constrains the component library
