# Skill: testing-strategy

## Objective
Define a comprehensive and risk-based testing approach to ensure the reliability, accuracy, and security of Finance OS.

## Context
Used at the start of every feature development and during the final stabilization phase.

## Prerequisites
- Clear acceptance criteria from the Product Manager.
- Understanding of the system's critical paths (e.g., money movement).

## Execution Procedure
1. **Test Pyramid Definition**:
    - **Unit Tests**: Focus on business logic, calculations, and utility functions (Highest volume).
    - **Integration Tests**: Focus on API endpoints, DB interactions, and service communication.
    - **E2E Tests**: Focus on critical user journeys (e.g., "User creates account and adds first transaction").
2. **Risk-Based Prioritization**:
    - **Critical**: Financial calculations, Authorization, Data Integrity.
    - **High**: Core UI flows, Import pipelines.
    - **Medium**: Dashboard visualizations, User settings.
3. **Test Data Management**: Define sets of "Golden Data" for consistent testing.
4. **Execution Pipeline**: Integrate tests into the CI/CD pipeline (GitHub Actions).
5. **Reporting**: Define how test results are reported and tracked.

## Technical Patterns
- AAA (Arrange, Act, Assert).
- TDD (Test Driven Development) for core financial logic.
- Mocking external APIs.

## Examples
- Defining that the "Double Entry Ledger" must have 100% unit test coverage.

## Validation Criteria
- Test coverage meets the minimum threshold for the risk level.
- No critical bugs reach the QA phase.
- E2E tests pass in a clean environment.

## Common Errors
- Focusing only on "Happy Paths" and ignoring edge cases.
- Writing tests that are too coupled to implementation details.

## Security Rules
- Never use real user data in tests.
- Tests must verify that unauthorized users cannot access data.

## Deliverables
- Testing Strategy Document.
- Test Plan per Feature.
- CI Pipeline Configuration.
