# Typed API Client

## Purpose

The client's knowledge of the API is generated from the API itself.

The backend publishes a machine-readable description of every route, at `/openapi.json`.

Two tools turn that into something the client uses: `openapi-typescript` generates the type definitions, and `openapi-fetch` makes requests that are checked against them.

## Why Was It Chosen?

### The contract cannot silently drift

This is ADR-170's central claim and this is the mechanism behind it.

If the types were written by hand there would be two descriptions of the same API, and they would disagree eventually without anything failing.

Because they are generated, a backend change that the client has not caught up with is a build error.

### The generated file is readable

`openapi-typescript` produces type definitions only — one file describing shapes.

It does not generate hundreds of functions.

For a project meant to be read and copied, the generated artefact being legible is a requirement rather than a preference.

### One place attaches the security header

Every write must carry an `X-CSRF-Token` header, which proves the request came from the application rather than from another site.

`openapi-fetch` allows one function to see every outgoing request, so the header is attached in exactly one place and no screen can forget it.

### It is open source and free

Both tools are MIT licensed with no paid tier.

## Alternatives Considered

### Writing the types by hand

Rejected because it creates a second description of the same contract.

The first thing to drift would be the channel fields the architecture took care to get right, and nothing would fail when it did.

### Generating a full client library

Tools exist that generate one function per API route, not just the types.

Rejected because the generated output becomes large and has to be re-read on every regeneration.

The thin approach keeps the generated part to one file of shapes, and the code that calls the API stays written by people.

### Using `fetch` directly with no types

Rejected for the same reason as writing types by hand, with the additional cost that there would be nothing to check the URL or the request body against.

## How Is It Used?

`npm run generate:client` regenerates `frontend/src/api/schema.d.ts` from the running backend.

That file is committed, which is what gives `npm run check:contract` something to compare against — it regenerates and fails if the result differs.

`frontend/src/api/client.ts` creates the one client used everywhere and attaches the security header.

Its base address is deliberately empty, which makes every request relative and therefore same-origin, as ADR-168 requires.

## Architectural Impact

The typed client supports:

- A client and a backend that cannot disagree without failing a check
- One place where the security header is attached
- A check that can be run in an automated build
- A dependency on the generator, which must keep working for the guarantee to hold
