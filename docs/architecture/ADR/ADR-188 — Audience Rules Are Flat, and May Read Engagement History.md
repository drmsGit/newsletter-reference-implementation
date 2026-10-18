---
type: adr
status: accepted
topic:
  - architecture
  - audience
  - engagement
  - frontend
created: 2026-10-06
source:
  - "Design interview with the user, 2026-10-06, one question at a time (task-293)"
  - "[[Manager Workflow - design interview]] Cluster 5, question 6: no retry button, build a segment of who missed it"
  - "[[Audience Write Surface - final design pass]]"
depends_on:
  - "[[ADR-176 — A Negative Decision Outranks a Positive One]]"
  - "[[ADR-163 — Per-Channel Consent and Addressability]]"
  - "[[ADR-093 — Audience Intelligence Is Derived, Not Authoritative]]"
  - "[[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]]"
  - "[[ADR-055 — Separate Delivery Execution from Engagement Events]]"
  - "[[ADR-056 — Engagement Events as Foundation for Automation]]"
  - "[[ADR-160 — Channel Model and Composition]]"
enables:
  - "[[ADR-169 — Operational Flows Are Sequenced Variants, Not a Canvas]]"
---

## Status
Accepted

## Context

**The React client cannot create or edit an audience** (task-293). It shows a group's reach per channel and writes nothing. The server already has routes for groups, rule blocks and hand-picked members, and the Jinja pages use them as forms. An editor for those routes is mostly a picture of the rule language, so the rule language had to be settled first. That is this record. The rest of the editor is in [[Audience Write Surface - final design pass]].

**How an audience resolves today.** `_resolve` in `backend/app/audience/service.py` computes `((∪ include blocks) ∪ hand-added members) − (∪ exclude blocks)`, then applies the consent floor for the channel being resolved. The order is [[ADR-176 — A Negative Decision Outranks a Positive One]] point 1, and the floor is [[ADR-163 — Per-Channel Consent and Addressability]]. This record does not change either.

**A rule block's criteria are an untyped dict, and it fails open in two ways.**

- **Four keys are read: `language`, `status`, `category_id` and `min_score`.** `find_by_criteria` combines them with AND. Any other key is stored without complaint and ignored when the audience resolves. A typo such as `langauge` therefore produces a rule that matches more people than its author meant, and nothing says so.
- **A category with no `min_score` means "nearly everyone".** `find_by_criteria` defaults the threshold to `0.0`, and a recipient with no signal for the category reads as `0.0` too. "Interested in Beach" with no score therefore matches every recipient who has never shown any interest in Beach. The only people it leaves out are those whose signal is below zero, which in practice means an unsubscribe outweighs everything else (`"unsubscribe": -50.0` in `backend/app/insight/signals.py`). The content-driven suggestion already writes `min_score: 1.0` (`DEFAULT_SUGGESTION_MIN_SCORE`). A hand-written rule has no such default.

**A rule cannot read what has happened to someone** (task-215). All four keys describe who a recipient is. Engagement history is already stored. `DeliveryExecutionDB` holds one row per recipient per send, with its channel and a status of `sent`, `failed` or `excluded`. `EngagementEventDB` holds the provider's events against those rows, each with an `event_type` such as `click` or `open` and an `occurred_at`. The [[Manager Workflow - design interview]] (Cluster 5, question 6) has already chosen to depend on this. A failed send gets no retry button; the manager "builds a segment" of the people it missed. That segment cannot be written today. [[ADR-169 — Operational Flows Are Sequenced Variants, Not a Canvas]] also depends on it. Its point 3 makes the reminder a followup whose condition is "did not open", and its point 4 says followup conditions "speak the same predicates an audience rule block speaks". The vocabulary decided here is therefore the one followups will use as well.

**Opens are weak evidence, and how much they count is the company's call.** Apple Mail Privacy Protection fetches the open pixel whether or not anyone reads the mail ([[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]]), so the signal layer weighs an open at `0.0` by default (`backend/app/insight/signals.py`). That figure is a default the company may change, not a rule the architecture sets. A signal weight decides how much an open says about interest. Whether a manager may *select* people by an open is a separate question, and it is answered in point 4.

