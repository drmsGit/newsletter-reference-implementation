# TanStack Query

## Purpose

TanStack Query fetches data from the API and remembers the answers.

When two screens ask for the same thing, it makes one request and gives both the same answer.

When something changes, it marks the remembered answers as out of date and fetches them again.

## Why Was It Chosen?

### Switching brand has to clear everything

This is the reason it is here, and it is worth stating on its own.

A person working across several brands can switch which brand they are working in.

ADR-172 carries that working brand into every query the backend runs, so after a switch **every** answer already on screen describes the wrong brand.

With this library that is one line: mark the whole cache out of date and let the visible screens refetch.

Without it, that is remembering to clear the stored data of sixteen screens in one place, with nothing failing when somebody forgets.

The failure would be silent and would be the worst kind available: one brand's campaigns listed under another brand's name.

### Loading and error states come with it

Every screen needs to know whether data is on its way, arrived, or failed.

Writing that by hand is a small amount of code repeated on every screen, and it is where inconsistencies collect.

### Shared answers, without shared plumbing

Three separate parts of the shell need to know who is signed in.

Because they all ask for the same thing, they get one request and one answer, without any of them knowing about the others.

### It is open source and free

TanStack Query is MIT licensed with no paid tier.

## Alternatives Considered

### Fetching by hand in each screen

This is the default approach and it is what ADR-170 expected when it wrote down the cost of choosing a plain React application.

Rejected on the brand-switch requirement above.

That requirement turns a per-screen convenience into a correctness problem, and correctness problems with silent failures are the ones worth a dependency.

### Redux, or another general state library

Rejected because it solves a different problem.

Those tools manage state the application owns.

Almost all the state here is owned by the server, and the real question is when to ask the server again — which is what this library is about and what a general state tool leaves to you.

## How Is It Used?

One shared client is created in `frontend/src/main.tsx`.

`frontend/src/api/session.ts` holds the session query and the sign-in, sign-out and brand-switch actions.

Switching brand calls `invalidateQueries()` with no arguments, which means every key rather than a chosen list.

A list would be something somebody has to maintain as screens are added, and omitting one would fail silently — so the blunt version is the safe one.

A test asserts that this stays true, because it is the only reason this dependency is here.

## Architectural Impact

TanStack Query supports:

- A brand switch that cannot leave another brand's data on screen
- One request where several parts of a screen ask the same question
- Consistent loading and error handling across screens
- A second way of thinking about state, which a maintainer has to learn
