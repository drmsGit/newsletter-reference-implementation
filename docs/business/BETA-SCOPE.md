# Beta scope — what "first beta, shipped by end of 2026" means

Written 2026-08-22. Answers the ambiguity between BRIEF.md's two readings of
"beta," using `docs/business/LAUNCH-GATES.md`, `POSITIONING.md`,
`ASSUMPTIONS.md`, `docs/playbook-strategy.md` §6, and `docs/backlog.md`.

## 1. Chosen definition

**Definition A, gates-only.** Beta = the playbook and repo are published, and
every gate in `LAUNCH-GATES.md` reads ✅. Nothing is in scope that is not
required to make an existing gate true.

**Why A beats B in one line:** every currently-open gate (1, 2, 3, 4, 4b, 8, 9)
is already scoped to the existing Jinja UI and the current repo — none of them
name the React frontend or omni-channel — so A fits inside ~18 part-time weeks
and B, which puts a not-started second codebase and a deferred 160-ADR
interview in scope, does not.

This is not really a judgment call between two equally live options. Gate 1
(BRIEF.md, POSITIONING.md) already states beta is blocked on the positioning
statement, not on features, and "content is not marketing for the launch, it
is the launch" is a direct statement of A. B is what the ambiguity in BRIEF.md
implies is *possible*, not what the gate file says is *required*. Picking B
would mean overriding LAUNCH-GATES.md's own scope on no new evidence.

One correction this makes to BRIEF.md: its "Where it stands" section still
describes `POSITIONING.md` as not existing. It exists (created 2026-08-20) and
is read directly for this decision — the file just hasn't recorded an adopted
statement yet, which is Gate 1's actual open state.

## 2. Scope

### In scope — required to close an open launch gate

| Gate | Backlog item | Source |
|---|---|---|
| 1 — Positioning | Draft candidate statements in `docs/business/decisions/`, stress-test with `positioning-critic`, adopt into `POSITIONING.md` | POSITIONING.md process |
| 2 — P0 consent | Fix: unconditional consent/suppression check immediately before `provider.send()`; replace the bare `except ValueError` with typed exceptions | code review 2026-08-07 P0-02 + P3-03 |
| 3 — P0 machine auth | Inbound machine authentication — API keys with scopes for the JSON routers; also close the unauthenticated `POST /provider/events` sibling route | code review 2026-08-07, raised to P0; user 2026-07-31 |
| 4 — Auth enforcement | Default `auth_enforced()` to on, gated by an explicit `APP_MODE=development` escape; add CSRF tokens to mutating forms; rate-limit login-code requests | code review 2026-08-07 P1-01, P2-02, P2-03 |
| 4b — Sign-in disclosure | Fix `deliver_code()`/`request_login_code()` so a delivery failure never returns the live code; fix `+`-address sign-in (2 loc, `quote()` the unescaped param); decide the login-form enumeration-oracle question (accept-in-dev-and-document, or gate behind `AUTH_DEV_SHOW_CODE`) | code-slimmer sweep 2026-08-21, Cluster 6 A1/A2/A4 |
| 8 — Playbook structure | Phase 4A: reader-per-chapter, voice, how "Ausblick" extension points are presented | playbook-strategy.md §6 Phase 4 |
| 9 — Client cases | Phase 4B: map 2–3 real client cases to the three pillars | playbook-strategy.md §6 Phase 4 |
| — Publish | Phase 4C: write and publish (website and/or ebook) | playbook-strategy.md §6 Phase 4 |

**One addition not tied to a numbered gate, included anyway:** the
three-one-liner deployment bundle — `requirements.txt`'s `httpx2` typo (blocks
a fresh install, which is the first thing anyone following the playbook will
run), the hard-coded DB password in `app/database.py`, and the missing
`Secure` cookie flag (code review P2-09, P2-08, P2-01). Cost is minutes;
shipping a publicly-cloneable repo whose first `pip install` fails, or whose
source has a live credential in it, directly damages the "control,
transparency" pitch the whole project rests on. This is the one deliberate
exception to "nothing not required by a gate" — it's required by the fact of
publishing the repo at all, which Gate-8/9/4C already assume.

### Out of scope for beta