**Exclusion still means two different things, and the model still cannot tell them apart.** ADR-176 point 3 separates an editorial exclusion segment from a legal blocklist or suppression entry. Both are `kind="exclude"`, and task-231 remains blocked on the suppression data model. An editor that calls its exclusion section a "suppression list" would invite people to keep legal opt-outs there, which is the confusion point 3 warns about.

**The decision log carries it.** `docs/playbook-strategy.md` §5 has "2026-10-06 — The audience editor is decided", from the same interview, held one question at a time. This record does not depart from it.

## Decision

**1. Rules stay flat. A field takes one or more values.**
Values combine with OR inside a field ("is one of"). Fields combine with AND inside a rule. Include rules combine with OR. Exclusion rules subtract.

```
audience(channel) = consent floor(channel) applied to
                    ( (rule₁ ∪ rule₂ ∪ … ∪ hand-added) − (leave-out₁ ∪ leave-out₂ ∪ …) )

rule  = field₁ AND field₂ AND …
field = value₁ OR value₂ OR …
```

There are no nested condition groups. In every "X and (Y or Z)" seen so far, the OR sat inside a single field, and anything else could be written as two rules. Nested groups wait until a real case needs them. AI-suggested audiences may make them unnecessary altogether.

The user's example, from the Condor use case: *interested in Beach* AND *preferred departure airport is one of FRA, BER* is one rule. The airport field itself waits for task-294 (point 2).

**2. Today a rule has three kinds of field: language, status and category interest. Engagement (point 4) is added as a fourth.**
Language and status are chosen from the values that actually occur among the brand's recipients, not typed. Related data, meaning CRM attributes, sales data and product data, is out of scope until it has its own decision (task-294: synced and stored, or pulled when needed).

**3. A category-interest field always carries a minimum score.**
The editor fills it in as `1.0`, the same default suggested rules use. The server refuses a category with no score or with a score of `0`, so "interested in Beach" can never mean everyone.

The server validates every rule against the fields in point 2 and point 4. It refuses an unknown field, and its refusal names that field. Unknown fields are no longer stored.

**4. A rule may read engagement history.**
An engagement field states three things:

- **What happened:** received, opened or clicked.
- **To which mailing:** a specific send, any send of a campaign, or any send on the channel.
- **When:** either absolute ("between 1 and 15 September") or relative ("in the last 30 days", "more than 90 days ago").

It combines with the other fields of the same rule under point 1. "Interested in Beach and clicked any send in the last 30 days" is one rule.

