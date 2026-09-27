# Skill: financial-ux

## Objective
Apply specialized UX patterns to financial data to reduce cognitive load and prevent user errors in money management.

## Context
Used when designing any screen that involves monetary values, transaction lists, or financial charts.

## Prerequisites
- Basic understanding of financial concepts (e.g., credit vs debit).

## Execution Procedure
1. **Clarity First**: Use clear labels. Avoid jargon. Ensure "Positive" and "Negative" flows are visually distinct (e.g., Green for income, Red for expense).
2. **Error Prevention**: Use masks for currency input. Provide immediate feedback on invalid entries.
3. **Information Hierarchy**: Place the most critical number (e.g., Current Balance) in the most prominent position.
4. **Contextual Actions**: Provide actions where the user needs them (e.g., "Edit" button next to a transaction).
5. **Confirmation for Criticality**: Require explicit confirmation for destructive actions (e.g., deleting a transaction).

## Technical Patterns
- Currency Formatting (BRL).
- Progressive Disclosure for complex financial details.
- "Empty State" guidance for new users.

## Examples
- Designing a transaction form that automatically suggests categories based on the merchant name.

## Validation Criteria
- User can complete a core task (e.g., add expense) in < 30 seconds.
- Critical financial errors are prevented by the UI.
- Visual contrast between income and expense is clear.

## Common Errors
- Using too many colors, causing "visual noise".
- Hiding the total balance behind multiple clicks.

## Security Rules
- Mask sensitive data (e.g., account numbers) by default.

## Deliverables
- UX Specifications.
- Interaction Flows.
- UI Mockups.
