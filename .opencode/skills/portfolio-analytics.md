# Skill: portfolio-analytics

## Objective
Generate meaningful indicators to evaluate the performance and risk of an investment portfolio.

## Context
Used in Investment Dashboards (Module D).

## Prerequisites
- Accurate investment accounting (positions, prices, operations).
- Access to current market prices.

## Execution Procedure
1. **Valuation**: Calculate $\text{Current Value} = \sum (\text{Quantity} \times \text{Current Market Price})$.
2. **Unrealized Gain/Loss**: $\text{Current Value} - \text{Cost Basis}$.
3. **Rentability (Yield)**: 
    - Simple Yield: $\frac{\text{Current Value} + \text{Dividends}}{\text{Invested Capital}} - 1$.
    - Time-Weighted Return (TWR) for performance independent of cash flows.
    - Internal Rate of Return (IRR) for cash-flow sensitive performance.
4. **Allocation Analysis**: Calculate % distribution by Asset Class, Sector, and Ticker.
5. **Dividend Tracking**: Project future income based on historical payouts.

## Technical Patterns
- Time-series aggregation.
- Portfolio rebalancing calculations.
- XIRR algorithm implementation.

## Examples
- Calculating the portfolio's total return compared to a benchmark like the IBOVESPA.

## Validation Criteria
- Rentability calculations match a spreadsheet (Excel/Google Sheets).
- Allocation charts sum to 100%.
- Indicators are updated in real-time or on a defined schedule.

## Common Errors
- Ignoring dividends when calculating total return.
- Confusing nominal return with real return (inflation-adjusted).

## Security Rules
- N/A.

## Deliverables
- Analytics Engine.
- Performance Report Specifications.
- Allocation Logic.
