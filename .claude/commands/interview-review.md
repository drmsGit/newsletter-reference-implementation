Work through an interview-prep baseline file with the user, question by question, and log actionable decisions to the backlog. This is a working session, not a one-shot report — expect to stop and resume across multiple invocations.

## Step 1 — pick the file
If the user didn't already name a file in this invocation, ask which interview-prep file to work on. List the cluster files under `docs/architecture/interview-prep/` (exclude the `MOC - Interview Prep Baseline.md` index itself). If a file was fully cleared last time (no unchecked questions remain), say so and ask if they want to pick a different one.

## Step 2 — go question by question
1. Find the first unchecked (`- [ ]`) question in the chosen file, in file order (top to bottom, module by module).
2. Present the question and its existing baseline answer.
3. Discuss with the user as needed.
4. Ask the user to decide one of:
   - **act / fix** — this needs a code or design change
   - **keep in poc** — acceptable gap for now, not worth fixing at this stage
   - **keep in project** — accepted as permanent/intentional design, not actually a gap
5. Record the decision immediately:
   - Check the box (`- [x]`) on that question.
   - Fill in its `**Resolution:**` line with the decision plus a one-sentence rationale from the discussion.
   - If the decision is **act / fix**, add a task to the queue (see Step 3). If **keep in poc** or **keep in project**, do NOT add a backlog entry — the resolution line in the interview-prep file is the complete record.
6. Move directly to the next unchecked question in the same file. No summary or recap in between — keep momentum.

Do not skip a question unless the user explicitly says to skip it. A skipped question stays unchecked and will be presented again, in the same position, the next time this command runs on that file — never silently drop it.

Stop when either all questions in the file are checked, or the user says to stop for now. If stopping mid-file, briefly note how many questions remain unchecked so the user knows where things stand.

## Step 3 — logging to the queue
The queue is Backlog.md (`docs/queue/`, the `backlog` CLI). Order is priority: lowest `ordinal` = do next. Ranges: 1xxxxx Bugs, 2xxxxx Features, 3xxxxx Needs ADR.

When a decision is **act / fix**:
- Classify it as **Bug** (something broken/incorrect) or **Feature** (something missing/to build).
- Find its position: `backlog task list --status "To Do" --type <bug|feature> --sort ordinal --plain`, then `backlog task view task-N --plain` on the neighbours to read their `Ordinal`. Do not just put it at the bottom. If the right position isn't obvious, ask the user where it ranks relative to existing items.
- Pick an ordinal between the two neighbours (they start 100 apart). If no whole number is left between them, tell the user and renumber the tasks below with `backlog task edit task-N --ordinal <n>` — only with their go-ahead.
- Create it:
  `backlog task create "<title>" --desc "<entry>" --type <bug|feature> --labels <backend|frontend|docs> --ordinal <n> --no-dod-defaults -a ""`
  adding `--priority P0|P1|P2|P3` only if the user stated one.
- The description is the full entry, not a summary: `**[Bug|Feature]** <what and why, with file:line where known>. Source: [[<interview-prep file>]] → <Module> Q<n>.` Wikilinks resolve because the queue sits inside the vault.
- Bugs outrank features of similar importance when both are candidates for the same position.

## Step 4 — re-grooming existing backlog items
If, while working through a file, an already-logged To Do task comes up again (e.g. a related question surfaces the same issue, or the user brings up an old item), ask: "still want to act on this, or should it become Won't Do?" If declined, record why with `backlog task edit task-N --append-notes "Won't Do <date>: <reason>"`, then `backlog task archive task-N`, rather than leaving it stale. `docs/backlog.md` is a signpost now — never write to it.

## Rules
- Never skip ahead or batch multiple questions without the user weighing in on each one individually.
- Never invent or assume a resolution the user didn't actually state.
- Keep responses tight during the loop — question, brief discussion, decision, log, next question. Save longer synthesis for when the user asks for it or the file is fully cleared.
