# Launch gates

What must be true before public beta. Reviewed against commits and
`docs/backlog.md`; not a wish list — each item blocks something specific.

| # | Gate | Blocks | State |
|---|---|---|---|
| 1 | Positioning statement adopted | public beta, Phase 4C write & publish | ❌ open — `POSITIONING.md` |
| 2 | P0 consent defect fixed | any public exposure (compliance) | ❌ open |
| 3 | P0 inbound machine authentication | any public exposure | ❌ open |
| 4 | Auth enforcement flag switched on | any public exposure | 🟡 built, ships off |
| 5 | Real provider integration proven | the "no lock-in" claim | ✅ done — Resend, live, verified domain |
| 6 | Inbound engagement loop proven | the signal-layer claim | ✅ done — signed webhooks, end-to-end |
| 7 | Security model designed + base built | Phase 4C | ✅ ADR-150–154; base built, proposed status |
| 8 | Playbook structure decided (4A) | 4C | 🟡 started in Cowork |
| 9 | 2–3 client cases mapped to the pillars (4B) | 4C | ❌ open |

## The three that actually block exposure
Gates 2, 3 and 4 are the ones where "we launched" and "we were fine" come
apart. From the 2026-08-07 external review:

- **Gate 2** — a frozen audience is consent-gated at plan time and never again,
  and the decision layer's consent guard is swallowed by a bare `except
  ValueError` in `delivery/service.py`. A compliance defect currently reads as a
  rendering behaviour. Note it overlaps the deferred omni-channel interview,
  which restructures the same send-time gate — fixing once, in the right shape,
  is the argument for running that interview first.
- **Gate 3** — the JSON API routers are deliberately unguarded; that is machine
  authentication, scoped as a Mode B prerequisite. It was raised to P0 because
  it blocks public exposure, not just Mode B.
- **Gate 4** — the enforcement mechanism covers every UI page but ships off
  until a deployment has signed in once. Fine locally, not for anything public.

## Rules
- A gate moves to ✅ only with something checkable behind it — a commit, a
  verified live run, an adopted file. "Designed" is not "done"; gate 7 is
  deliberately split that way.
- Update this file when a gate moves, not at review time.