**"Opened" is included, by the user's decision.** How much an open counts is the company's call: a company may give opens a signal weight. Marketing teams build reminders on opens, and the follow-up send already depends on them (ADR-169 point 3's first worked example is "did not open"). In the user's words, removing it is "not our call".

This closes task-215.

**5. "Did not" is an exclusion, not a negated field.**
"Received the spring email but did not click" is written as include *received (spring)* plus leave out *clicked (spring)*. "Who missed the failed send" is the original audience plus leave out *received (that send)*.

Each such case has exactly one way to say it, so the logic in point 1 stays flat. The editor explains this once to new users.

**6. Exclusion rules are editorial, and the editor says so.**
The two sections are headed **"Who's in"** and **"Leave out"**. Under "Leave out" the editor shows this line:

> Leaves these people out even if a rule or a hand-add includes them. People who opted out are never sent to anyway: that's consent, not this list.

The words "blocklist" and "suppression" do not appear, so nobody is led to keep a legal opt-out list as an exclusion. The distinction between the two is the one ADR-176 point 3 states and task-231 still owes the schema. This point gives it wording. It does not give it a data model.

## Consequences

### Positive

- **One readable logic.** OR inside a field, AND inside a rule, OR across rules, then subtract. A manager can read any audience from top to bottom, and the arithmetic (task-213) can show each part's effect.
- **Condor-style cases need no groups.** "Beach, departing from FRA or BER" is one rule.
- **Reminders and "who missed it" become rules, not features.** The retry button the Manager Workflow interview declined, and the reminder that ADR-169 turned into a followup, are both written with the same fields as any other audience.
- **A category rule can no longer silently mean everyone.** The score is always present and is never `0`.
- **Typos are refused.** A misspelt field is an error with its name in it, not a rule that quietly ignores a condition.

### Negative

- **A genuinely nested condition needs two or more rules.** If "X and (Y or Z)" cannot be written with the OR inside one field, it becomes "X and Y" plus "X and Z". The editor shows X twice, and a change to X has to be made twice.
- **Engagement rules read the tables that grow fastest.** Delivery executions and engagement events increase with every send and every event. Resolving an engagement rule therefore costs more as history grows, and the audience is re-resolved at every send (ADR-176 point 4). That cost needs indexes and measurement, and the task-106 benchmarks are where it will be measured. "Any send of a campaign" also joins from delivery executions through the send to the campaign.
- **"Opened" includes machine opens (MPP), by the user's explicit choice.** An "opened" audience counts more people than actually read the mail, and a "did not open" leave-out removes people who never saw it. The editor states this. It does not filter machine opens out.
- **Engagement data is only as complete as the provider's webhooks.** If a provider does not report an event, or a webhook is lost, the person does not match "clicked". Nothing in the rule shows that gap.
- **An engagement rule sees only the history the company keeps.** Retention periods are the company's decision ([[ADR-154 — Erasure and Retention]]), and erasure removes delivery executions and engagement events ([[ADR-154 — Erasure and Retention]] point 2). When those rows are pruned or erased, a rule such as "received the spring email" or "more than 90 days ago" matches fewer people, and no rule was edited.
- **Existing rule blocks with a category and no score change meaning when validation lands.** Today such a block matches nearly everyone. After point 3 it is refused. A migration or a one-time fix-up must decide what each one becomes, and that choice changes those audiences either way.

## Notes

- **The rest of the editor is in [[Audience Write Surface - final design pass]].** It covers hand-adds with a reason (task-217), pasting a list of people, refusing to delete a group that a send uses, one version token for the group with an audit entry on every write ([[ADR-180 — A Lock Is Advisory for a Person and Binding for a Machine]] point 2, [[ADR-153 — Audit and Accountability]]), and "Save rule". This record holds only the rule language.
- **Point 5 meets ADR-176 point 1, and the result is intended.** A "did not" condition is a leave-out rule, and a leave-out rule also removes hand-added people. A person hand-added to "received spring, did not click" who did click is therefore left out. This is the precedence ADR-176 chose: a negative decision outranks a positive one.
- **Point 5 constrains how ADR-169 can phrase a followup.** ADR-169 point 4 has followup conditions reuse the audience vocabulary, and point 3 words the reminder as "did not open". The vocabulary decided here has no negated field. A followup's "did not open" is therefore either the "if not" branch of an "opened" condition, which point 3 already describes, or received minus opened. Which of the two is not decided here. ADR-169 point 4 also mentions frequency and decay-state predicates. This record adds neither: an engagement field asks whether something happened, not how often.
- **"Received" means handed to the provider and not bounced. The user decided this on 2026-10-06.** Excluded and failed deliveries never count: an `excluded` one is by definition not a delivery (ADR-163 point 7), and point 5's "who missed the failed send" depends on `failed` not counting. A bounce removes the person. A confirmed "delivered" is not required, because not every provider reports one. [[Audience Write Surface - final design pass]] records the same answer.
- **A minimum score must be above 0, and that covers negative scores.** Point 3 names a missing score and a score of `0`. A negative minimum would match even more widely than `0`, because a missing signal reads as `0.0` and an unsubscribe contributes a negative signal. [[Audience Write Surface - final design pass]] settles it: the server refuses any minimum score that is not above `0`.
- **The follow-up send that point 4 cites is decided and not yet built.** As of 2026-10-06 no follow-up or reminder exists in `backend/app/` or `frontend/src/`. Its design is ADR-169 point 3. Its design pass is now filed as task-299. In the user's words, a follow-up is more than a reminder: it combines the audience builder with a next send, such as the next newsletter after X days, for the people chosen with include rules.
- **The not-agreed count now also reads engagement history.** Under [[ADR-163 — Per-Channel Consent and Addressability]]'s 2026-10-06 addendum, the arithmetic re-runs each include block with the consent gate reversed, and only the count leaves that query. Once include blocks can carry engagement fields, that count also reads the delivery and event history of people who have not agreed. The addendum accepted the same kind of cost for behavioural signals, and its reasoning carries over: nothing about any individual leaves the count.
- **Still derived, still not authoritative.** A hand-written engagement rule is a filter over the platform's operational record. It is not the Audience Intelligence of [[ADR-093 — Audience Intelligence Is Derived, Not Authoritative]], and resolution results are still not stored. A rule with a relative window ("in the last 30 days") is a standing definition whose members change every day. That fits [[ADR-123 — Audience Ownership Depends on Reuse]], which places temporary and campaign-specific audiences in this layer and long-lived reusable ones in the CRM ([[ADR-120 — CRM as Customer Source of Truth]]).
- **Not a supersession, and no record's Decision changes.** ADR-176 point 3 gains wording from point 6 but keeps its statement that the schema cannot express the distinction. A short dated addendum on ADR-176 is proposed in the report that came with this record. It is not applied here.
- **The decision log carries it.** `docs/playbook-strategy.md` §5 has the entry "2026-10-06 — The audience editor is decided". That entry's points 2 and 3 summarise this record's rule language, point 1 carries the "Who's in" and "Leave out" sections, and point 6 is the task-294 boundary. This record does not depart from it.

## Addendum 2026-10-06 — Category interest takes several categories, each with its own score

**What prompted it.** The user used the new React audience editor (task-297) on the day this record was accepted. They built a rule: language de, status active, category Nature ≥ 5. They then wanted to add Wellness ≥ 5, and could not, because category interest took one category per rule. A second rule with only Wellness would also bring in every other language and status. So "de and active and (Nature or Wellness)" had to be written as two rules, each repeating "de, active".

That contradicts point 1: "a field takes one or more values". The first build kept category interest single-valued in two places:

- the server's criteria check, `normalise_criteria` in `backend/app/audience/service.py` (task-295);
- the editor's rule form, `frontend/src/screens/AudienceRules.tsx` (task-297).

This section applies point 1 to category interest. It is not a new rule. The user decided it in chat on 2026-10-06.

**1. A category-interest field takes one or more categories.** They combine with OR inside the field, as point 1 says. A person matches when they clear the threshold in any one of the listed categories.

**2. Each category has its own minimum score.** "Nature ≥ 5 or Wellness ≥ 3" is one field. Point 3 holds per category: every listed category carries a score, the score must be above `0`, and the editor fills in `1.0`.

**3. The shared condition stays in the rule.** The user's example is one rule: language de, status active, category interest Nature ≥ 5 or Wellness ≥ 5.

**Settled in the final design pass.** These follow from points 1 to 3 above. They were not asked of the user separately.

- **Stored shape.** A rule's criteria store category interest as a list: `categories: [{category_id, min_score}, …]`. Stored rules are always the list. A migration rewrites the existing rules.
- **The old single pair is still accepted as input.** A `category_id` with a `min_score` is normalised to a one-entry list. This keeps the Jinja form and existing integrations working. It is the same courtesy the group's version token gives them: a caller that sends none is still accepted ([[Audience Write Surface - final design pass]]).
- **Suggested rules keep one category each.** "Recalculate from campaign" (`recalculate_suggested_blocks`) applies only the difference per category. It keeps matching a suggested rule by its single category, so suggestions are never merged into one rule. Recalculation stays manual, as [[Manager Workflow - design interview]] Cluster 4, question 7 decided.

**Recorded, not built: an "Everyone must also" section.** A third section beside "Who's in" and "Leave out" would hold conditions that apply to every "Who's in" rule. That gives "X and (Y or Z)" across different fields without nested groups. The example: German speakers who are Nature fans, or who clicked the last issue.

- Point 1 says nested groups wait until a real case needs them. This section is the planned next step when such cross-field ORs appear in real use.
- Engagement in the editor (task-298) is the most likely source of them.
- Taking that step would change point 1, so it needs its own decision when the time comes: a further addendum or a superseding record.

**Consequences.**

- **Fewer cases need the repeated condition.** Point 1's Negative, "a genuinely nested condition needs two or more rules", now covers only ORs across different fields. An OR across categories is one field, as an OR across languages already was.
- **Every reader of a stored category changes with the migration.** Code that reads `category_id` or `min_score` from stored criteria must read the list instead. That includes resolution, the criteria preview and the suggested-rule matching above.
- **A complement is not the pattern for the shared condition.** "Leave out en, fr, nl" in place of "language de" silently lets in people with no language and any language that appears later. It also makes the rule read as the opposite of what it means.

Nothing here changes the Decision section above.

## Addendum 2026-10-18 — a suggested audience is made per variant: its topics and its language

**What prompted it.** The system can suggest an audience from content. Two buttons do this: "Suggest from campaign" on Audiences, and, since 2026-10-18, "Suggest an audience…" on a campaign's page. Both build one include rule per top category of the *campaign's* content. They read every variant, whatever its channel. The code is `campaign_category_scores` and `suggest_include_blocks_for_campaign` in `backend/app/audience/service.py`.

That was a choice of 2026-09-18. The user had asked whether a suggestion should check channels. The answer cited the principle of [[ADR-160 — Channel Model and Composition]] point 4: the campaign is the topic, and the channel is a delivery preference. The choice was recorded in the code's docstrings, not in a Decision.

On 2026-10-18 the user raised a gap. An English variant and a German variant of one campaign suggest the same audience. Yet each should reach readers of its own language. Two variants can also carry different content. The business decision on multilingual newsletters already says each language is its own variant, sent to an audience filtered by language (P2-F2, `docs/playbook-strategy.md` §5). The suggestion did not follow it.

The user decided the following on 2026-10-18, in a session.

**1. A suggestion is made for one variant.** The entry point is each variant on the campaign page ("Suggest an audience…"). "Suggest from campaign" on Audiences stays campaign-wide for now. It takes topics from every variant, sets no language, and says so.

**2. Its topics come from that variant's content only.** That means the modules bound to content records and the resolved picks of its decision slots. Ranking is as today: the top five categories, the same default minimum score, one include rule per category.

**3. Every suggested rule carries the variant's language.** The language is the language of the variant's brand profile ([[ADR-194 — Brand Profiles Carry an Email's Look, Texts and Legal Details]] point 6: one profile per language). It goes into each rule as its language field. It must sit inside each topic rule because of point 1: fields combine with AND inside a rule, and include rules combine with OR. "Interested in Hiking AND language is de" is one rule. A separate rule "language is de" would add every reader of that language.

**4. The channel stays out of the suggestion, as before.** The group resolves against each channel's consent at send time ([[ADR-163 — Per-Channel Consent and Addressability]]). Its counts are asked with the channel in hand ([[ADR-176 — A Negative Decision Outranks a Positive One]] point 5). A push variant's suggestion is its topics and its language.

**5. A suggested group remembers its source variant.** A new nullable reference sits beside its source campaign. Recalculating its suggested rules follows the variant when one is recorded: its topics and its language. Otherwise it follows the campaign.

**6. What this revises.** It revises the 2026-09-18 choice that a suggestion reads every variant of the campaign. ADR-160's principle stands for the model: there is no channel layer, and the campaign is the topic. A suggestion is about who receives one variant. That is the variant's content, in its language.

**Consequences.**

- *Positive:* a German variant and an English variant get audiences in their own language. A variant whose content differs gets its own topics.
- *Negative:* two variants of one campaign may get two near-identical groups. The manager deletes one or reuses it.
- *Negative:* the suggestion is per variant, while the entry on Audiences stays campaign-wide until it is changed.
- *Negative:* a migration adds the source-variant column.

Nothing here changes the Decision section above.

## Related ADRs

### Depends On
- [[ADR-176 — A Negative Decision Outranks a Positive One]]
- [[ADR-163 — Per-Channel Consent and Addressability]]
- [[ADR-093 — Audience Intelligence Is Derived, Not Authoritative]]
- [[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]]
- [[ADR-055 — Separate Delivery Execution from Engagement Events]]
- [[ADR-056 — Engagement Events as Foundation for Automation]]
- [[ADR-160 — Channel Model and Composition]]

### Enables
- [[ADR-169 — Operational Flows Are Sequenced Variants, Not a Canvas]]

### Referenced By
- [[ADR-123 — Audience Ownership Depends on Reuse]]
- [[ADR-120 — CRM as Customer Source of Truth]]
- [[ADR-154 — Erasure and Retention]]
- [[ADR-153 — Audit and Accountability]]
- [[ADR-180 — A Lock Is Advisory for a Person and Binding for a Machine]]
