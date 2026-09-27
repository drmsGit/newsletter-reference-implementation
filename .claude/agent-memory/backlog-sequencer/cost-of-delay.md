---
name: cost-of-delay
description: Rises / Flat / Decays classification of backlog items, 2026-09-12. Rises entries name why and who pays.
metadata:
  type: project
---

## Rises

| Item | Why it rises | Who pays the tax |
|---|---|---|
| Consent-events + addressability migration (ADR-163 §1/§2) | Every call site added against `consent_status` must be migrated; 10 files already | P0 fix, suppression model, provider contact sync, transactional sends, drift endpoint, React recipient screens |
| `SignalContributionDB.channel` (ADR-164 §9) | Contributions are append-only, decay-on-read. Rows written before the column exists can never be truthfully backfilled | Channel weights, any per-channel signal analysis, DWH export schema |
| Artifact rename + subject/preheader to module fields (ADR-162 §1/§3) | Two schemas diverge the longer they coexist; a bespoke subject-override built first is wasted work ADR-162 gives free | Mode-A work, snapshot build, snapshot atomicity fix, React variant screens |
| Gate 3 machine auth | A constraint before the feature that makes its race routine; every JSON route added meanwhile is one more to retrofit, and a second client built against an open API bakes it in | React SPA, Mode B, every new router |
| `app/database.py` engine-at-import | Every fix landed without a clean test runtime is hand-verified; the P0/P1 are exactly the ones needing regression tests | All six missing tests, beta DoD #4 |
| Auth enforcement default-on (Gate 4) | Fail-open default plus a growing route count; CSRF must cover all 43 frontend write routes at once | Every new UI route |
| Signal-weight editor no-op (+3 loc) | ADR-164 §10 extends this exact grid with channel weights | Channel weights, any settings-driven tuning |
| Click/open attribution guesses one primary content record | Mis-attributed contributions are append-only history; the corruption is permanent, and grows with every send | Signal layer, decision explainability, 3D |
| Missing DB uniqueness constraints (category assignment, content versioning) | Duplicates must be cleaned before a unique index can be added at all | Any later constraint work |
| Mode A/B/C vs Phase 4A/4B/4C rename (Docs) | Phase 4A/4C are about to write the playbook; publishing bakes the collision into the public artifact. Already cost one planning cycle | Playbook text, every future ADR reference |
| Pagination envelope | Each new list endpoint is one more retrofit, and the typed client is generated off the schema | React client, every data-heavy endpoint |

## Flat

P1 send-status aggregation; `+`-address `quote()` fix (2 loc); brand-scoped role
enforcement; webhook fail-closed when secret unset; `httpx2` typo; `Secure` cookie flag;
snapshot atomicity (but batch with the artifact rename); bulk-remove-by-criteria;
image upload/media picker; guaranteed placement; zero-content-module safety check;
provider choice on the campaign send flow; system-mail channel on its own domain;
dev-data pseudonymization guard; token-counting escape-hatch doc; extended-thinking
ceiling coupling; conversion signal sourcing; DWH export + local prune.

## Decays

- **Provider contact sync (Needs-ADR)** — its own text corrects the premise: the
  transactional `/emails` endpoint needs no pre-synced list. May delete itself.
- **A/B test component** — the architecture's own thesis is that personalization makes
  content-level A/B largely redundant over time.
- **Anti-bubble exploration** and **negative category-affinity** — both need real
  behavioral evidence that does not exist yet; building early means guessing the
  magnitude and then rebuilding.
- **"Most recipients matched" tiebreak variant** — an option alongside an existing
  working tiebreak.
- **Calendar-time vs activity-relative decay** — a named edge case (90-day holiday) with
  no observed instance.
- **Cost/token feedback before an AI decision batch** — predicated on per-recipient LLM
  selection, which the Mode-A build found to be the wrong tool, not merely expensive.
- **AI ledger double-scan** — LOW, n is small; the performance-notes doc may absorb it.
- **Progress indication + double-submit for AI tasks** — explicitly deferred to the React
  frontend; disappears if that frontend replaces the server-rendered POST.
- **Passkeys/WebAuthn** — on hold pending the user's own research; ADR-151 §6 already
  fixes the shape as additive.
- **"Publish all" button**, **DOI cold-start seeding** — convenience, no downstream.
- **11-broken-wikilink housekeeping** — see staleness-watchlist; the count is disputed.

