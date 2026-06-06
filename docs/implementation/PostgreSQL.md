# PostgreSQL

## Purpose

PostgreSQL is the primary data store of the reference implementation.

It stores architecture entities, operational data and decision-related information.

## Why Was It Chosen?

### Open Source

PostgreSQL is open source and avoids vendor lock-in.

### Relational Model Support

The architecture contains strongly related entities such as:

- Campaign
- Variant
- Content Record
- Decision Resolution
- Engagement Event

Relational storage is therefore required.

### Flexibility

PostgreSQL also supports JSON structures where flexibility is beneficial.

This allows structured and semi-structured data to coexist.

### Industry Adoption

PostgreSQL is widely adopted and supported across hosting providers and cloud environments.

## Alternatives Considered

### MySQL

Rejected because PostgreSQL provides stronger capabilities for complex data models and analytical workloads.

### NoSQL Databases

Rejected because the architecture primarily relies on relationships between entities.

## How Is It Used?

PostgreSQL stores:

- Content Catalog
- Categories
- Campaigns
- Variants
- Snapshots
- Engagement Events
- Decision Data

## Architectural Impact

PostgreSQL supports:

- Domain relationships
- Historical tracking
- Decision transparency
- Future analytics and recommendation capabilities