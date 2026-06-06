# Domain Structure

## Purpose

The implementation mirrors the architecture through domain-oriented code organization.

## Why Was It Chosen?

The project is intended to demonstrate architecture rather than technology.

Architectural domains should therefore remain visible inside the codebase.

## Structure

text backend/ ├─ content/ ├─ campaigns/ ├─ rendering/ ├─ delivery/ ├─ decision/ ├─ automation/ ├─ insight/ ├─ providers/ └─ privacy/ 

## Domain Pattern

Each domain follows the same structure:

text domain/ ├─ models.py ├─ service.py └─ router.py 

### Models

Define data structures.

### Services

Contain business logic.

### Routers

Expose APIs.

## Alternatives Considered

### Layer-Based Structure

Examples:

text models/ services/ controllers/ 

Rejected because architectural domains become difficult to identify.

## Architectural Impact

The code structure directly reflects the reference architecture.

This improves maintainability, onboarding and future service extraction.