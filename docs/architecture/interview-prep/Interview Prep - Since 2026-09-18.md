---
type: interview-prep
status: closed
topic:
  - architecture
  - review
  - client
  - ci
  - delivery
  - unsubscribe
created: 2026-10-09
modified: 2026-10-09
---

> Prepared by ChatGPT (GPT-6 / Codex) on 2026-10-09 in its pre-stage (`docs/queue/docs`, doc-8) and moved here by the user's decision the same day. Its three defect findings were verified and promoted as task-327, task-328 and task-329.

# Interview prep — technical — since 2026-09-18 (GPT-6 / Codex)

Prepared 2026-10-09. Suggested answers describe current code for the maintainer to confirm or reject; they are not adopted answers or architecture decisions.

Scope starts at `b008707aaab4dd703e5606587d61f42d6ad29c46`, the last commit before 2026-09-18 at midnight Atlantic/Canary. Started with the requested `git log --since=2026-09-18 --stat` and diff from that base. Review began at `50db60f`; concurrent work advanced HEAD to `05088de4` and changed delivery source. Final delivery premises were rechecked there. Concurrent edits in ADR-142/192 and task-326 are another session's work and were left untouched. `git fetch` succeeded; the regression branch's equivalent tests are already cherry-picked, so none were imported.

## Manager client, held approvals and machine reads


Governing ADRs: 168, 170, 173, 172. `docs/architecture/Code/manager-client.md` was read before source. The older `frontend.md` page describes Jinja, not this client.

- [x] **Q1.** The session query explicitly disables retries for 401; resource queries inherit one retry for every thrown HTTP error. What failure classes should a reviewing developer expect the retry to help, and is the extra request for a permission refusal intentional?
  **Why it's worth asking:** `frontend/src/main.tsx:24-25` sets the general retry; `frontend/src/api/session.ts:99-107` opts the session out; `frontend/src/api/resources.ts:69-74` converts all non-OK statuses to thrown errors without a status-based retry predicate. The client sends additional reads after failures, even when repeating the same request cannot change authorization.
  **Checked against:** Auth interview Q7 resolves repeated *server session lookup/write*, not client HTTP retry; ADR-173 Decision 2 chooses the cache library but does not classify retryable responses; Manager Workflow and all final-design passes do not settle this retry predicate; no matching open/completed task found in the retry/focus/cache search. Business baseline P2-B1 concerns timeout configuration, not read retries.
  **Suggested answer (for the maintainer to confirm or reject):** Current resource reads retry once; session reads fail immediately. This is the implemented distinction, without a broader HTTP-status retry policy (`main.tsx:18-27`, `session.ts:103-109`).
  **Resolution (2026-10-09): act / fix — retry only network failures and 5xx, never a 4xx.** Repeating a refused, missing or conflicting read cannot change the answer; it only delays the error and doubles denials in the logs. Nothing on record ever chose the blanket retry. Queued as task-333.

- [x] **Q2.** What event ends the assumption that a module manifest cannot change during a manager session: a browser reload, a backend deployment, or an explicit cache invalidation?
  **Why it's worth asking:** `frontend/src/api/resources.ts:700-706` caches manifests with `staleTime: Infinity` because files are read at startup. A backend restart can load new files while an existing browser remains open; the browser session and process lifetime are different boundaries. This asks about an operational assumption, not whether manifests should be data instead of files.
  **Checked against:** ADR-173's cache choice; ADR-177's single field definition; Variant Editor design interview's manifest-driven fields; task-255's editor implementation; all interview files/business files/playbook and open/completed tasks searched for staleTime, manifest cache, session and deployment. The existing manifest ownership/field questions do not specify the browser/deployment lifetime contract.
  **Suggested answer (for the maintainer to confirm or reject):** No manifest version or deploy identifier appears in this query key. The browser continues using its cached answer until an explicit invalidation or client restart causes another read (`resources.ts:702-706`; brand switching invalidates all queries at `session.ts:177`). No live deployment was tested.
  **Resolution (2026-10-09): keep in poc — the boundary is a page reload** (or a brand switch, which invalidates everything). The comment "do not change under a session" is corrected to say so (task-334). Revisit together with the reference deployment (task-55), when deploys happen under open tabs.

