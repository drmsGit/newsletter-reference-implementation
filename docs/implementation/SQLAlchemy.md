# SQLAlchemy

## Purpose

SQLAlchemy is used as the database access layer between FastAPI and PostgreSQL.

It allows the application to work with Python objects while storing data in relational database tables.

## Why Was It Chosen?

### Separation Between Application and Database

The application should not contain raw SQL statements throughout the codebase.

SQLAlchemy provides a structured way to map application models to database tables.

### Fit for Relational Data

The reference architecture contains many related entities, such as:

- Content Record
- Category
- Content Category Assignment
- Campaign
- Variant
- Module Instance
- Decision Resolution
- Engagement Event

These relationships are well suited for a relational database model.

### Compatibility with PostgreSQL

SQLAlchemy works well with PostgreSQL and keeps database access explicit and testable.

### Future Migration Support

The current proof of concept creates tables automatically.

Later, database migrations should be handled with a dedicated migration tool such as Alembic.

## Alternatives Considered

### Raw SQL

Rejected for the initial implementation because it would spread database logic across the codebase and reduce maintainability.

### Direct PostgreSQL Driver Usage

Rejected because it would provide lower-level database access but less structure for domain models.

### Django ORM

Rejected because it would require adopting Django as the main backend framework, which is broader than needed for this API-first implementation.

## How Is It Used?

SQLAlchemy is used in three places:

### Database Configuration

app/database.py defines:

- database connection URL
- engine
- session handling
- declarative base model

### Database Models

Each domain defines database models.

Example:

- ContentRecordDB
- CategoryDB
- ContentCategoryAssignmentDB

These classes describe real database tables.

### Services

Services use SQLAlchemy sessions to:

- query records
- create records
- commit changes
- return API response models

## Example Flow

text API Request ↓ Router ↓ Service ↓ SQLAlchemy Session ↓ PostgreSQL ↓ Response Model ↓ API Response 

## Architectural Impact

SQLAlchemy supports the modular monolith by keeping database access inside domain services.

It helps maintain separation between:

- API models
- database models
- business logic
- persistence

This supports future service separation because each domain can later own its own persistence model more clearly.

## Current Limitation

The proof of concept currently creates tables automatically through:

text Base.metadata.create_all() 

This is acceptable for early development.

For a more mature implementation, database migrations should be introduced.