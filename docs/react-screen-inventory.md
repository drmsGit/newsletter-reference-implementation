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
| Shell context + brand switcher | `GET /auth/session`, `POST /auth/session/brand` | ✅ **built 2026-09-20 (was gap C1).** `GET` returns the user, the working brand and the brands they may switch to; `POST` answers **204 whether or not the switch was accepted**, so a refusal cannot be used to discover brands. Re-read `GET /auth/session` to see where you are. |

### Core loop

| Screen | Needs | Status |
|---|---|---|
| Campaigns list | `GET /campaigns/` | ✅ |
| Campaign detail | campaign, variants, modules, decision slots, snapshots, sends | ✅ reads exist. **The screen itself is inventory B11** — the largest block of derived state in the Jinja router (overrideability, module limits from the channel manifest, audience counts per channel, providers filtered by channel). None of that is a *rule* — it is presentation the SPA computes for itself — but it is the biggest single design problem in the app. |
| Content list / detail | `GET /content/`, `GET /content/{id}`, `PATCH /content/{id}` | ✅ including the merge semantics (B19) |
| Audience list / detail | groups, members, blocks, `POST .../recalculate` | ✅ ; `GET .../criteria-preview` is **gap C11** and `POST .../bulk-add` by criteria is **gap C12** |
| Deliveries list / detail | send instances, executions | ⚠️ **Corrected 2026-09-20: the reads do not serve the screen.** Send instances are reachable only via `GET /delivery/snapshots/{snapshot_id}/send-instances`, and **there is no get-by-id at all** — so neither the list nor the detail can be built without walking campaigns → variants → snapshots client-side, which this document forbids three sections below. Logged as a read gap beside C8. **Planning a send is gap C8** — `prepare_send_from_audience` has one call site and it is the Jinja route. This is the largest capability gap in the product. |
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

**This list said three things and was wrong — there were four.** The fourth was
in the auth spine, which is why nothing above it caught it.

1. ~~**C1, the brand switcher.**~~ ✅ **Closed 2026-09-20**, and it was two routes
   rather than one: the shell also had no way to ask who it is and which brand
   it is in.
2. ~~**C15, the CSRF token after a reload.**~~ ✅ **Closed 2026-09-20.** Found
   while planning the client, not while auditing the API. The token was
   obtainable from exactly one place — the `POST /auth/session/verify` response
   body — and is not a cookie, so a reload, a new tab or a restored session held
   a valid session and **no way to perform a single write**. `GET /auth/session`
   now returns it. Recorded as a dated addendum to
   [[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]], because
   point 2 decides how the token is *compared* and never said how a client
   learns it.
3. **C8, planning a send.** Without it "deliveries" is a read-only list of sends
   the SPA cannot create, which is most of the product's point.
4. **C2, settings.** Not blocking the core loop; blocking a usable product.

Everything else in the core loop is already reachable.

**The lesson worth keeping:** C1, C8 and C2 were all found by reading the API
for what it cannot do. C15 was invisible to that method, because every route
involved existed and worked — what was missing was a sequence a browser
performs and a test suite does not. Auditing the surface does not find it;
walking the client's own lifecycle does.

---

## What the client is generated from

`GET /openapi.json` — FastAPI generates it, and ADR-170's Positive is that "the
contract cannot silently fork, because the client's types are generated from the
schema rather than transcribed from it."

**Renamed before the generator ever ran**, deliberately, because renaming
afterwards means regenerating the client and touching every call site:

- `snapshots.html_*` → `artifact_*` (2026-09-20, ADR-162 point 3)
- `RenderedVariant.html` → `artifact_body` (2026-09-20) — the same rename,
  finished. The snapshot columns went and this response model was missed.
- `GET /email-modules` → `GET /modules` (2026-09-20), with the tag description
  rewritten to say it serves every channel

