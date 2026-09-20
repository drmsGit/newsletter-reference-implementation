# React Aria Components

## Purpose

React Aria Components supplies the interactive controls the manager client is built from.

That means dialogs, dropdown menus, selects, tabs, checkboxes, tables and similar.

It supplies how they behave and not how they look: every visual rule in this client is written here, in plain CSS.

## Why Was It Chosen?

### The hard part of a control is not its appearance

A dropdown that looks right is easy.

A dropdown that closes on Escape, traps the keyboard while open, returns focus where it came from, announces itself to a screen reader, and behaves on a touch device is not.

That is the part this library provides, and the part that is silently wrong when it is written by hand.

### Nothing in this project would catch an accessibility mistake

There is no test here that would fail if a dialog trapped focus incorrectly.

This project's standard is that a claim is worth the test that proves it, so accepting a claim nothing can check was the wrong trade.

Buying the behaviour from people who test it is the honest alternative.

### It imposes no design

The management interface is themed through a small set of CSS custom properties, decided in ADR-170.

A library with its own design system would have to be overridden into that arrangement rather than dropped into it.

### It has an accessible table

This is what decided the choice, and it was not the obvious factor.

The manager client is mostly lists — campaigns, content, audiences, deliveries, approvals.

React Aria is the only option considered that supplies an accessible table, grid and tree under a licence that costs nothing.

## Alternatives Considered

### Radix UI

The reflex answer, and rejected on evidence rather than reputation.

Measured in September 2026: releases stopped for roughly ten months between August 2025 and June 2026, the most recent commits are all by a single employee of one company, and over 150 proposed changes are waiting.

It also has no combobox — a text field you can type into to search a list — and that has been declined repeatedly rather than left pending.

An admin application needs exactly that control for choosing content, audiences and providers, so Radix would have meant a second component dependency for the control most screens need.

### Base UI

**Rejected, and it was the recommendation.**

It is the healthiest of the options by a clear margin: released properly in December 2025, updated monthly, maintained by several people including those who originally built Radix.

It lost on one thing.

It has no table, and the natural next step within its family is a commercial product whose useful tier is paid.

ADR-171 requires that nothing needed to run this platform costs money, so that was disqualifying.

This is the first dependency that rule has ever refused, which is the rule working as intended rather than a problem.

### A complete component library, such as Mantine

Rejected because it is a design system an adopter inherits.

ADR-170 argues that an adopter who wants something different should be changing a dependency rather than a paradigm.

With a full library, replacing it means rewriting every screen, so that claim would stop being true.

### Building the controls by hand

Rejected for the reason in the second section above.

The accessibility cost is real, invisible, and nothing in this repository would detect it.

## How Is It Used?

Controls are imported from `react-aria-components` and styled with the project's own CSS in `frontend/src/index.css`.

The brand switcher and the sign-in form are the first two users.

**Two things to know before relying on it.**

Its notification component is still marked unstable after roughly eighteen months, so the first screen that needs one will have to choose between an unstable interface and writing that one control by hand.

Its licence is Apache-2.0 rather than MIT, which satisfies ADR-171 but is the first non-MIT dependency here, and some organisations review Apache-2.0 where they would wave MIT through.

## Architectural Impact

React Aria Components supports:

- Keyboard and screen-reader behaviour this project could not otherwise verify
- Accessible tables for the list screens that make up most of the client
- A visual design owned entirely by this project's own CSS
- A first Apache-2.0 dependency, and one control still marked unstable
