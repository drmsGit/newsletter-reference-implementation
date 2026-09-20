# React

## Purpose

React is the library used to build the manager client.

The manager client is the screen a person uses to compose campaigns, manage audiences and approve sends.

React's job is narrow: it turns application state into what you see, and keeps the two in step when the state changes.

## Why Was It Chosen?

### The client is a form over an API

Every screen in the manager does the same thing.

It reads data from the JSON API, shows it, and sends back what the user did.

React is well suited to that and brings nothing that this job does not need.

### The backend already exists

The API was built first and is complete.

That means the client does not need a framework that also runs server code, because there is already a server.

### It is widely known

A reference architecture is meant to be read and copied by other people.

React is the most widely understood option, so the client is legible to the largest number of adopters.

### It is open source and free

ADR-171 requires that nothing needed to run this platform costs money.

React is MIT licensed and has no paid tier.

## Alternatives Considered

### Next.js

Rejected, and this was the reflex answer that had to be argued down.

Next.js earns its keep on server-side rendering, search-engine visibility, and content-heavy public pages.

The manager client has none of those: it serves no anonymous traffic, needs no search ranking, and sits entirely behind a login.

There is also a concrete conflict.

ADR-168 requires the client and the API to be served from the same address, which is what keeps the login cookie simple and keeps cross-origin configuration out of the backend.

Next.js is itself a server, so serving it would mean either running a second server process, which reintroduces exactly that problem, or exporting it as static files, which discards most of what Next.js is for.

**The public marketing website is a separate decision.** A tool rejected for an admin panel is not thereby rejected for a marketing site, and Next.js may well be the right answer there.

### Vue or Svelte

Not rejected on quality.

Both would do this job well.

React was chosen because more adopters will already know it, and legibility to the reader is the point of a reference architecture.

### Server-rendered HTML, as the backend already does

This is what exists today and what the client replaces.

It was rejected because the API and the UI had drifted into two separate route sets doing the same work, and every action had to be built twice.

A client that speaks the same JSON API an external system speaks makes that parity structural instead of maintained by hand.

## How Is It Used?

The client lives in `frontend/` beside `backend/`.

Screens are plain React components, and routing is handled by React Router as a library the application calls.

Nothing is derived from the filenames on disk; the list of routes is written out in `frontend/src/App.tsx`.

## Architectural Impact

React supports:

- A client that uses the same JSON API external systems use
- A static bundle the existing backend can serve with no second process
- Replacement of the server-rendered admin UI
- An adopter changing one dependency rather than one paradigm
