# FastAPI

## Purpose

FastAPI is the backend framework used by the reference implementation.

It provides the API layer between frontend applications, external systems and the internal architecture domains.

## Why Was It Chosen?

### API First Architecture

The reference architecture is built around APIs.

Every major architectural domain exposes capabilities through APIs.

FastAPI supports this approach natively.

### Automatic Documentation

FastAPI automatically generates OpenAPI documentation.

This allows developers to explore and test APIs without manually creating documentation.

### Python Ecosystem

Decision, Automation, Insight and AI-related capabilities are expected to benefit from the Python ecosystem.

Choosing FastAPI keeps the implementation aligned with future AI and data-processing requirements.

### Simplicity

FastAPI provides a lightweight framework with minimal overhead.

The project does not require the complexity of larger frameworks.

## Alternatives Considered

### Django

Rejected because it provides significantly more functionality than required.

The project does not require a full web framework.

### Express.js

Rejected because Python provides a stronger ecosystem for AI, analytics and decisioning capabilities.

## How Is It Used?

FastAPI exposes APIs for architectural domains such as:

- Content
- Campaigns
- Rendering
- Delivery
- Decision
- Automation
- Insight
- Privacy

Each domain exposes its own API routes.

## Architectural Impact

FastAPI supports:

- API First Architecture
- Modular Monolith implementation
- Future service separation
- Automatic API documentation
- AI integration through Python