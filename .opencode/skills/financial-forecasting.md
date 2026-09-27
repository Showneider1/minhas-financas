# Skill: financial-forecasting

## Objective
Project future financial states based on current trends, planned budgets, and historical data.

## Context
Used in Planning (Module E) and AI Assistant (Module F).

## Prerequisites
- Historical transaction data.
- Defined budgets and goals.

## Execution Procedure
1. **Trend Analysis**: Identify recurring expenses and income patterns.
2. **Linear Projection**: Estimate future balance: $\text{Current Balance} + (\text{Avg Income} - \text{Avg Expense}) \times \text{Months}$.
3. **Scenario Modeling**:
    - **Optimistic**: High income, low expense.
    - **Pessimistic**: Low income, high expense.
    - **Realistic**: Based on average.
4. **Goal Tracking**: Estimate the date when a financial goal will be reached based on the current saving rate.
5. **Cash Flow Projection**: Create a month-by-month view of expected liquidity.

## Technical Patterns
- Time-series forecasting.
- Monte Carlo simulation (for advanced investment projections).
- Budget variance analysis.

## Examples
- Projecting if the user will have enough money for a trip in December based on their current savings rate.

## Validation Criteria
- Projections are clearly marked as "Estimates".
- Forecasts update automatically when new data is added.
- Scenarios are distinct and logically sound.

## Common Errors
- Assuming the future will be exactly like the past without considering planned changes.
- Over-promising goal dates without considering inflation.

## Security Rules
- N/A.

## Deliverables
- Forecasting Engine.
- Scenario Simulation Logic.
- Cash Flow Projection View.