## Scope-dependent (flips between BETA-SCOPE §1-4 and the §5 React addendum)
Pagination envelope; image upload/media picker; AI progress indication; category picker
(also stale, see watchlist); brand/theming web palette; per-task model selection;
shared approval inbox. Under §1-4 all are out; under §5 the first three become
frontend prerequisites.

---

# Run 2 additions — 2026-09-27

## Rises (new)

| Item | Why it rises | Who pays the tax |
|---|---|---|
| **Content-catalogue field model** (VE 1.8/2.4/2.8/2.9/2.10) | Every gap in batch M1 writes against a field vocabulary the ADR has not named yet. `ContentRecordDB.content` is unvalidated JSON, so a wrong key orphans content **silently**. The hero migration invents a title and brand per row and gets harder per row written | VE-2,3,10,11,13,14, VE-9's `type`, Feature L176, the client's field form, every future module manifest |
| **VE-15/20 — refuse an override on a slot-bound module** | A constraint before the feature that makes its race routine. Once `max_results` works, an override on a slot puts one pinned headline on three personalised picks | `max_results` (L358), the whole override layer, the edit-vs-override ADR |
| **Server-side filtering + pagination (MW-5)** | Reprices L242 from latent to blocking. Already invalidated four built screens; every further screen built on the un-enveloped contract is another rebuild, and the typed client is generated off the schema | The four Phase 2 screens, every Phase 3 screen, MW-7, MW-10, the typed client |
| **MW-10 — `resolutions` route unpaginated** | On the table its own model comment calls the fastest-growing in the schema, measured at 96,040 rows and unbounded by design | Any client touching decision slots; grows with every send |
| **VE-25 — `variants.status` accepts any string** | Same shape as `CONTENT_STATUSES`; constraining it after rows exist means cleaning them first | Variant list, readiness assertion (4.7), `ready` as a column the list reads |
| **MW-17 — nothing prevents self-approval** | "Safe only while machines requested and could not approve; a hole the moment a person can request" — and ADR-168's 2026-09-24 addendum just made approval available to people | The whole approval surface; it is a live hole now, not a latent one |
| **MW-8 — a held action cannot exist without a deadline** | `expires_at` is `nullable=False`; changing it later means every comparison must be re-read as *never expires* vs *expired*, across rows already written | ADR-142 §4 approval surface, content review |
| **New Needs-ADR "nothing is ever hard-deleted" (L398)** | Each new table otherwise decides independently and one eventually decides wrong. The failure is silent and only visible long afterwards | Assets, content records, categories, every future catalogue table |

## Flat (new)
VE-1 section-heading module; VE-12 `envelope_module_type` route; VE-17 reach-count
query; VE-19 `reason` as a constrained code; VE-23 per-module render state;
VE-27 `duplicate_variant`; VE-29 context-sensitive `content_mode` default;
MW-6/7 approvals response+filters; MW-9 slot distribution endpoint;
MW-12 audience-suggestion JSON route; MW-13 `resolve_audience` arithmetic;
MW-16 delivery-history audience criteria; MW-18 campaign state view.

**VE-21 (test send mails the draft, `delivery/service.py:520`) is Flat but is a
BUG, not a gap** — the one action whose purpose is showing what ships, showing
something else. Cheap, and it does not get worse. It just should not wait on a
design.

**MW-15 (`resolve_audience` defaults `channel` to email) is Flat and is also a
bug with a recorded incident** — "the recorded cause of a push send once
resolving to nobody."

## Decays (new)
- **VE-18 `outcome_delta`** — moves *deeper* into Decays than the backlog implies.
  It has no producer **and no experimental design**: a delta needs a baseline
  that was not sent, requiring a holdout, counterfactual or A/B, none of which
  exists or is specified. Building the producer without the design produces a
  number nobody can interpret. Its natural upstream (the A/B component) is
  already in Decays.
- **VE-26 shareable preview link** — new surface, carries an authorisation
  question, no consumer asking for it.
- **VE-30 nothing prevents sending a template variant** — recorded by the
  interview as *accepted, not fixed*. Leave it accepted.
- **VE-24 post-render per-recipient "nothing meaningful" skip** — needs real
  send volume to know whether it ever fires.

## Reclassified from run 1
- **Pagination envelope: Scope-dependent -> RISES.** MW-5 removed the scope
  dependency; it is a blocker under the addendum the repo is actually executing.
- **Image upload/media picker: Scope-dependent -> now the asset subsystem
  (L364), design settled, and still out of beta scope under Definition A.**
  It moved from "convenience Feature" to "subsystem with a settled design",
  which changes its size but not its launch relevance.