- [x] **Q3.** How should a developer adding a nested screen or overlay resolve two live handlers that register the same shortcut: is registration order deliberately the precedence rule?
  **Why it's worth asking:** `frontend/src/shortcuts/Shortcuts.tsx:67-72` appends registrations; `:87-94` uses the first exact match. The registry supports descriptions with no handler and component lifetime cleanup, but has no explicit priority or collision check. This is a contract for adding client features, not a report that bundled shortcuts already collide.
  **Checked against:** Variant Editor design interview's keyboard-first resolution; Campaign Write Surface D1 and picker keyboard notes; task-266's shortcut work; ADR-173's React Aria choice. These establish keyboard operation and a single shortcut inventory, not the precedence of simultaneously registered handlers. Full duplicate-corpus search found no shortcut collision/duplicate dispatch resolution.
  **Suggested answer (for the maintainer to confirm or reject):** Today the oldest matching live registration wins; removing that registration exposes the next. Typing targets and modifier combinations are filtered before dispatch (`Shortcuts.tsx:76-99`). Whether that precedence is an intended extension contract remains a maintainer question.
  **Resolution (2026-10-09): keep in poc.** Today the oldest live registration wins; overlays will need the newest (innermost) to win, plus a warning on duplicates. Decided as part of the later keyboard and accessibility session, not now.

- [x] **Q4.** The HTTP client's explanation justifies its mutable CSRF token with “exactly one writer”; verify and sign-out also write it now. What is the actual lifecycle invariant that keeps this shared value correct?
  **Why it's worth asking:** `frontend/src/api/client.ts:52-55` claims one writer; session fetch writes at `frontend/src/api/session.ts:91`, successful verification writes immediately at `:141`, and sign-out clears it at `:189`. The code is more accurate than its rationale. This is a documentation/ownership premise question, not a claim that the CSRF check is broken.
  **Checked against:** ADR-168 Decision 2 (token in memory and header); Auth Q4 (domain separation/hash primitive); Manager Workflow's same-origin cookie/CSRF summary; task-32 (resolve session once); every interview and business file/playbook searched for token writer/ownership. Existing security decisions settle where the token lives but do not justify the now-expanded set of client writers.
  **Suggested answer (for the maintainer to confirm or reject):** One module owns the value, with three auth lifecycle write sites. Verification makes it usable immediately, session reads refresh it, and logout clears it along with cached data (`session.ts:139-144,188-191`). “One owner” would describe current code more accurately than “one writer”; the maintainer decides whether that is the intended invariant.
  **Resolution (2026-10-09): keep in project — already settled; only the comment is stale.** The token is derived from the session token and fixed for the session's life (ADR-168, 2026-09-20 addendum), so the three lifecycle write sites cannot disagree. The comment is reworded to "one owner module, three write sites" (task-334).

- [x] **Q5.** Does the generated client promise compile-time agreement with this checkout only, or also compatibility for an older browser build or external integration when response meaning changes without changing its TypeScript shape?
  **Why it's worth asking:** `frontend/src/api/client.ts:8-13` explains compile-time generation; `frontend/src/api/resources.ts:74` casts response data; `.github/workflows/ci.yml:153-157` regenerates declarations and compares their text. None of these operations validates a live response's meaning or proves compatibility with an older deployed client.
  **Checked against:** ADR-170 Decision 4–5, ADR-190 contract check, task-244 (remove frozen Jinja schema routes), task-105 (schema file export), task-302 (real-browser flows). Those settle schema derivation and testing infrastructure, not a versioned compatibility promise. No compatibility/version policy found in the full interview/business/playbook/task duplicate search. This does not re-request the already queued browser tests.
  **Suggested answer (for the maintainer to confirm or reject):** The checked guarantee is that the committed client declarations match the current backend's generated schema; response data is not runtime-validated here (`resources.ts:66-75`). A support promise for older clients is not established by the inspected code.
  **Resolution (2026-10-09): keep in project — the guarantee is this checkout's client against this checkout's server, nothing more** (ADR-170 point 5: one repository, the backend serves the build). Said so in `docs/implementation/TypedApiClient.md` (task-334). The contract for outside integrations belongs to task-119 (note added there).


Governing ADRs: 142, 166, 168, 174. No dedicated Code page exists for approvals; auth's page was read first. 

- [x] **Q6.** If the requesting integration is deactivated or its grants are revoked after it creates a held request, does a person's later approval deliberately retain authority to execute that request?
  **Why it's worth asking:** `backend/app/approvals/service.py:103-115,163-171` stores requester attribution; `:261-342` approves using the stored payload/brand and the person who decides. `:495-534` checks the approver's current permission and self-approval rule, without re-authenticating the requesting integration. This is deferred authority in a held action, not future access using the revoked credential.
  **Checked against:** auth Code page’s durable-actor/credential-ownership explanation; business baseline P2-B2 (unexpiring issued credentials); ADR-166 Decision 3–5 (durable actor, revoke, approval) and its read addendum; ADR-142 lifecycle/claim addenda; task-200 (self-approval); Manager Workflow Cluster 1 (inbox and approval authority). Those settle attribution and future authenticated requests, not whether an already held proposal survives requester offboarding. Corpus search found no pending-request cancellation on requester revocation/deactivation resolution.
  **Suggested answer (for the maintainer to confirm or reject):** Current approval depends on the person's present authority and the action's live domain checks. Requester ID remains history; revocation does not appear on this execution path (`approvals/service.py:326-342,507-534`). Whether that is deliberately retained proposal authority is a maintainer question.
  **Resolution (2026-10-09): act / fix — void at decision.** When a person approves, the request is re-checked against its requester's standing at that moment; a requester that is switched off or no longer holds the action's permission voids it (withdrawn, audited), and the inbox marks such requests. One check covers deactivation and grant revocation alike; a person who still wants the action does it under their own authority. Recorded in the second 2026-10-09 addendum to ADR-142; queued as task-331.

