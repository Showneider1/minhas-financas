# Skill: market-data

## Objective
Integrate and manage external market data (prices, quotes, corporate events) to keep the portfolio updated.

## Context
Used to fuel Investment Accounting and Analytics.

## Prerequisites
- Selection of a market data provider (API).
- Infrastructure for scheduled updates (cron/workers).

## Execution Procedure
1. **Provider Abstraction**: Create a generic `MarketDataProvider` interface.
2. **Data Fetching**: Implement strategies for:
    - **Real-time quotes**: For current valuation.
    - **Historical data**: For performance charts.
    - **Corporate events**: For automatic adjustment of positions.
3. **Caching Strategy**: Store quotes in Redis or DB to avoid API rate limits.
4. **Error Handling**: Implement fallbacks if a provider is down.
5. **Data Validation**: Sanitize incoming data (e.g., check for negative prices).

## Technical Patterns
- Adapter Pattern.
- Cache-Aside Pattern.
- Rate Limiting/Throttling.

## Examples
- Fetching the daily closing price of all assets in the user's portfolio every night at 23:00.

## Validation Criteria
- Prices are current (within defined latency).
- API rate limits are not exceeded.
- Data is consistent across different assets.

## Common Errors
- Mixing currencies (USD vs BRL) without conversion.
- Trusting a single API without validation.

## Security Rules
- API keys must be stored in environment variables, never in code.

## Deliverables
- Market Data Adapters.
- Data Fetching Workers.
- Market Data Cache Layer.
