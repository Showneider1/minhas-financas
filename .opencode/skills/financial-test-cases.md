# Skill: financial-test-cases

## Objective
Design and implement specific test scenarios to validate the mathematical accuracy and integrity of financial operations.

## Context
Used by the QA Engineer and Backend Engineer when implementing the Ledger, Investment, and Analytics modules.

## Prerequisites
- Financial specifications from the Domain Expert.
- A working environment with a test database.

## Execution Procedure
1. **Boundary Value Analysis**: Test with zero, negative values, and extremely large numbers.
2. **Ledger Invariant Tests**:
    - Verify $\sum \text{Debits} = \sum \text{Credits}$ for every single transaction.
    - Verify that no confirmed entry is ever modified.
3. **Investment Calculation Scenarios**:
    - Buy $\rightarrow$ Buy $\rightarrow$ Sell (Check Average Price and Realized Gain).
    - Dividend payout (Check Balance and Yield).
    - Stock Split/Group (Check Quantity and Average Price).
4. **Concurrency Tests**: Simulate multiple transactions on the same account simultaneously to check for race conditions.
5. **Idempotency Tests**: Run the same "Add Transaction" request twice and verify only one record exists.

## Technical Patterns
- Parameterized Tests.
- Property-Based Testing (e.g., using Fast-Check).

## Examples
- Scenario: Buy 10 shares at 100, Buy 10 shares at 200 $\rightarrow$ Expected Avg: 150. Sell 5 shares at 300 $\rightarrow$ Expected Realized Gain: $5 \times (300-150) = 750$.

## Validation Criteria
- Results match a verified reference (e.g., Excel or official accounting rules).
- Ledger remains balanced after all operations.
- Idempotent requests do not create duplicate entries.

## Common Errors
- Rounding errors during tests.
- Not testing the "Reversal" flow for incorrect transactions.

## Security Rules
- N/A.

## Deliverables
- Financial Test Suite.
- Scenario Matrix.
- Calculation Validation Report.
