# Skill: database-design

## Objective
Design a PostgreSQL schema that ensures data integrity, performance, and auditability.

## Context
Used for all data storage in Finance OS.

## Prerequisites
- Prisma ORM installation.
- PostgreSQL database.

## Execution Procedure
1. **Conceptual Modeling**: Define entities and relationships (1:1, 1:N, N:M).
2. **Logical Design**:
    - Use `Decimal` for monetary values.
    - Use `UTCTime` for all timestamps.
    - Implement `createdAt` and `updatedAt` for all tables.
3. **Integrity Constraints**:
    - Primary Keys and Foreign Keys for all relationships.
    - `NOT NULL` constraints for required fields.
    - `UNIQUE` constraints for business identifiers.
4. **Optimization**:
    - Create indexes on columns frequently used in `WHERE` and `JOIN` clauses.
    - Use composite indexes for common query patterns.
5. **Migration Strategy**: Use Prisma Migrations for version-controlled schema changes.

## Technical Patterns
- Database Normalization (up to 3NF).
- Indexing Strategies (B-Tree, GIN).
- Soft Deletes (where applicable).

## Examples
- Designing the `LedgerEntries` table to prevent updates to confirmed records.

## Validation Criteria
- No data redundancy (except for intentional performance reasons).
- Referential integrity is maintained.
- Migrations are reversible and tested.

## Common Errors
- Using `Float` or `Double` for money.
- Missing indexes on foreign keys.

## Security Rules
- Row-Level Security (RLS) where necessary.
- No PII in logs.

## Deliverables
- Prisma Schema (`schema.prisma`).
- Migration files.
- ER Diagram.
