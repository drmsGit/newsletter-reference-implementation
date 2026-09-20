# TypeScript

## Purpose

TypeScript is JavaScript with type annotations.

It checks, before the code runs, that values are used the way they are meant to be.

In this project its main job is to make the client and the backend agree about the shape of every request and response.

## Why Was It Chosen?

### The API contract is checked at build time

The client's types are generated from the backend's own API description.

That means asking for a field the API does not return, or sending a body of the wrong shape, is a build error rather than a bug a user finds.

This is the mechanism ADR-170 relies on when it says the contract cannot silently fork.

### Mistakes surface where they are made

Without types, a renamed field fails at the moment a user opens the screen that reads it.

With types, it fails in the editor of the person who renamed it.

### It is the ordinary choice

Most React projects an adopter has seen will use TypeScript.

Choosing plain JavaScript would be the surprising decision and would need more explaining than this one.

### It is open source and free

TypeScript is Apache-2.0 licensed with no paid tier.

## Alternatives Considered

### Plain JavaScript

Rejected because it gives up the one property that makes the generated client worth generating.

The client's types exist so that a backend change cannot silently disagree with the client.

In plain JavaScript there would be nothing to check them against, and the generated file would be documentation rather than a guarantee.

### Runtime validation instead of types

This means checking data shapes while the program runs, rather than before it is built.

It was not chosen as a replacement because it finds problems later and costs work on every request.

It remains a reasonable addition later for data that genuinely arrives unpredictably.

## How Is It Used?

Every file in `frontend/src/` is TypeScript.

`frontend/src/api/schema.d.ts` is generated from the backend and is not written by hand.

`npx tsc -b` checks the whole client, and the build runs it first.

**The version is pinned to 5 on purpose, and the pin is load-bearing.**

TypeScript 7 is a rewrite of the compiler, and the tool that generates the client's types does not yet work with it.

The trap is that the ordinary build still succeeds on 7 — only the type generator breaks — so upgrading would not fail loudly.

It would disable the check that keeps the client and the backend in agreement, and nobody would notice until the next time somebody ran it.

This is recorded in `docs/backlog.md`, and the pin should be removed once the generator supports 7.

## Architectural Impact

TypeScript supports:

- A generated API client that is checked rather than trusted
- Backend changes surfacing in the client at build time
- Refactoring with the compiler finding the call sites
- One pinned dependency that must be reviewed before upgrading