- The React/Node frontend — not started, a second codebase, explicitly
  deferred in `playbook-strategy.md` §6 ("Product frontend... deliberately
  deferred until the stage-1 base is complete").
- Omni-channel generalization — still out of scope for beta itself, and now
  **designed rather than merely started**: the five-cluster interview closed
  2026-09-01 (25/25) and ADR-160–164 were accepted 2026-09-12, with ADR-165
  superseding ADR-001. Design being done does **not** pull omni-channel
  *building* into beta scope — but see §3 for what it settles for Gate 2, and
  §5 for frontend sequencing.
- Phase 3D (AI-based audience selection) — roadmap explicitly says "unblocked
  but should NOT be started yet" pending the per-recipient-LLM cost finding.
- Mode B (autonomous workflows), the Mode-A shared approval inbox, the second
  EU-hosted model adapter (ADR-144 §1 commitment, not yet built).
- The remainder of the 43-item Features list not named above: category
  picker, pagination envelope, bulk-remove-by-criteria, image upload/media
  picker, A/B test component, anti-bubble exploration, negative
  category-affinity, "publish all" button, DOI cold-start seeding,
  per-task model selection, brand/theming build (structure already decided,
  explicitly slated for "the final MVP package," not beta), AI ledger
  double-scan fix, `performance-notes.md`, pre-send safety-net bundle
  (dedup / double-send guard / suppression list), and the rest.
- The remainder of the 13-item Bugs list not tied to a gate: brand-scoped
  role enforcement (P1), send-instance status lying on partial failure (P1),
  webhook signature fail-open when secret unset (P1 — real risk, but not
  gate-tagged and the default deployment ships with the secret set),
  click/open attribution guessing one primary content record (P2), non-atomic
  snapshot write (P2), the signal-weight editor no-op (P2), missing DB
  uniqueness constraints on category assignment and content versioning (P2),
  the AI-suggestion truncation/lost-options UI gap (low).

  These are real defects worth fixing — none is disqualified on merit — they
  just don't block "playbook + repo published, gates green," so they don't
  compete for the ~18 weeks.

### Explicitly deferred past beta

- All 15 Needs-ADR items (see §3 — none is required, so all 15 land here by
  construction).
- Passkeys/WebAuthn — on hold pending the user's own research.
- Transactional-email consent model — flagged as a possible adoption
  dealbreaker, but explicitly "potentially a stage-2 feature."
- Snapshot/rendered-HTML storage strategy build (the ADR question and the
  build are both out).
- Suppression + opt-out reason data model.
- General data lifecycle/retention policy.
- 11-broken-wikilink ADR housekeeping session, and the Mode A/B/C ↔ Phase
  4A/4B/4C renaming cleanup — real, but editorial, not launch-blocking.

## 3. Needs-ADR: what beta actually requires

**None of the 15 Needs-ADR items are required to close a launch gate.** This
is the load-bearing finding for the timeline: the backlog's own status legend
already separates 📋 Needs-ADR from 🔴 To-Do precisely because the former
isn't actionable yet — and every item that *is* actionable and gate-tagged
(§2, above) is filed as a Bug or Feature, not as one of the 15. The two lists
don't overlap.

Three items are worth naming explicitly because someone could reasonably
assume they're required, and the reasoning for excluding each is not obvious
on its face:

- **Omni-channel.** Doesn't block Gate 1. It constrains *what the positioning
  statement is allowed to claim* (POSITIONING.md's own rule 2: no claim the
  repo can't demonstrate today), not whether the ADR gets written. The
  candidate "content management and orchestration for any channel" framing
  from the 2026-07-12/08-12 sharpening should **not** be adopted as the
  headline claim while omni-channel is undesigned — that's a writing
  constraint on Phase 4C, resolved by *not* overclaiming, not by resolving
  the ADR.

  **Status update 2026-09-12 (supersedes the 2026-08-22 update below):** the
  interview is closed and ADR-160–165 are accepted. Two consequences.
  *First, the writing constraint survives in a narrower form* — the design
  now exists, but only email is built, and POSITIONING.md's rule 2 was tested
  against exactly this case on 2026-09-12 and **held**: designed-and-accepted
  is not demonstrable, so the omni-channel framing still stays out of the
  headline claim. The constraint is now "not built" rather than "not
  designed". *Second, the Gate-2 sequencing question is answerable rather
  than open* — ADR-163 §7/§8 states the shape the P0 fix should take, so the
  remaining call is only whether the consent/addressability migration lands
  before that fix or after beta. Still a sequencing question inside
  already-in-scope Gate 2 work, not a new required ADR — the count in this
  section stays at zero.

  **Status update 2026-08-22 (stale, kept for the record):** the interview is
  now running (cluster 2 nearly done, clusters 3–5 queued)… worth deciding
  whether to sequence the Gate-2 fix *after* the interview lands instead of
  fixing the consent gate twice.
- **Dynamic decision-content × audience resolution ordering.** The circular
  dependency this item describes is already "masked" in the running system —
  suggest-audience reads existing resolutions and works for the current demo
  shape. It's a real gap, but not one the existing end-to-end path currently
  trips over, so it can be named as a known limitation in the playbook's
  Ausblick material rather than resolved first.
- **Rendered-HTML/snapshot storage strategy.** Already listed as deferred in
  BRIEF.md's own "Open forks" set ("noted as options now and implemented in
  the final MVP package"). This decision doesn't reclassify it; it just
  confirms the existing call.

The other 12 (system-email transport, concurrent-actors contention model,
Mode-A-vs-decision-slot cardinality, bulk-send batching, provider contact
sync, shadow-variant validation, guaranteed placement, isolated test DB,
hero/CTA catalogue membership, transactional sends, suppression/opt-out
model, data lifecycle) have no dependency on any of the seven open gates and
stay open without a special-case argument.

## 4. Definition of done

Beta is shipped when all of the following are checkable, per LAUNCH-GATES.md's
own rule ("a gate moves to ✅ only with something checkable behind it —
a commit, a verified live run, an adopted file"):

1. `docs/business/POSITIONING.md` has an adopted statement with a date,
   superseding this file's current "no statement adopted" state (Gate 1).
2. `docs/business/LAUNCH-GATES.md` gates 2, 3, 4, 4b, 8, and 9 all read ✅,
   each with a commit, merged fix, or adopted file behind it — not "designed."
   Gates 5, 6, 7 stay ✅ (no regression).
3. The playbook (website and/or ebook, Phase 4C) is live at a public URL or
   published as a file, built on the client cases from Gate 9 and the
   structure from Gate 8.
4. The repo is public, and a clean-container `pip install -r
   requirements.txt && pytest` succeeds (closes the `httpx2` typo and
   validates the "usable as-is" claim rather than assuming it).

No feature count, no bug count, and no Needs-ADR resolution count toward this
definition. If a future review wants to add one, it has to name which gate it
closes.

## 5. Optional — if a React/Next.js frontend is pulled into beta scope

Added 2026-08-22. This section is optional by design: §1–4 above remain the
decision unless this gets adopted. It exists because a real pilot client
needs something to work with beyond the Jinja UI, which changes what "the
repo and playbook are enough" actually requires.

**One-liner on the frontend.** The roadmap's "deferred until the stage-1 base
is complete" was a build-sequencing note about backend/security/AI work
coming first — it never actually said beta could ship on Jinja alone. A real
pilot client needs something to click, so a minimal frontend was always the
implicit plan; it just was never written down as a beta requirement, which
is what made it read as fully optional in BRIEF.md and the roadmap.

**Additive, not a replacement for §1–4.** Every gate in the scope above still
has to close regardless — a frontend doesn't reduce that work, it sits on top
of it. It also can't start for real until Gate 3 (machine/API auth) is built,
since that's what turns the JSON API from an open control plane into
something safe to build a second client against. So this track runs parallel
with the playbook-writing tail (Gates 8/9/4C), not with the security fixes.

**Decision on code — resolved 2026-08-22: React, not Next.js.** The reflex
answer was Next.js; challenged and rejected. Next.js earns its keep on
SSR/SEO/content-heavy public pages, and there is no anonymous/end-customer-
facing site in beta scope to justify that — the manager frontend serves no
anonymous traffic, needs no SEO, and its entire job is talking to an existing
REST API from behind a login. That profile fits a plainer SPA (React + Vite,
or React Router in SPA mode, with a typed API client) at less framework
weight and a shorter learning curve, and closer to the project's own
"principles over a fixed tech stack" ethos than an app-router Next.js
instance whose server-component/edge machinery would mostly go unused in an
admin panel. **Confirmed by the user 2026-08-22:** the anonymous-facing,
SEO-relevant site — the "official website go-live," where a Next.js-shaped
tool would actually earn its keep — is real but belongs to a *later* Phase 4
effort, not beta. So there's no "same app or two" fork to resolve right now;
there is one app in scope for beta (the React manager SPA), and the second
(public marketing/playbook site) doesn't get built, in any framework, until
that later go-live. Beta's own playbook publishing (Gate 8/9, Phase 4C) uses
whatever simpler channel is enough to publish content on time — Phase 4C was
always scoped as "website and/or ebook," so this isn't a new constraint, just
a confirmation that the *official* site isn't the vehicle for it.

Framework choice is a technical/architecture call, not a business one — per
this repo's own rule ("architecture decisions... written as an ADR before
implementation"), it should get a short ADR in the Claude Code side recording
the React-over-Next.js reasoning above, rather than living only in this
business doc.

**Done 2026-09-19: [[ADR-170 — The Manager Client Is a Plain React SPA, Not
Next.js]].** It records the reasoning above and adds three things this section
left open: the routing choice (React Router as a library, not its framework
mode), the repository layout (`frontend/` beside `backend/`, because FastAPI
serves the build output and the typed client is generated from the backend's
own schema), and an argument that did not exist on 2026-08-22 — ADR-168 made
FastAPI serve the client same-origin, and a Next.js app-router instance is a
server, so serving it would mean either a second Node process reintroducing the
CORS problem ADR-168 exists to avoid, or a static export that discards most of
what Next.js is for. Step 2 of the MVP cut below — reuse the session or mint a
token — is also answered and built: the session cookie, per ADR-168.

**Sequencing against the omni-channel interview.** The omni-channel
Needs-ADR item already warns, in its own text, that starting the React
frontend before that interview risks designing the manager UI around
email-only variants and then retrofitting channel-awareness in — exactly
what building the campaign/variant screens first would do. Since cluster 2 is
nearly done and 3–5 are next, the sketch and estimate below assume the
interview (or at least its implications for the campaign/variant data shape)
lands before that screen gets built, not after.

**Very rough sketch — MVP cut**, enough for a real pilot client to run the
proven end-to-end path, not full parity with the Jinja UI:

1. Framework decision + scaffold (per above) — repo, lint, CI, deploy target.
2. Auth/session transport for the frontend. The passwordless code flow
   already exists for humans; decide whether the frontend reuses that
   session (cookie, same-site) or gets its own token exchange. Keep this
   separate from Gate 3's *machine* API keys — those are for orchestrators
   and CRMs, not for a person sitting at the manager UI, and conflating the
   two auth mechanisms would be a mistake.
3. Typed API client off the FastAPI OpenAPI schema the backend already
   emits — avoids hand-writing request/response types per screen.
4. Core screens, in the order the Jinja build proved out the flow: campaign
   + variant builder (modules, decision slots) → audience (manual +
   suggested/edited) → prepare-send (audience, provider, freeze/re-run,
   schedule, cap) → a read-only delivery-status/signals view. Settings,
   full content-versioning UI, and Mode-A's polish stay Jinja-only or thin
   for now.
5. Minimal styling pass — usable, not the brand/theming build (still
   explicitly deferred to the final MVP package).
6. Smoke tests + CI for the new codebase.

**Recalculated date.** A naive bottom-up estimate for the MVP cut above
lands around ~11 additional part-time weeks. Two adjustments to that raw
number, one in each direction: most of this is new *views* on APIs and
domain logic that already exist and are already designed, which is narrower
than a from-scratch build — and the Jinja equivalent of this same set of
screens (Phases 1–3C: content, campaigns, decision slots, audience, send
prep) was actually built in about 7 calendar weeks from a standing start,
working the same part-time way this project has been built throughout. That
is a real in-repo data point, not a guess, and it argues the raw 11-week
estimate is conservative rather than optimistic. Netting that against the
sequencing dependencies on Gate 3 and the omni-channel interview, a
reasonable planning range is **+8 to +14 working weeks** on top of the
18-week gates-only baseline — **26 to 32 weeks total**, landing beta
somewhere between **~February 20, 2027 and ~April 3, 2027**. Recommended
planning point: **~March 6, 2027** (28 weeks, +10).

Treat this as a planning estimate to sanity-check against your own sense of
pace, not a committed date. I don't have velocity data finer than "how long
the equivalent Jinja phases took," and the frontend carries failure modes the
backend phases didn't — framework learning curve, CORS/session integration
friction, and the omni-channel sequencing dependency chief among them.
