# Skill: data-pipelines

## Objective
Implement efficient and reliable processes for moving, transforming, and aggregating data.

## Context
Used for financial imports (CSV/OFX) and portfolio aggregation.

## Prerequisites
- Source data formats (CSV, XML, JSON).
- Target database schema.

## Execution Procedure
1. **Extraction**: Read data from source files or APIs.
2. **Validation**: Check for file integrity and basic format correctness.
3. **Transformation**:
    - Map source fields to internal entities.
    - Normalize dates, currencies, and descriptions.
    - Cleanse data (remove duplicates, fix typos).
3. **Loading**: Persist data using bulk inserts for performance.
4. **Reconciliation**: Verify that the number of records imported matches the source.

## Technical Patterns
- ETL (Extract, Transform, Load).
- Worker queues (BullMQ) for background processing.
- Idempotent loading (Upsert).

## Examples
- Pipeline that reads a Brazilian bank OFX file and converts it into `LedgerEntries`.

## Validation Criteria
- Pipeline handles large files without memory overflow.
- Transformation logic is unit-tested with various edge cases.
- Errors are logged and reported to the user.

## Common Errors
- Processing large files synchronously in the main thread.
- Failing to handle encoding issues in CSV files.

## Security Rules
- Scan imported files for malicious content.
- Sanitize all strings before DB insertion.

## Deliverables
- Data Pipeline Implementation.
- Transformation Logic.
- Import Status Reports.
