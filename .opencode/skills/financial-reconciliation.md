# Skill: financial-reconciliation

## Objective
Verify that the internal ledger matches the external reality (e.g., bank statements).

## Context
Used in the "Import and Reconciliation" flow (Module B).

## Prerequisites
- Import of external statements (CSV/OFX).
- Existing internal ledger.

## Execution Procedure
1. **Matching Logic**: Attempt to match external transactions with internal ones based on:
    - Date (within a window, e.g., $\pm 3$ days).
    - Amount (exact match).
    - Description/Merchant (fuzzy match).
2. **State Management**: Mark transactions as `Pending`, `Matched`, or `Discrepancy`.
3. **Resolution Flow**:
    - **Auto-match**: Automatic reconciliation.
    - **Manual-match**: User confirms a match.
    - **Creation**: User creates a missing internal transaction from the external record.
4. **Balance Verification**: Confirm that $\text{Internal Balance} + \text{Unreconciled} = \text{External Balance}$.

## Technical Patterns
- Fuzzy String Matching (e.g., Levenshtein distance).
- Batch processing for large statements.
- Reconciliation state machine.

## Examples
- Matching a "Netflix" charge of -R$ 55,90 from the bank statement to a planned "Streaming" expense in the app.

## Validation Criteria
- Reconciliation process reduces the number of "unmatched" items.
- User can easily identify discrepancies.
- Final balance match is confirmed.

## Common Errors
- Over-aggressive auto-matching causing incorrect ledger entries.
- Not handling bank fees that appear only on the statement.

## Security Rules
- Do not trust external data blindly; validate all imports.

## Deliverables
- Reconciliation Service.
- Reconciliation UI Specification.
- Matching Algorithm Logic.
