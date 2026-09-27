# Skill: api-integration

## Objective
Design and implement consistent, secure, and performant APIs for communication between frontend, backend, and external services.

## Context
Used for all inter-service and client-server communication.

## Prerequisites
- OpenAPI/Swagger specification.
- Defined authentication mechanism.

## Execution Procedure
1. **Contract First**: Define the API spec (OpenAPI) before implementation.
2. **REST Standards**:
    - Proper use of HTTP verbs (GET, POST, PUT, DELETE, PATCH).
    - Meaningful URL paths (`/accounts`, `/transactions/{id}`).
    - Standard HTTP status codes (200, 201, 400, 401, 403, 404, 500).
3. **Request/Response Validation**: Use DTOs and Zod to validate all data.
4. **Pagination and Filtering**: Implement `limit`, `offset`, and `sort` for list endpoints.
5. **Versioning**: Use URL versioning (e.g., `/api/v1/...`) to avoid breaking changes.

## Technical Patterns
- HATEOAS (where applicable).
- JSON:API or similar standards.
- Idempotency Keys for POST requests (especially for payments).

## Examples
- Creating a `POST /transactions` endpoint that requires an idempotency key to prevent duplicate charges.

## Validation Criteria
- API matches the OpenAPI specification.
- All endpoints have defined request/response types.
- Error responses are consistent and descriptive.

## Common Errors
- Returning 200 OK for errors.
- Over-fetching data (Returning the whole user object when only the name is needed).

## Security Rules
- Implement Rate Limiting.
- Validate Content-Type.
- Use CORS policies correctly.

## Deliverables
- OpenAPI Specification.
- API Controller Implementation.
- Integration Tests.
