# Docker

## Purpose

Docker provides a reproducible runtime environment.

All developers should be able to run the reference implementation in a consistent way.

## Why Was It Chosen?

### Environment Consistency

Applications behave the same regardless of operating system.

### Simplified Setup

Developers do not need to manually install every dependency.

### Deployment Alignment

The same containers used during development can later be deployed to servers.

### Service Separation Readiness

Docker supports future separation into independent services.

## Alternatives Considered

### Native Installation

Rejected because environments become difficult to reproduce and maintain.

## How Is It Used?

Docker runs:

- PostgreSQL
- Backend APIs
- Future frontend applications
- Future worker processes

Docker Compose defines how components interact.

## Architectural Impact

Docker supports:

- Local development
- Reproducibility
- Deployment portability
- Future service-oriented architecture