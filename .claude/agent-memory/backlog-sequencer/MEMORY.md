# Memory Index — backlog-sequencer

First run 2026-09-12. Second run 2026-09-27 (after the Manager Workflow and
Variant Editor interviews closed). Refine these files; do not rebuild from scratch.

- [Dependency edges](graph-edges.md)
- [Cost-of-delay classes](cost-of-delay.md)
- [Same-surface batches](same-surface-batches.md)
- [Needs-ADR downstream map](needs-adr-downstream.md)
- [Staleness watchlist](staleness-watchlist.md)

## Standing constraints (do not re-derive)
- Never edit `docs/backlog.md`. Top of section = do next is a human decision record.
- Write access is this directory only.
- No calendar time, velocity, hours, or story points, ever.

## Backlog navigation (re-measured 2026-09-27)
`docs/backlog.md` is 621 lines / 364KB. Each item is ONE very long line, with
some continuation lines indented beneath. Grep by section, then
`awk 'NR==<n>' docs/backlog.md | fold -s -w 150`.

Section line ranges 2026-09-27: Bugs 23-131, Features 132-395, Needs ADR 396-482,
Won't Do 483-486, Done 487-618, Related 619+.

Useful absolute line anchors (2026-09-27, will drift):
- 136 React first-screen gaps (C1/C15 done, **C8 + C2 open**)
- 138 the `frontend/router.py` service-boundary precondition
- 142 `audit_events` three unproven properties
- 144 machine-plane reads fall through to platform `view`
- 150 subscribe/DOI/unsubscribe + `List-Unsubscribe` (RFC 8058)
- 176 content-record form half hand-written
- 242 pagination envelope (stale — does not record the MW repricing)
- 354 audience member removal · 356 section-heading module
- 358 `max_results` + single-pick resolution · 360 advisory lock + concurrency
- 362 `hero` -> `cms: true` migration · 364 asset subsystem (design settled, +25 cont. lines)
- 390 duplication drops overrides · 392 `outcome_delta` · 394 test-send bug
- 398 "nothing hard-deleted" (new Needs-ADR) · 400 catalogue field set union
- 427 ADR-169 flow decision (unblocks L150)

## Run-2 orientation snapshot
- BETA-SCOPE.md **exists**: Definition A, gates-only. §5 is the optional React addendum.
- Gates 2, 3, 4 CLOSED. Open: 1 (positioning), **4b (REOPENED 2026-09-19, timing oracle)**, 8, 9.
- ADRs now run to 176. ADR-150–154 accepted 2026-09-18. ADR-174/175/176 accepted.
  All four Manager-Workflow addenda (142, 150, 161, 168) are written.
- Frontend: `frontend/src/screens/` has exactly the four Phase 2 list screens
  (Content, Campaigns, Audiences, Approvals) + two details + SignIn. Phase 3 paused.
