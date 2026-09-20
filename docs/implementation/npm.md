# npm

## Purpose

npm installs the client's dependencies and records exactly which versions were installed.

It is to the frontend what `pip` and `requirements.txt` are to the backend, with one important difference described below.

## Why Was It Chosen?

### It comes with Node

Anyone who has Node installed already has npm.

The whole instruction for an adopter is therefore `npm install`, with no tool to fetch first.

A package this project hands to somebody else should not require installing something before it can be built.

### It records exact versions

`package.json` lists roughly what is wanted, such as "any version 5 of TypeScript".

`package-lock.json` records exactly what was installed, down to every indirect dependency, and that file is committed.

Two people installing a month apart therefore get identical code.

**This is stricter than the backend currently is.** `backend/requirements.txt` pins no versions at all, so two installs there can legitimately differ.

### Installing runs code, so the record matters

Packages are allowed to run scripts when they are installed.

That makes the lock file a security boundary and not only a convenience, because it is what stops an unreviewed version running on a machine.

### It is open source and free

npm's client is Artistic-2.0 licensed, and using the public registry requires no account.

## Alternatives Considered

### pnpm

Genuinely better on the technical merits.

It installs faster, uses far less disk by sharing one copy of each package across projects, and is stricter about code using packages it did not declare.

Rejected because an adopter would have to install pnpm before they could build the thing they just cloned.

That is a small cost, paid by every reader, to save time this project does not spend.

### Yarn

Rejected because it offers no advantage here over npm, and its current versions introduce conventions an adopter would have to learn.

It was the main alternative to npm historically, which is why it appears in older documentation.

## How Is It Used?

`npm install` in `frontend/` installs everything.

`npm run dev`, `npm run build`, `npm run test` and `npm run check:contract` are defined in `frontend/package.json`.

Installed packages live in `frontend/node_modules/`, which is not committed — the lock file is the record, and `node_modules` is the checkout.

## Architectural Impact

npm supports:

- A clone-and-install path with no tool to fetch first
- Exact, reproducible installs via a committed lock file
- A dependency list that ADR-171's licence rule can be checked against
- A second dependency tree, with its own updates, beside the Python one
