# Skill: dashboard-design

## Objective
Design high-impact executive dashboards that provide an immediate, accurate overview of financial health.

## Context
Used for the main Dashboard (Module A) and Investment Portfolio views (Module D).

## Prerequisites
- Defined Key Performance Indicators (KPIs) for the dashboard.
- Data availability for the required metrics.

## Execution Procedure
1. **KPI Selection**: Identify the "North Star" metrics (e.g., Net Worth, Monthly Cash Flow).
2. **Hierarchy Planning**: Place high-level summaries at the top, trends in the middle, and details at the bottom.
3. **Visualization Choice**: 
    - Line Charts for evolution/trends.
    - Pie/Donut Charts for allocation.
    - Bar Charts for budget vs actual.
4. **Interactivity Design**: Implement "drill-down" capabilities (clicking a chart segment filters the list below).
5. **Performance Optimization**: Ensure charts render quickly using optimized data.

## Technical Patterns
- Recharts for visualization.
- Data Aggregation on the backend.
- Skeleton screens for loading states.

## Examples
- Designing a "Net Worth Evolution" chart that allows toggling between different asset classes.

## Validation Criteria
- User can answer "Am I okay this month?" in < 5 seconds of looking at the dashboard.
- Charts are legible and accessible.
- Transitions between views are smooth.

## Common Errors
- Including too many charts on one screen ("Dashboard Fatigue").
- Using unsuitable chart types (e.g., pie charts for time series).

## Security Rules
- Ensure aggregated data doesn't leak PII in shared views.

## Deliverables
- Dashboard Layout Specs.
- Chart Definitions and Data Requirements.
- Interactive Prototype.
