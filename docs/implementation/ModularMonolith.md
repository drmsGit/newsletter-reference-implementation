# Modular Monolith

## Purpose

The proof of concept is implemented as a modular monolith.

This minimizes operational complexity while preserving architectural boundaries.

## Why Was It Chosen?

### Faster Development

A single deployable application is easier to build and maintain.

### Lower Complexity

The project can focus on validating architectural assumptions rather than operating distributed systems.

### Learning Efficiency

The implementation serves as a learning platform for architecture validation.

## Alternatives Considered

### Microservices

Rejected for the proof of concept because operational complexity would outweigh the benefits.

## How Is It Used?

The application is separated into architectural domains:

- Content
- Campaigns
- Rendering
- Delivery
- Decision
- Automation
- Insight
- Providers
- Privacy

Each domain contains:

- Models
- Services
- API Routes

## Architectural Impact

The deployment model is a monolith.

The architectural model remains service-oriented.

Individual domains may later be extracted into independent services.