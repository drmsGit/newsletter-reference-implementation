# The backlog moved to `docs/queue/`

**This file is a signpost. It has held no queue since 2026-09-27.**

The work tracker is now [Backlog.md](https://backlog.md) under `docs/queue/` —
one markdown file per task, inside this vault so wikilinks still resolve.

```bash
backlog task list --status "To Do" --sort ordinal --plain   # the queue, in priority order
backlog board                                               # the board
backlog task <id>                                           # one task
```

`--sort ordinal` matters: **ordering is the priority record**, carried over from
this file's section order. Without it the list sorts by the `priority` field,
which most tasks do not yet carry.

Open tasks live in `docs/queue/tasks/`, finished ones in `docs/queue/completed/`.

## Where the old contents went

Every entry became a task, description byte-identical to what stood here — the
reasoning, the verified `file:line` citations and the rejected options were the
point of this file, so nothing was summarised. Each task's notes name its source
line and its position in its old section.

- `b70f432` — the migration
- `a1bf183` — finished entries into `completed/`
- `f8278cb` — the design-interview gaps, which had never been in this file at all

## If you followed a link here

**Citations across the ADR set point at this path.** They are historical and
were deliberately left alone: an ADR records what was true when it was written,
and rewriting those citations would edit dated records to match a later fact.

If one sent you here, the entry it meant is a task now — open or, more often
for an ADR citation, finished. Search both folders; `backlog task list` and
`backlog search` do not look in `completed/`:

```bash
grep -rli "<a few words from the entry>" docs/queue/tasks docs/queue/completed
```

If the citation gives a line number, read that line as the file stood when the
citation was written — the file's length changed a lot, so today's numbering
will not match — then search for its words:

```bash
git show $(git rev-list -1 --before=<date written> HEAD):docs/backlog.md | sed -n '<line>p'
```

## The file itself

It ran from 2026-07-04 (`ec5b85e`) to 2026-09-27 and reached 633 lines and
371 KB — which is why it was replaced. **Every version is in git** and none of
it is lost:

```bash
git log --follow -p -- docs/backlog.md    # the whole history
git show b70f432^:docs/backlog.md         # the last full version
```

That is the reason this is a signpost rather than a frozen copy. Git is the
archive already, and a second one that looks authoritative and is not is the
exact failure this repository kept hitting — a stale entry misled a sequencing
pass on 2026-09-27, and an accepted ADR sat unimplemented for three days because
nothing tracked it. One place to look was the point of moving.
