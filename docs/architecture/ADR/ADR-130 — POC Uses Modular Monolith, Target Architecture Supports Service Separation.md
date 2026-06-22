---
type: adr
status: accepted
topic:
  - architecture
  - implementation
  - poc
created: 2026-06-06
modified: 2026-06-06
---
## Status

Accepted

## Context

The reference architecture is designed around clearly separated architectural domains such as Content, Composition, Rendering, Delivery, Decision, Automation, Insight, Provider and Privacy.

For the first proof of concept, implementing each domain as a separate service would add unnecessary operational complexity.

At the same time, the implementation should not become a tightly coupled application that prevents later service separation.

The project aims to validate the architectural assumptions through working software rather than continuing architecture work without implementation feedback.

The initial implementation should therefore optimize for simplicity, development speed and learning while preserving the boundaries required by the target architecture.

## Decision

The proof of concept will be implemented as a modular monolith.

The target architecture continues to support separation into independent services.

The selected technology stack for the proof of concept is:

### Frontend

- React
- TypeScript

### Backend

- Python
- FastAPI

### Data Storage

- PostgreSQL

### Runtime & Deployment

- Docker

### AI Integration

The architecture must support interchangeable AI providers.

Possible future implementations include:

- Local AI models
- European AI providers
- OpenAI-compatible providers
- Self-hosted models

The proof of concept must not depend on a specific AI vendor.

The codebase must be organized according to architectural domains.

Example:

>backend/
├─ content/
├─ campaigns/
├─ rendering/
├─ delivery/
├─ decision/
├─ automation/
├─ insight/
├─ providers/
└─ privacy/

The modular monolith is considered a deployment model rather than an architectural model.

Architectural boundaries must remain explicit even when deployed as a single application.

## Consequences

### Positive

- Faster local development
- Lower operational complexity
- Easier debugging
- Lower infrastructure cost
- Simpler onboarding
- Easier architecture validation
- Clear migration path toward independent services

### Negative

- Requires discipline to maintain domain boundaries
- Future service extraction may require refactoring
- Independent scaling of architectural domains is not initially possible

## Local Development Environment

The proof of concept will initially be developed entirely locally.

No cloud infrastructure is required during the first implementation phase.

### Required Software

| Purpose | Tool |
|----------|----------|
| Code Editor | VS Code |
| Version Control | Git |
| Frontend Runtime | Node.js LTS |
| Backend Runtime | Python 3 |
| Container Runtime | Docker Desktop |
| Database | PostgreSQL (Docker) |
| Database Client | DBeaver |
| API Testing | Bruno |
| Local AI Runtime (optional) | Ollama or equivalent |

### Installation Order

1. VS Code
2. Git
3. Node.js LTS
4. Python 3
5. Docker Desktop
6. DBeaver
7. Bruno
8. Optional local AI runtime

## Initial Project Structure

>newsletter-poc/
├─ frontend/
├─ backend/
├─ docs/
├─ docker-compose.yml
└─ README.md

### Backend Structure

>backend/
├─ content/
├─ campaigns/
├─ rendering/
├─ delivery/
├─ decision/
├─ automation/
├─ insight/
├─ providers/
└─ privacy/

## Planned Implementation Sequence

### Phase 1

Local development environment

### Phase 2

Project skeleton

### Phase 3

Core data model

- Content Record
- Category
- Campaign
- Variant
- Module Instance
- Decision Slot
- Decision Resolution
- Snapshot
- Send Instance
- Engagement Event

### Phase 4

Content Catalog and Decision Slot proof of concept

### Phase 5

Rendering and Snapshot proof of concept

### Phase 6

Signals and Recommendation proof of concept

### Phase 7

Provider simulation and event processing

### Phase 8

Deployment to VPS infrastructure

## Notes

The modular monolith is a deployment decision for the proof of concept.

It is not a rejection of the service-oriented target architecture.

The long-term architecture continues to support independently deployable services for Content, Decision, Automation, Rendering, Delivery, Provider, Insight and Privacy domains.