## CI and dependency verification


Governing ADRs: 189 and 190, including ADR-190's 2026-10-08 Ruff security addendum. There is no dedicated Code page for CI or installed-package verification; `Code/testing.md` covers testing generally. Missing dedicated page is a finding, not a reason to infer undocumented behavior.

- [x] **Q1.** CI says actions are pinned so a moved tag cannot change what runs; should that same immutability boundary include the gitleaks container tag?
  **Why it's worth asking:** `.github/workflows/ci.yml:14-16` makes the rationale explicit and actions use SHAs, but `:169` executes `ghcr.io/gitleaks/gitleaks:v8.30.1`, not a digest. This asks about a concrete remaining boundary rather than reopening the choice to scan secrets.
  **Checked against:** ADR-190 Negative (third-party action SHA pins), task-105 notes (gitleaks container avoids paid organization licensing), task-235/ADR-189 dependency provenance, business launch/security gates. No container digest/pin resolution found in all interview/business/playbook/open/completed-task searches.
  **Suggested answer (for the maintainer to confirm or reject):** Workflow action revisions are immutable SHA selections; the scanner image is selected by a version tag (`ci.yml:163-169`). The repository does not attest that tag's immutable digest. This is not a claim the registry has changed the tag.
  **Resolution (2026-10-09): act / fix — pin the gitleaks image by digest**, tag kept in a comment, so the file's own immutability promise holds for the one step that reads the whole history. Queued as task-332.

- [x] **Q2.** What does a green installed-package check promise about an optional npm package absent on a platform where it could run, rather than a binding for another architecture?
  **Why it's worth asking:** `backend/scripts/check_installed.py:95-100` marks every lock entry with `optional` as optional; `:158-160` allows any such entry to be absent. Its explanation and task-236 motivate the exemption with platform-specific builds. The code's exemption is broader than a platform comparison.
  **Checked against:** task-236 description, acceptance criteria and implementation notes (optional other-platform bindings may be missing); ADR-189's scope and install rule; ADR-190's installed-packages gate; all question/business/playbook/task files searched for optional missing packages. No rule distinguishes “optional on this machine” from “for another machine.” This does not allege npm's permitted optional-dependency behavior is a defect.
  **Suggested answer (for the maintainer to confirm or reject):** The check guarantees presence only for entries not marked optional; it checks versions of optional packages if installed (`check_installed.py:149-161`). Whether a current-platform optional omission matters requires some separate functional evidence.
  **Resolution (2026-10-09): keep in project.** The exemption is for other-platform builds. A missing current-platform binding breaks the frontend build and tests in the same CI run, which is what catches it. One sentence saying so goes into the script's docstring (task-334).

- [x] **Q3.** What makes failing checks an enforced merge gate for this repository or an adopter's fork, beyond the workflow running and returning failure?
  **Why it's worth asking:** `.github/workflows/ci.yml:20-25` declares execution triggers, while `:27-28` gives read-only repository permissions. Branch protection/rulesets are hosted configuration, not expressed by this file. ADR-190's claim that defects cannot land therefore depends on a deployment of the workflow as a required check.
  **Checked against:** ADR-190 Decision 1–2 and its positive consequences; task-105 completion notes (checks ran green); ADR-143's structural enforcement principle; launch gates, business beta scope and all interviews/tasks searched for branch protection/rulesets/required checks. No repository-side merge-enforcement setting was inspected, so this is an explicit unverified boundary, not a claim that protection is absent.
  **Suggested answer (for the maintainer to confirm or reject):** The repository supplies runnable checks. Whether merging is refused when those checks fail depends on host rules not visible in the checkout. A fork can run the same commands but inherits no proved hosted configuration from this source.
  **Resolution (2026-10-09): keep in poc — CI fails visibly; it does not stop a change landing.** On a private repository on a personal free plan, GitHub refuses branch protection and rulesets. All work goes straight to `main` and every push is followed until green, so required checks would change nothing today. ADR-190's "cannot land" is corrected by its 2026-10-09 addendum. Required checks are switched on when the code moves to the product's own GitHub account: free if that repository is public, Team plan if private; Enterprise is not needed. Not now: Pro on the personal account would gate the wrong account, and going public is blocked by the positioning gate and the uncleared name. The README will tell a fork to set its own required checks (task-334).

