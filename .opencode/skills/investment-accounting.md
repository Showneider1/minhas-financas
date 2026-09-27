# Skill: investment-accounting

## Objective
Correctly track the cost basis, value, and performance of financial assets (Stocks, FIIs, ETFs, Fixed Income).

## Context
Core logic for Module D (Investments).

## Prerequisites
- Asset registry (Ticker, Type, Currency).
- Ledger for recording buy/sell operations.

## Execution Procedure
1. **Position Tracking**: Maintain the current quantity of each asset.
2. **Average Price Calculation**: 
    - $\text{New Average Price} = \frac{(\text{Current Qty} \times \text{Current Avg}) + (\text{New Qty} \times \text{Price})}{\text{Total Qty}}$
3. **Operation Handling**:
    - **Buy**: Increase quantity, update average price.
    - **Sell**: Decrease quantity, realize gain/loss based on average price.
4. **Corporate Events**:
    - **Dividends/JCP**: Record as income, no change in quantity.
    - **Splits/Groups**: Adjust quantity and average price proportionally.
    - **Bonuses**: Increase quantity, reduce average price.
5. **Cost Basis**: Track total invested capital.

## Technical Patterns
- FIFO (First-In-First-Out) or Average Cost for tax reporting.
- Asset state snapshotting.

## Examples
- Buying 10 shares of PETR4 at R$ 30 and then 10 at R$ 40 results in an average price of R$ 35.

## Validation Criteria
- Average price is updated correctly after every purchase.
- Realized gain is calculated as $\text{Sale Price} - \text{Average Price}$.
- Corporate events don't distort total invested capital.

## Common Errors
- Forgetting to account for brokerage fees in the cost basis.
- Using floating point for share quantities (some assets allow fractions).

## Security Rules
- N/A.

## Deliverables
- Investment Logic Service.
- Corporate Event Handler.
- Position Calculator.
