# Git

## Purpose

Git provides version control for the reference implementation.

It tracks changes to code, documentation, architecture artifacts and implementation decisions over time.

## Why Was It Chosen?

### Industry Standard

Git is the most widely adopted version control system.

### Change Tracking

Every modification can be traced back to a specific point in time.

This supports transparency and architecture governance.

### Safe Experimentation

Developers can make changes without risking the stability of the project.

Previous states can always be restored.

### Architecture History

The project is not only software.

It is also a learning journey and architecture reference.

Git preserves this evolution.

## Alternatives Considered

### No Version Control

Rejected because architecture and implementation decisions would become difficult to trace and recover.

### Centralized Version Control Systems

Rejected because Git provides better flexibility and industry adoption.

## How Is It Used?

### Repository

The entire project is maintained in a single repository.

Contents include:

- Source Code
- Architecture Documentation
- ADRs
- Models
- Implementation Notes

### Commits

Changes are grouped into logical milestones.

Examples:

text Add Docker setup Add FastAPI setup Add Content domain skeleton Add PostgreSQL integration 

Commits should describe why a change was made rather than only what changed.

### GitHub

GitHub serves as the remote repository.

Benefits include:

- Backup
- Collaboration
- Public sharing
- Future open-source publication

## Important Concepts

### Working Directory

Files currently being edited.

### Commit

A snapshot of the project at a specific point in time.

### Repository

The complete project history.

### Push

Uploads local commits to GitHub.

### Pull

Downloads changes from GitHub.

## Architectural Impact

Git enables:

- Traceable architecture evolution
- Safe experimentation
- Documentation versioning
- Reproducible implementation history

Without Git, the reference implementation would lose a significant part of its educational and architectural value.