- [x] **Q4.** Should a new push deliberately cancel an in-progress weekly vulnerability scan, and how is a canceled scan distinguished from a completed healthy scan operationally?
  **Why it's worth asking:** `.github/workflows/ci.yml:23-24` schedules weekly discovery; `:30-32` groups all runs by `github.ref` and cancels in-progress runs. A schedule and push on the same ref share that cancellation group. The next push normally runs the same audit again, but cancellation is not itself evidence of a clean result.
  **Checked against:** ADR-190 Decision 1 and 4 (weekly scans detect newly published vulnerabilities), task-105 implementation notes (push, PR, weekly and manual), business launch gates and all interview/task files searched for cancellation/concurrency/scan notification. These settle frequency, not cancellation/observation semantics. No notification automation or hosted run state was inspected.
  **Suggested answer (for the maintainer to confirm or reject):** The current policy favors the newest run on a ref, across event types (`ci.yml:30-32`). A completed successor can provide audit evidence; the YAML alone does not show who observes missing or canceled weekly evidence.
  **Resolution (2026-10-09): act / fix — a push never cancels the scheduled scan.** The weekly run exists for quiet weeks; on a busy day a push silently erased it. Queued as task-332. Who watches the weekly result stays a POC gap.

- [x] **Q5.** Why is the installation equality check performed in a separately re-created environment instead of the exact backend and frontend environments whose tests just passed, and what shared guarantee should readers infer?
  **Why it's worth asking:** `.github/workflows/ci.yml:74-77` installs the backend under test; `:110-111` installs the frontend under test. The dependent `contract-and-installs` job installs both again (`:142-148`), then compares the fresh installation with locks. The gate proves the second job's install, rather than observing the tested jobs' files after their checks.
  **Checked against:** ADR-190 Decision 1 (run the installed check), ADR-189 Decision 3 (hash installs), task-236 (local and CI check), task-105 job layout and its final verification notes. They describe the separation but do not discuss whether mutation during a test/build job belongs to the attestation. All earlier interviews and business/playbook/task records were searched for environment attestation and tested installation equivalence.
  **Suggested answer (for the maintainer to confirm or reject):** All jobs install the same committed locks, and the separate job checks that a clean installation agrees with those locks. It does not attest the post-test files or installed metadata in another job's filesystem (`ci.yml:124-148`). The intended assurance beyond reproducibility should be confirmed.
  **Resolution (2026-10-09): keep in project, with the rationale written down.** The test jobs already refuse any non-locked install (`--require-hashes`, `npm ci`). The fresh-install check proves a clean install reproduces the locks, and its main value is the local drift guard task-236 built. It does not attest the tested environment. Recorded in `docs/architecture/Code/testing.md` (task-334).

## Audience history, delivery safety and recipient unsubscribe

Governing ADRs: ADR-188 (flat engagement predicates), ADR-176 (exclusion precedence and send-time audience resolution), ADR-163 (consent), ADR-191 (unsubscribe), ADR-192 (stranded release), ADR-183 (as-sent evidence). Read Code pages `audience.md`, `delivery.md`, `recipients.md`, `providers.md`, `insight.md` and `Flow - Engagement to signal.md` before source. **Missing module page:** `backend/app/subscriptions/` has no page in `docs/architecture/Code/`.

- [x] **Q1.** Does “clicked more than N days ago” mean any historical click, or that the person's most recent click is that old?
  **Why it's worth asking:** `_engaged` joins event rows and applies `occurred_at < cutoff`; recipient membership uses an `IN` subquery. A person who clicked both long ago and yesterday still matches the older window (`backend/app/audience/service.py:707`, `backend/app/audience/service.py:782`, `backend/app/audience/service.py:795`). This is an existential history predicate, not an inactivity predicate.
  **Checked against:** ADR-188 Decision 4 and Notes on frequency/decay predicates; Audience Write Surface final-design decision 7; completed task-296 implementation choices; Manager Workflow Cluster 4 Q7 (suggestions), Cluster 5 Q6 (missed-send audience); business baseline J1 and K1; task-82 (signal decay) and task-96 (automated engagement suggestions). Those establish historical events and live windows, but do not settle the any-event versus latest-event interpretation.
  **Suggested answer (for the maintainer to confirm or reject):** Today it means any matching event. A “lapsed reader” audience needs a positive historical rule plus a leave-out recent-click rule, under ADR-188's subtraction model; the query contains no per-recipient `max(occurred_at)` (`backend/app/audience/service.py:775`). Confirm that this is the intended meaning of the wording.
  **Resolution (2026-10-09): keep in project — any click older than N days.** An engagement field asks whether something happened (ADR-188 Notes); a "did not" is a leave-out rule (ADR-188 point 5). A lapsed reader is two rules: who's in, "clicked more than 90 days ago"; leave out, "clicked in the last 90 days". Built that way in task-296 and task-298.

