# Memory Index — backlog-sequencer

First run 2026-09-12. Second run 2026-09-27 (after the Manager Workflow and
Variant Editor interviews closed). Refine these files; do not rebuild from scratch.

- [Dependency edges](graph-edges.md)
- [Cost-of-delay classes](cost-of-delay.md)
- [Same-surface batches](same-surface-batches.md)
- [Needs-ADR downstream map](needs-adr-downstream.md)
- [Staleness watchlist](staleness-watchlist.md)

## Standing constraints (do not re-derive)
- Never write to the queue (no writing `backlog` command, no file under `docs/queue/`), and never edit the frozen `docs/backlog.md`. Lowest ordinal = do next is a human decision record.
- Write access is this directory only.
- No calendar time, velocity, hours, or story points, ever.

## Queue navigation (migrated to Backlog.md 2026-09-27)
The queue is Backlog.md tasks in `docs/queue/tasks/`. Each task's description is
the original `docs/backlog.md` entry verbatim; its Implementation Notes name the
original line and section position. Read with:
- `backlog task list --status "To Do" --sort ordinal --plain` — do-next order.
  Without `--sort ordinal` the list sorts by priority, which is not the human's order.
- `backlog task view task-N --plain` — one item in full.
- `backlog search "<text>" --plain`; filter with `--labels needs-adr`, `--type bug`.
Done tasks are in `docs/queue/completed/` — outside `task list`, the board and
`backlog search`; grep that directory or `task view task-N`.
Old sections are ordinal ranges: 1xxxxx Bugs, 2xxxxx Features, 3xxxxx Needs ADR,
5xxxxx Done. `priority` is set only where the entry stated one; `Parked` = must be
prioritised before anything else.

`docs/backlog.md:NNN` citations in this directory predate the migration. The
frozen file still resolves them; to find the task, grep `docs/queue/tasks/` for
`line NNN,` in the migration note.

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
