# Skill: design-system

## Objective
Create and maintain a consistent set of reusable UI components and tokens to ensure visual harmony and development speed.

## Context
Used throughout the frontend development to avoid duplicating styles and ensuring a "Premium" feel.

## Prerequisites
- Defined brand colors and typography.
- Use of Tailwind CSS and shadcn/ui.

## Execution Procedure
1. **Token Definition**: Define colors, spacing, typography, and shadows in `tailwind.config.js`.
2. **Atomic Components**: Create basic components (Buttons, Inputs, Badges) using shadcn/ui.
3. **Molecular Components**: Combine atoms into complex components (TransactionRow, BalanceCard).
4. **Organism Templates**: Create page layouts and dashboard shells.
5. **Documentation**: Document usage and variants for each component.

## Technical Patterns
- Atomic Design.
- Design Tokens.
- Utility-First CSS.

## Examples
- Creating a `FinancialBadge` component that automatically changes color based on the transaction type.

## Validation Criteria
- No "magic numbers" for colors or spacing in the code.
- Components are reusable and configurable via props.
- Design is consistent across all modules.

## Common Errors
- Creating "one-off" components for a single page.
- Inconsistent naming conventions for tokens.

## Security Rules
- N/A.

## Deliverables
- `tailwind.config.js` with custom tokens.
- Library of reusable components in `packages/ui/`.
- Component Documentation.