- [x] **Q2.** Which calendar does an absolute engagement date represent for a manager outside UTC?
  **Why it's worth asking:** Both date boundaries are UTC midnights, while the inclusive end date becomes the following day's exclusive boundary (`backend/app/audience/service.py:798`, `backend/app/audience/service.py:800`). A manager's local September 1 can therefore straddle the selected interval.
  **Checked against:** ADR-188 Decision 4; completed task-296 choices (whole end day and relative-to-now); Audience Write Surface decision 7; business baseline P2-F2 (locale axis for channel content). P2-F2 concerns content/module locale and is not re-raised here. No timezone selection or absolute-date timezone decision was found in the duplicate corpus.
  **Suggested answer (for the maintainer to confirm or reject):** The implementation uses UTC calendar dates for every caller. There is no recipient or brand timezone input to `_engaged` (`backend/app/audience/service.py:752`); whether the editor's date wording should explicitly name UTC remains for the maintainer.
  **Resolution (2026-10-09): act / fix — dates are UTC days, and the editor says so.** The shift is a few hours at each end, which barely matters for engagement windows of weeks. A company time zone setting stays a later idea. Each manager's browser zone was rejected: one saved rule would mean different people depending on who opens it. Queued as task-337.

- [x] **Q3.** Should all relative-time predicates in one audience resolution share the same “as of” instant?
  **Why it's worth asking:** `_engaged` obtains `datetime.now()` separately on each invocation (`backend/app/audience/service.py:792`). `_resolve` evaluates blocks separately and, for arithmetic, evaluates includes again for the not-agreed count (`backend/app/audience/service.py:1256`, `backend/app/audience/service.py:1264`). At a moving boundary, logically complementary include and leave-out rules can use slightly different cutoffs.
  **Checked against:** ADR-188 Decision 4 and live-relative-window Notes; ADR-093 (derived rather than stored audiences); completed tasks-213, -214 and -296; Audience Write Surface decision 4 (live arithmetic). These settle on-demand calculation, but do not settle a common timestamp within a calculation. This is distinct from task-106's throughput benchmarks and task-124's concurrent writers.
  **Suggested answer (for the maintainer to confirm or reject):** Today each predicate takes its own timestamp; no common resolution timestamp is carried through `_recipients_for_criteria` to `_engaged` (`backend/app/audience/service.py:847`, `backend/app/audience/service.py:868`). Most audiences will not notice the difference, but the exact boundary semantics have not been recorded.
  **Resolution (2026-10-09): keep in poc — yes, one "as of" per resolution is right, but the gap is milliseconds** and only matters for an event exactly on a boundary. Cheap to fix (take `now` once in `_resolve` and pass it down) if someone is in `backend/app/audience/service.py` anyway; not queued on its own.

- [x] **Q4.** After a recipient opts in again, should an unsubscribe link from an earlier consent period be able to opt them out again?
  **Why it's worth asking:** `message_for` resolves any existing token without reference to consent age (`backend/app/subscriptions/service.py:52`). `_opt_out` checks only the latest cell status, and appends an opt-out whenever that status is no longer opted out (`backend/app/subscriptions/service.py:69`). An old link therefore remains effective after a later opt-in.
  **Checked against:** ADR-191 Decision 2 (non-expiring token) and Decision 4 (scope); ADR-163's event-cell design; completed task-56; business baseline M2 (pause/snooze), F1 (consent floor), P2-E1 (legal calibration); task-324 (signup/DOI) and task-135 (suppression reasons). None discusses distinct consent periods or re-use after re-subscription. This asks about interaction with a later grant, not whether tokens should generally expire.
  **Suggested answer (for the maintainer to confirm or reject):** Yes in today's code: the old token still names the person and creates a new latest marketing opt-out (`backend/app/subscriptions/service.py:98`, `backend/app/recipients/consent.py:134`). Confirm whether perpetual access to stopping mail intentionally survives re-subscription.
  **Resolution (2026-10-09): keep in project — yes, an old link still unsubscribes.** Stopping mail must always work (ADR-191 decision 2: tokens never expire, a link from last year still works); the worst case is one unwanted opt-out the person can undo. A later double opt-in or CRM re-sync design must not add "old links stop working after re-signup".