✅ **The schema honesty pass is done (2026-09-20).** Seven routes returned bare
dicts and now carry declared response models: `process-due`, `process-expired`,
`send-test`, `suggest-subject` — **and the five session routes, which this
document did not list.** Those were the worse omission: `/auth/session/request`
and `/auth/session/verify` also took `payload: dict = Body(...)`, so a generated
client had neither input nor output types for the entire sign-in flow, which is
the one surface the SPA cannot start without.

Verified by diffing `/openapi.json` before and after: twelve schemas added, none
removed, path count unchanged.

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

## Names that lie — read before building a form

**The platform is omni-channel; several names in the schema are older than that
and say "email".** They are accurate about what they carry and wrong about what
they imply, so a client generated from the schema will happily build an
email-only UI. Measured 2026-09-20: twelve email-shaped names reach the schema,
nine of which are FastAPI's auto-named Jinja form bodies and do not matter.
These four did.

**Two of the four were fixed on 2026-09-20 and two were deliberately not.** The
split is not about which names are worst — it is about which are *renames*. The
two that went were renames and cost eight lines. The two that stayed are not
naming problems at all, and calling them one is what kept them on this list.

| Name | What it looks like | What it is |
|---|---|---|
| `Variant.subject`, `Variant.preheader` (and on `VariantCreate` / `VariantUpdate`) | a variant has a subject line | **It does not.** ADR-162 point 1 moved both into a `header` module and migration 0012 dropped the columns; they are synthesised on read and written through `set_envelope_fields`. A push variant has no envelope at all, so these are null and a Subject input on a push form is a field that cannot be saved. **Ask the channel, not the variant** — `envelope_module_type(channel)` returns `None` when there is nothing to show. |
| ~~`GET /email-modules`~~ | the module catalogue is email-only | ✅ **Renamed to `GET /modules`, 2026-09-20.** It takes a `channel` parameter that **defaults** to email and serves every channel. Zero references in the Jinja router, templates or tests — the whole cost was the router prefix, the `BRAND_OWNED` key and three lines of `main.py`. |
| ~~`RenderedVariant.html`~~ | rendering produces HTML | ✅ **Renamed to `artifact_body`, 2026-09-20.** For push it produces a field payload. Snapshots already carried this correctly as `artifact_*`; this response model was not renamed with them, so this was finishing ADR-162 point 3 rather than a new decision. The value it holds was already `artifact.body`. |
| `Recipient.email`, `Recipient.email_consent_status` | a recipient has an address and a consent status | A recipient has **addresses per channel** (ADR-163 point 2) and a **consent grid** of `(brand, channel, purpose)`. These two fields are the email cell of each, flattened for convenience. Do not build a single "Consent: yes/no" control from them. |

**The rule underneath all four:** where the SPA needs to know whether something
applies, ask the channel's manifest rather than inferring from a field name.
That is ADR-160/161's whole design — a channel declares what it accepts — and
it is the one thing a generated type cannot tell you.

**Why the other two stayed, decided 2026-09-20.**

`Variant.subject`/`preheader` is **not a naming problem** and renaming it would
not help. The defect is that an envelope field exists on a channel-neutral type
at all; the honest fix is an envelope shaped by the channel's manifest, which
reopens [[ADR-162 — Channel Rendering and Artifacts]] point 1. That is design
work and it belongs beside campaign detail (inventory B11), not in a rename
pass. It was misfiled here as a name.

`Recipient.email`/`email_consent_status` **already has a decision against it**,
written into `backend/app/recipients/models.py` — an `email` alias was weighed
and rejected as a breaking change, and `address` + `channel` already exists on
the sibling model. Renaming it now would have silently reversed a recorded call.

Both remain documented above, which is what this table is for. The rule
underneath all four is unchanged, and the two survivors are exactly the cases
where it bites hardest.

## Related

- `docs/react-migration-inventory.md` — what the Jinja router contains
- [[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]]
- [[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]]
- [[ADR-171 — Nothing Required to Run This Platform Is Commercial]] — constrains the component library
