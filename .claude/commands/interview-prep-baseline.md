Review the current codebase as it stands (not just a recent diff). For each major module/feature already implemented, generate 5-8 interview-style questions a reviewing developer would likely ask, focused on:
- why this approach over the obvious alternative
- edge cases / failure modes
- performance or concurrency implications
- data model / schema tradeoffs

Group the questions by module/feature. Answer each concisely, referencing specific files/functions/line numbers.

**Delegate the sweep.** This is a whole-codebase pass — do not read the modules into the main session. Fan out with the Explore agent, one call per module cluster, and compose the questions from what comes back. `docs/architecture/Code/` holds a page per module (Purpose / Key files / Public surface / Data model / Invariants) — read those first; they are cheaper than the source and were written for exactly this.

Two things about that folder:
- If a module has no page, say so in the output rather than silently falling back to source. A missing page is itself a finding.
- `backend/app/automation/` and `backend/app/privacy/` contain no code. Skip them; their ADRs are accepted-but-unimplemented, which is a business finding, not an interview question.

Do not re-raise questions already cleared in `docs/architecture/interview-prep/` — every cluster file in that folder is reviewed. New questions only, or a specific claim that an earlier resolution no longer holds.