- [x] **Q5.** Does “everything we send” mean the brand/channel cells that exist now, or an enduring company-wide preference applying to future brands and channels too?
  **Why it's worth asking:** The operation iterates current brands and registered channels and writes ordinary marketing consent cells (`backend/app/subscriptions/service.py:94`). It does not store a separate company-wide refusal that a future grant must consult.
  **Checked against:** ADR-191 Decision 4; ADR-163 2026-09-15 addendum point 2; completed task-56; business baseline P2-A2 (brand-local lawful basis), F1; task-135 (unified suppression reasons). Those settle the current all-brands/all-channels option, not its temporal scope when dimensions are later introduced.
  **Suggested answer (for the maintainer to confirm or reject):** It is a snapshot operation over existing cells. A new brand/channel has no grant by default, so cannot send marketing merely because it was added; a later explicit opt-in can permit it under the cell model (`backend/app/subscriptions/service.py:94`, `backend/app/recipients/consent.py:139`). Confirm the promise intended by the recipient-facing phrase.
  **Resolution (2026-10-09): keep in project — "everything" means the company, now and later.** Fail-closed already covers brands and channels added later: with no consent record, nothing is sent. The remaining gap is a later automated grant (CRM sync, import) for a new brand to someone who said stop everything. That goes to task-135 (note added): store the company-wide refusal and make automated grants check it, while a fresh opt-in by the person still wins. Nothing built now.

- [x] **Q6.** What establishes that the configured unsubscribe URL is reachable HTTPS before a real marketing send is permitted?
  **Why it's worth asking:** `public_base_url` accepts the environment value without scheme validation and falls back to `http://localhost:8000` (`backend/app/subscriptions/service.py:25`). That URL is put into the outgoing email headers (`backend/app/delivery/providers/resend.py:61`), so a missing deployment setting can send a valid token at an unusable location.
  **Checked against:** ADR-191 Context (HTTPS one-click), Negative (public URL must be configured), Notes (environment variable); completed task-56; LAUNCH-GATES gate 10; business baseline H1 (worked real provider), P2-C1 (secret source mismatch). The variable and development fallback are decided; a production preflight or deployment verification responsibility is not specified there.
  **Suggested answer (for the maintainer to confirm or reject):** The code presently delegates reachability and HTTPS to deployment configuration. `footer_for` constructs the URL directly (`backend/app/subscriptions/service.py:49`); it does not verify the deployment address. Confirm what evidence an adopter is expected to obtain before sending.
  **Resolution (2026-10-09): act / fix — the real provider refuses a marketing send when `PUBLIC_BASE_URL` is unset or not https.** Today it silently falls back to localhost, and the link is fixed into each mail for good. Mock provider and development unaffected. Queued as task-330; the setting is named in task-55.

- [x] **Q7.** Does the rationale that the public unsubscribe route “does nothing costly” also hold for the company-wide option as brands and channels grow?
  **Why it's worth asking:** Each cell performs a latest-event query; if needed, it appends and flushes an event (`backend/app/subscriptions/service.py:69`, `backend/app/subscriptions/service.py:94`, `backend/app/recipients/consent.py:108`). Repeated successful requests still scan all existing cells even when already opted out.
  **Checked against:** ADR-191 Notes, rate-limit bullet: “the route does nothing costly”; Decision 4 (everything scope); completed task-56; business baseline P2-G2 (authenticated integrations lack budgets); task-106 (recipient send-pipeline benchmarks). This explicitly narrows the earlier no-cost claim to the newly exposed all-cell path; it does not re-ask P2-G2's authenticated-machine quota question.
  **Suggested answer (for the maintainer to confirm or reject):** The default operation is small, but the everything operation grows with brands × registered channels; it commits once after the loop (`backend/app/subscriptions/service.py:99`). Confirm whether that is considered acceptably bounded for the supported reference deployment. No limit or alternate policy is proposed here.
  **Resolution (2026-10-09): keep in project — still cheap.** "Everything" grows with brands × channels, which an administrator controls, not an attacker; it needs a real token and repeating it writes nothing new. A deployment with very many brands relies on the gateway rate limits task-55 already names.

### Verified defects — not interview questions

Verified behavior defects are filed as draft-2 (Resend timeout replay) and draft-3 (failed recipient outside the rerun audience).

