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

1. ~~**C1, the brand switcher.**~~ ✅ **Closed 2026-09-20**, and it was two routes
   rather than one: the shell also had no way to ask who it is and which brand
   it is in.
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

## Names that lie — read before building a form

**The platform is omni-channel; several names in the schema are older than that
and say "email".** They are accurate about what they carry and wrong about what
they imply, so a client generated from the schema will happily build an
email-only UI. Measured 2026-09-20: twelve email-shaped names reach the schema,
nine of which are FastAPI's auto-named Jinja form bodies and do not matter.
These four do.

| Name | What it looks like | What it is |
|---|---|---|
| `Variant.subject`, `Variant.preheader` (and on `VariantCreate` / `VariantUpdate`) | a variant has a subject line | **It does not.** ADR-162 point 1 moved both into a `header` module and migration 0012 dropped the columns; they are synthesised on read and written through `set_envelope_fields`. A push variant has no envelope at all, so these are null and a Subject input on a push form is a field that cannot be saved. **Ask the channel, not the variant** — `envelope_module_type(channel)` returns `None` when there is nothing to show. |
| `GET /email-modules` | the module catalogue is email-only | It takes a `channel` parameter that **defaults** to email and serves every channel. A module picker built from its name will silently be email-only. |
| `RenderedVariant.html` | rendering produces HTML | For push it produces a field payload. Snapshots already carry this correctly as `artifact_*`; this response model was not renamed with them. |
| `Recipient.email`, `Recipient.email_consent_status` | a recipient has an address and a consent status | A recipient has **addresses per channel** (ADR-163 point 2) and a **consent grid** of `(brand, channel, purpose)`. These two fields are the email cell of each, flattened for convenience. Do not build a single "Consent: yes/no" control from them. |

**The rule underneath all four:** where the SPA needs to know whether something
applies, ask the channel's manifest rather than inferring from a field name.
That is ADR-160/161's whole design — a channel declares what it accepts — and
it is the one thing a generated type cannot tell you.

Renaming these is logged in `docs/backlog.md` and deliberately **not** done
before the client: the four above are documented, and renaming a schema field
after a typed client exists costs more than doing it now only if nobody wrote
this table.

## Related

- `docs/react-migration-inventory.md` — what the Jinja router contains
- [[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]]
- [[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]]
- [[ADR-171 — Nothing Required to Run This Platform Is Commercial]] — constrains the component library
