Work through a business-interview file with the user, finding by finding, and log business decisions durably. Structural counterpart to `/interview-review`, adapted to this file's actual shape: lettered/numbered findings (e.g. A1, B2) with 5 fixed sub-answers and a 4-way status tag, not per-question checkboxes — and business decisions belong in `docs/playbook-strategy.md`'s Decision Log, not `docs/backlog.md`. This is a working session, not a one-shot report — expect to stop and resume across multiple invocations.

## Step 1 — pick the file
If the user didn't already name a file, ask whether to work on `docs/business-interview-baseline.md` (the initial ADR/codebase scan) or `docs/business-interview.md` (the per-feature companion log, if it has entries). If a file has no remaining 🟡 deferred or ⚠️ unsure items, say so and ask if they want to revisit a ⚪ non-blocking one anyway or stop.

## Step 2 — go finding by finding
1. Find the first item still tagged `🟡 deferred` or `⚠️ unsure` in the Triage section at the top of the file, in the order it's listed there (not necessarily document order — the Triage section is the authoritative queue).
2. Present the finding: its heading, the 5 sub-answers, and (if it has one) its existing partial resolution note.
3. Discuss with the user as needed. If the finding depends on a feature/phase that doesn't exist yet, say so explicitly — don't force an answer ahead of scope just to close the item.
4. Ask the user to decide one of:
   - **resolve now** — a real business decision can be made; capture it
   - **still deferred** — genuinely not answerable yet (note why, briefly, if the reason changed)
   - **reclassify as non-blocking/cosmetic** — discussion revealed it doesn't actually matter
   - **unsure, skip for now** — needs the user's input at a later time (only if they explicitly say so — don't default to this)
5. Record the decision immediately:
   - If **resolve now**: write a `**Resolution (<date>):**` paragraph directly under the finding's 5 sub-answers, in the same voice/detail level as the existing 6 resolved findings in this file (narrative, references specific files/ADRs, states the actual decision and its reasoning) — not a one-liner. Update the heading's status tag to `✅ resolved 2026-07-05` (or session date). Add a row to the Triage section's "✅ Resolved" table with a one-line summary. Also append the full narrative to `docs/playbook-strategy.md` → Decision Log as a new dated entry, matching the existing "2026-07-05 — Business-Assumption Triage Resolutions" style — this file is the durable business-decision record, the interview file is the classification/audit trail pointing back to it.
   - If **still deferred**: leave the tag as `🟡 deferred`; only update the Triage bullet if the reason changed.
   - If **reclassify as non-blocking**: move the item from the 🟡 Triage list to the ⚪ list, update its heading tag to `⚪ non-blocking`, and add one sentence explaining why it turned out not to matter.
   - If **unsure, skip for now**: tag `⚠️ unsure` and add to that Triage section — this must be explicit, not a default.
6. If discussion surfaces a genuinely new idea/concept (not a resolution of the current finding), add it to the "New Concepts Surfaced" section (create one if the file doesn't have it yet) rather than forcing it into the current finding's resolution. Cross-reference `docs/backlog.md` if it has a technical-implementation angle worth tracking there too.
7. Move directly to the next open item. No summary or recap in between — keep momentum.

Do not skip an item unless the user explicitly says to. A skipped item stays in its current status and will be presented again, in the same order, the next time this command runs on that file.

Stop when either all `🟡`/`⚠️` items are resolved or reclassified, or the user says to stop for now. If stopping mid-file, briefly note how many open items remain.

## Rules
- Never invent or assume a business decision the user didn't actually state — these are strategic calls, not code fixes; get it right rather than fast.
- Never skip ahead or batch multiple findings without the user weighing in on each one individually.
- Keep responses tight during the loop — finding, brief discussion, decision, log, next finding. Save longer synthesis for when the user asks for it or the file is fully resolved.
- If a finding's resolution changes an already-settled technical decision (e.g. reopens something closed via `/interview-review`), flag the conflict explicitly and ask how to reconcile rather than silently overwriting either record.