- **High severity; reachable today:** A retry can mail a recipient removed from the audience after the first attempt. Reconciliation deletes out-of-audience rows only when `status == created` (`backend/app/delivery/service.py:662`). A definitive failed provider result leaves `failed` (`backend/app/delivery/service.py:1256`), and the later loop retries that row despite the resolved audience no longer including it. This undermines ADR-176 point 4 and the completed task-318 safe-retry work. Proven with actual reconciliation and full claimed-delivery function ASTs, a resolver returning no recipients, a failed execution, and a mocked provider: no row deleted, provider called, child becomes sent.
- **High severity; reachable today:** Real Resend network timeouts bypass the uncertain-outcome protection. `ResendProvider.send` catches `httpx.HTTPError`, including response timeouts after possible acceptance, and returns `success=False` (`backend/app/delivery/providers/resend.py:77`). `_deliver_claimed` therefore changes the child from sending to failed (`backend/app/delivery/service.py:1256`), and a later retry makes another vendor request. No idempotency key is supplied (`backend/app/delivery/providers/resend.py:68`). This overtakes completed task-318's stated policy that an uncertain result must never be resent. A mock `ReadTimeout` passed through the actual adapter and actual delivery loop produced failed/failed after one request, then sent after a second request on retry.

Proof harness: `/tmp/tarrow-delivery-premise-proof.py`, run using `backend/venv/bin/python`. It loads executable ASTs from current source, removes imports and annotations, and substitutes persistence, rendering, model symbols and network operations. No application startup, environment lookup, database operation or outbound request occurred. It proves state/control flow, not Postgres concurrency or vendor acceptance itself.

### Audit and stranded release: covered, no fresh interview prompts retained

Read `docs/architecture/Code/audit.md` first, then current audit source and ADR-153 Decision/addenda. The Code page's “never raises,” no DB trigger, unvalidated action/detail, services never audited and whole-transaction rollback descriptions are stale: write-time vocabulary/address checks, savepoints, strict actor lookup and service exceptions exist (`backend/app/audit/service.py:11`, `backend/app/audit/service.py:236`, `backend/app/audit/service.py:251`). These are resolved questions, not newly unreviewed decisions. Read the current delivery release source and ADR-192 before considering its prompts.

### Dropped as duplicates

- Why flat audience rules / negative conditions as subtraction / opens despite MPP / category OR thresholds? → ADR-188 Decision 1–5 and 2026-10-06 addendum; Audience Write Surface decisions 2/7; completed tasks-295, -296, -300.
- Why pins lose to exclusions / why every send resolves again? → ADR-176 Decision 1/4; Manager Workflow Cluster 4 Q8–Q10; delivery reconciliation implementation (`backend/app/delivery/service.py:577`).
- Why live arithmetic and memberships are derived rather than materialized? → Manager Workflow Cluster 4 Q3/Q5; completed tasks-213/-214; ADR-093.
- Why persist successful recipients and never resend uncertain ones? → Delivery, Providers, Recipients / Delivery Q3; completed task-318; ADR-192 Context. Only actual regressions reported above survive this check.
- Why no automated provider reconciliation? → Delivery Q3 resolution; task-81; ADR-192 Notes.
- Why person-only release / planner permission / 30-minute flag / why a live stalled provider can be released? → ADR-192 Decision 1–4 and Negative; completed task-325. The explicit residual liveness risk is not a new bug.
- What happens to a held request stranded in executing when its send is released? → ADR-192 Notes and ADR-142 2026-09-29 second addendum; not decided as new interview work here.
- Why random persisted token, no expiry, POST confirmation, anonymous route without CSRF, no rate limit, no transactional opt-out? → ADR-191 Decision 2–4 and Notes; completed task-56. D4/D7 concern narrower interactions not answered by those decisions.
- Why no unsubscribe interest contribution, CRM propagation or designed footer? → ADR-191 Notes/Decision 5; tasks-135/-301; task-305 for complaint signals. These remain named deferred boundaries.
- Why audit checks rather than enum columns, savepoint failure behavior, copy exemptions, actor forwarding, brand-less events in brand filter? → Channels, Audit / Audit Q1–Q5 resolutions; ADR-153 addenda 2026-10-01 and 2026-10-08; completed tasks-22/-23/-25/-52. Retention remains task-136.

### Coverage and limits

The sweep used module Code pages before source, git history of the owned modules since 2026-09-18, current source premises, completed-task implementation notes, and duplicate searches over every interview-prep file, both business interview documents, business documents/decisions, strategy decision log, open/completed tasks and every ADR Decision/addendum. Detailed checks above name the nearest substantive predecessors. Read source for current behavior rather than relying on CODE-REVIEW-BRIEF's already-overtaken open-bug list.

No `.env` read, application startup, migrations, seeding, provider change, dev database or outbound mail. No browser/live integration check or full test-suite run. The mocked proof cannot prove external acceptance or real lock scheduling. No audit/release question was padded into the doc merely to meet a per-module quota; duplicate suppression takes precedence. Source-module content, compositor, auth and client coverage belongs to the other sweep clusters.

## Client/CI duplicate drops


