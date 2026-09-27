# Skill: backend-patterns

## Objective
Build a maintainable, testable, and secure backend using NestJS and TypeScript.

## Context
Used across `services/api/` and `packages/financial-core/`.

## Prerequisites
- NestJS framework installation.
- TypeScript knowledge.

## Execution Procedure
1. **Modular Architecture**: Divide the system into domains (e.g., `AccountsModule`, `TransactionModule`).
2. **Layered Responsibility**:
    - **Controller**: Handle HTTP requests and input validation.
    - **Service**: Implement business logic.
    - **Repository**: Handle data persistence.
    - **DTO**: Define data transfer objects for input/output.
3. **Dependency Injection**: Use NestJS DI to decouple services and improve testability.
4. **Interceptors and Guards**: Implement logging, transformation, and authorization centrally.
5. **Custom Exceptions**: Use specific Exception filters for consistent API error responses.

## Technical Patterns
- Repository Pattern.
- Service Layer Pattern.
- DTO (Data Transfer Object).

## Examples
- Implementing a `TransactionService` that ensures ledger balance before persisting a transfer.

## Validation Criteria
- Business logic is isolated from the HTTP layer.
- Services are easily unit-testable with mocks.
- API responses follow a consistent format.

## Common Errors
- Putting DB queries directly in the Controller.
- Circular dependencies between modules.

## Security Rules
- Always validate input using `class-validator` / Zod.
- Implement a global `ValidationPipe`.

## Deliverables
- Modular API Implementation.
- Service Classes.
- DTO Definitions.
