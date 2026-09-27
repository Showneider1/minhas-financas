# Skill: double-entry-ledger

## Objective
Implement a robust, immutable accounting system where every movement of value is recorded as at least one debit and one credit.

## Context
The core engine for all financial movements in Finance OS. Essential for accuracy and auditing.

## Prerequisites
- Database schema supporting a `Transactions` and `Entries` (or `Journal`) structure.
- Use of exact decimals (Decimal/Numeric) for amounts.

## Execution Procedure
1. **Transaction Definition**: Every "Financial Event" is a `Transaction` (e.g., "Payment of Rent").
2. **Atomic Entries**: A Transaction must consist of two or more `Entries`.
    - Debit: Increases Assets or Expenses.
    - Credit: Increases Liabilities, Equity, or Revenue.
3. **Balance Equation**: Ensure $\sum \text{Debits} = \sum \text{Credits}$ for every transaction.
4. **Immutability**: Confirmed entries cannot be edited.
5. **Correction via Reversal**: To fix an error, create a "Reversal Transaction" that cancels the original entries and then create the correct one.

## Technical Patterns
- Transactional atomicity (DB Transactions).
- Event Sourcing (optional, for full audit trail).
- Decimal.js / Big.js for calculations.

## Examples
- Transfer from "Checking Account" to "Savings Account":
    - Credit Checking (Asset $\downarrow$)
    - Debit Savings (Asset $\uparrow$)

## Validation Criteria
- Ledger always balances.
- No record is ever updated or deleted (only appended).
- All movements are traceable to a specific transaction.

## Common Errors
- Using a single "balance" column in an account table without a ledger.
- Allowing a transaction to be "half-saved".

## Security Rules
- Strict access control to the ledger tables.
- Audit logs for any attempt to modify historical data.

## Deliverables
- Ledger Schema.
- Ledger Service Implementation.
- Invariant Validation Tests.