- Why React/Vite rather than Next.js, why same origin and cookies, why React Aria, why TanStack Query → ADR-168/170/173 and Manager Workflow introduction.
- Why autosave on blur, why version guards, why queue writes and re-read before the next save → Campaign Write Surface D1, task-110, task-255. The new retry question does not re-open these.
- Whether held requests must always expire → Manager Workflow Cluster 1 Q7; ADR-142 2026-09-24 addendum; task-210, now implemented.
- Why a machine readiness mark is held, why one request per channel, who receives publication attribution → Manager Workflow Q2.6b; ADR-174 and ADR-142 2026-10-08 addenda; task-206.
- Whether the approval claim can be released by the action's inner commit → ADR-142 2026-09-29 state-claim addendum; tasks 4 and 13.
- How a process crash strands an executing approval → newly present task-326; not raised anew.
- Why a machine cannot approve and why self-approval is action-specific → ADR-168 addendum, ADR-166, task-200.
- Whether a machine with write permission can read back what it wrote → Auth interview Q3; task-53; ADR-166 2026-10-08 addendum. This also settles delayed read-only permission design; no new question asks for it.
- Whether integration-management/settings writes may be performed by machines → ADR-166 2026-10-02 addendum and task-51/53 notes; deliberately person-only.
- Why hash locks, split runtime/dev, no blanket upgrades, provenance checks, the runtime-only blocking vulnerability policy, weekly scan frequency, small blocking lint set, security-rule widening → ADR-189/190 (including addendum), tasks 235/105/311. These are decisions, not fresh interview questions.
- Why greenlet must be declared across Mac/Linux → `requirements.in:11-15`, task-105 final implementation notes.
- Why CI exports the schema instead of starting an HTTP server → task-105 implementation notes and `export_openapi.py:1-9`; not restated.
- Whether a real browser test gap exists → task-302; not restated.

## Client/CI coverage, method and limitations

Read baseline command and pasted request, CLAUDE.md, current review brief, Code pages for manager-client/frontend/auth before source; examined bounded git history since 2026-09-18 for these clusters. Read relevant ADR Decisions/addenda. Duplicate scanning included every interview-prep file, both business interview files, business docs/decisions, the playbook decision log, and all open/completed task files. Candidate-specific matching passages were inspected; relevant tasks read through the CLI. This is a targeted duplicate sweep, not a claim to have manually read every unrelated prose paragraph.

Source inspected: auth guard/policy, approval service/models/router/actions, client auth/cache/serializer/fields/shortcuts, CI workflow and installed-package/schema-export scripts. No repository files changed, no environment file read, no migrations/seed/provider changes/mail executed. The standalone component probe required no database or network.

Not reached: exhaustive live HTTP authorization permutations; deployment refresh behavior in an actual browser; host merge rules; notification behavior; real CI execution; runtime response-contract validation. Approvals and CI lack dedicated Code pages. Removing an action plugin could make its pending requests unrejectable (resolver refusal and JSON reject share a gate), but no public-route reproduction was completed; retained only as an extension/removal limitation, not a defect claim or interview question. Installed-package equality reads package-manager metadata, not a content-integrity inventory of every on-disk file; that assurance boundary was observed, not tested or promoted to a bug/question. Other technical clusters belong to the parent/other delegates.

## Additional changed areas checked

Content catalogue writes/versioning, manifest field definitions, hidden-field rendering, and snapshot/reconstruction semantics were checked through Code pages and current source, the Variant Editor interview, Campaign/Content Write Surface and Element Hiding final passes, and ADR-177/179/180/183/186/187. Their new implementation follows already recorded resolutions; no fresh question was added merely to restate those choices. AI task discovery is implemented at `backend/app/ai/tasks/registry.py:30` and `:74`; the Code ai page explains its seam. Existing AI questions, P2-H findings and registry cleanup task-308 cover the prior concerns. Old empty `automation/` and `privacy/` implementation areas are business gaps already tracked, not technical module questions.

## Defect drafts

- draft-1 — unblurred editor draft replaced by a read refresh; real component probe outside the repository, moderate severity.
- draft-2 — actual Resend adapter catches an ambiguous timeout and makes the execution retryable; mocked current-function proof, high severity.
- draft-3 — rerun reconciliation retains failed work outside current membership; mocked current-function proof, high severity.

All drafts were created through the Backlog CLI with type bug, severity in the description, and no priority or ordinal. They are pre-stage findings; no fix was made. Unknown held-action removal remained an unproved conditional edge, not a filed defect. Approval crash recovery is already task-326, not another finding.

## What was not reached

No live browser refresh/deployment/shortcut collision test; no host merge-rules inspection; no real CI run; no real-provider timeout/acceptance test; no PostgreSQL concurrency or full-suite run. The probe limitations are recorded with each defect. No `.env`, development database, mail, migrations, seeds or provider switches were used. All repository writes in this sweep are pre-stage docs/drafts through the CLI.
