# Skill: frontend-patterns

## Objective
Implement a scalable and maintainable frontend architecture using Next.js and React.

## Context
Used across `apps/web/` to ensure code consistency and performance.

## Prerequisites
- TypeScript knowledge.
- Tailwind CSS and shadcn/ui installation.

## Execution Procedure
1. **Component Layering**:
    - **UI Components**: Pure, stateless components (atoms).
    - **Feature Components**: Components tied to specific business logic (molecules/organisms).
    - **Pages**: Top-level route handlers.
2. **State Management**:
    - **Server State**: Use React Query or SWR for API data.
    - **Client State**: Use Zustand or Context API for global UI state.
    - **Form State**: Use React Hook Form + Zod.
3. **Data Fetching**: Prefer Server Components for initial load; Client Components for interactivity.
4. **Error Handling**: Use Error Boundaries and Zod for API response validation.
5. **Performance**: Implement dynamic imports and image optimization.

## Technical Patterns
- Compound Components.
- Custom Hooks for business logic.
- Zod-driven type safety.

## Examples
- Creating a `useAccountBalance` hook that manages the state and refreshing of the balance.

## Validation Criteria
- Components are decoupled from business logic.
- Types are strictly defined (no `any`).
- Layout shifts (CLS) are minimized.

## Common Errors
- Putting too much business logic inside the JSX.
- Over-using global state when local state suffices.

## Security Rules
- Never store sensitive data (tokens) in `localStorage` if `HttpOnly` cookies are available.
- Sanitize all user inputs to prevent XSS.

## Deliverables
- Component Library.
- Custom Hooks.
- Page Implementations.
