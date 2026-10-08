---
type: adr
status: accepted
topic:
  - architecture
  - decision
  - rendering
created: 2026-06-01
modified: 2026-10-08
source:
  - interview-2026-06-01
  - "[[Variant Editor - design interview]] Cluster 4, question 5, and gap 24 (2026-09-26)"
  - "task-228 notes: design settled with the user, 2026-09-28"
  - "Interview with the user, 2026-10-08, three answers (addendum)"
depends_on:
  - "[[ADR-084 — Decision Slots May Resolve One or Multiple Content Records]]"
enables:
  - "[[ADR-061 — Snapshot Based Final Rendering]]"
---


## Status

Accepted

## Context

A Decision Slot may not always find suitable content.

Mandatory fallback content would reduce the automation benefit.

## Decision

If no suitable content is found, the Decision Slot may be hidden.

If no meaningful newsletter content remains, the email must not be sent.

Fallback content is optional.

## Consequences

### Positive

- avoids irrelevant fallback content
- reduces manual preparation effort
- prevents empty or meaningless emails

### Negative

- sendability checks are required

## Addendum 2026-10-08 — What "meaningful" means, and the part a manager chooses

**What prompted it.** The Decision says the email must not be sent when no meaningful content remains. It does not say what "meaningful" is. Nothing in the send path checks it. `send_send_instance` in `backend/app/delivery/service.py` applies only the pre-send exclusion stack. An empty slot is hidden and the send carries on.

[[Variant Editor - design interview]] Cluster 4, question 5 (gap 24) gave a first answer on 2026-09-26. It said: meaningful means at least one module produced output beyond the envelope and the decorative modules. On 2026-09-28 the user corrected it, in the notes of task-228. The correction rests on three cases:

1. A focused email: hero, editorial and cta, no slots. It ships. Correct.
2. The same email plus one personalised block. The slot finds nothing, the block hides, the email ships. Correct: the block was a bonus.
3. Hero, editorial and three slots, where the slots are the point. Nothing resolves. The Q4.5 rule ships it, because the hero rendered. The user: *"it shouldn't be sent to people that actually don't have any resolutions."*

The system cannot tell case 2 from case 3. In both, static content rendered and the slots did not. The difference is whether the personalised blocks were the point or a bonus. That is intent. [[ADR-174 — Channel Readiness Is Asserted, Not Computed]] says no computation over the data can see intent. So this is a choice to ask the manager for, not a heuristic to tune.

The rest was settled with the user on 2026-10-08. This section records it. Nothing here changes the Decision above.

**1. The check is per recipient, at send time, after rendering.**
"The email must not be sent" means that email, to that person. Compose time and preview cannot know, because slots resolve per recipient. A send to a thousand people does not abort because one of them resolved to nothing. That one recipient is skipped.

**2. The floor always applies. It is not a manager's choice.**

- A recipient is skipped when nothing but the envelope rendered.
- For email, the envelope is the header module, which holds the subject and the preheader. The manifests already mark it: its fields declare `envelope`, and `envelope_module_type` in `backend/app/modules/registry.py` finds it.
- For push, there is no envelope module. The floor means an empty notification.
- Every other module that produced output counts as meaningful. That covers typed-in content, a catalogue record, and a slot that found something.
- An empty slot does not count. Nor does an unbound module or an unknown module.
- There is no "decorative" marker today, because no footer or divider module exists. The only structural module is the email header, and the envelope attribute already identifies it. When a decorative module is added, it gets a manifest marker then, decided at that time.

This also closes a gap on push. A push whose only slot found nothing went out as a blank notification. The comment in `backend/app/rendering/renderers/push.py` says the send path must refuse it. Nothing did.

**3. An option per send, set at plan time, default off: "Don't send if no slot resolved."**

- It skips a recipient whose slots all came up empty, even though static content rendered. This is case 3.
- It is per send, not per variant. The same variant may be sent once where the personalised blocks are the point, and once where they are a bonus. That is intent, and no computation can see it (ADR-174).
- It is off by default, because "the block was a bonus" is the common case.
- It applies only when there was something to resolve. A variant with no slots is never skipped by the option. A focused email with no slots always ships.
- It is stored as a column on the send (`SendInstanceDB`) and set when the send is planned.
- It is offered on the JSON plan route (`SendPlanRequest`) and as a checkbox on the existing server-rendered plan form. Today that form is the only place a person plans a send. React send planning takes the option over when it is built.

**4. Both skips are recorded with the other exclusion reasons, as two different reasons.**

- The execution's status is `excluded`. The reason goes in `exclusion_reason`, under a new stage, `render`, in the existing "stage: reason" form.
- The send's detail groups reasons by the stage before the colon. The recipient page shows the reason too. So both surfaces show the skip with no second place to look. "Why didn't this person get it?" has one answer surface.
- The two reasons, as the user worded them:
  - the floor: "render: nothing to show — no module produced content for this person"
  - the option: "render: no personalised block found anything for this person"
- They are two facts. Only the second one says something about the rule.
- The `render` stage is not part of the exclusion stack in `backend/app/delivery/exclusion.py`. That stack runs before the send loop, and this check needs the rendered result. Its reasons land in the same column all the same.

**Deliberately not touched.**

- A test send (`send_test_email`) still sends. Its purpose is to show what someone would get, including an empty result.
- The pre-send safety-net bundle (task-104) is not changed or decided here.

**Consequences.**

- The floor holds for every send and cannot be turned off. A recipient whose email would carry only a subject and preheader, or whose push would be blank, is never sent to.
- Case 3 becomes expressible. A manager who planned the personalised blocks as the point can say so, per send.
- The option is one more choice at plan time. A manager who forgets it in case 3 still ships hero-only emails. That is the cost of default off.
- `SendInstanceDB` gains a column, and the plan form, `SendPlanRequest` and the plan service gain a field. A migration is owed for the column.
- `exclusion_reason` now carries values that the exclusion stack does not produce. Anything that reads the stage from it must accept `render`.
- When a footer or divider module is added, the floor is wrong until that module gets its marker. A recipient who gets only header and footer would pass the floor. Adding such a module must therefore include the marker decision.

## Related ADRs

### Depends On

- [[ADR-084 — Decision Slots May Resolve One or Multiple Content Records]]

### Enables

- [[ADR-061 — Snapshot Based Final Rendering]]
