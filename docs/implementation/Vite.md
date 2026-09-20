# Vite

## Purpose

Vite is the build tool for the manager client.

A browser cannot run the client's source code directly, because that source is written in TypeScript and JSX.

Vite turns the source into plain files a browser understands, and runs a fast development server while the code is being written.

## Why Was It Chosen?

### The deployment wants static files

ADR-168 makes the backend serve the client.

Vite produces exactly that: a folder of files with no process to run beside it.

### The development server is fast

Vite only rebuilds the file that changed, so a saved edit appears in the browser almost immediately.

This matters more than it sounds, because it is paid on every single change.

### It proxies the API in development

In production the client and the API are served from one address.

In development they are two processes, which would make the browser treat them as two different sites and break the login cookie.

Vite forwards API requests to the backend so the browser still sees one address, which preserves the property the production setup relies on.

### It is open source and free

Vite is MIT licensed with no paid tier, as ADR-171 requires.

## Alternatives Considered

### Create React App

Rejected because it is no longer maintained.

It was the standard way to start a React project for years, so it appears in most older tutorials, and choosing it today would mean adopting an unmaintained dependency.

### Webpack

Rejected because it requires substantial configuration to do what Vite does with almost none.

Webpack is more capable and that capability is not needed here.

### No build step at all

Genuinely considered, because it is the simplest thing that could work.

Rejected because it would mean giving up TypeScript, which is what stops the client and the API disagreeing about data shapes.

It would also mean the browser fetching several hundred small files instead of a few.

## How Is It Used?

`npm run dev` starts the development server on port 5173 and proxies API paths to the backend on port 8000.

`npm run build` produces the `frontend/dist/` folder that the backend serves.

The configuration lives in `frontend/vite.config.ts`, and the list of proxied paths there is taken from the backend's registered routes rather than written from memory.

## Architectural Impact

Vite supports:

- A static bundle with no second server process
- The same-origin requirement ADR-168 states
- A fast edit-and-see loop
- One toolchain for building and for testing
