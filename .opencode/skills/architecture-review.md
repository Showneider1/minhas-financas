# Skill: architecture-review

## Objective
Critically analyze technical designs and implementations to ensure they align with the project's long-term goals and quality standards.

## Context
Used during the design phase of a feature and before merging major PRs.

## Prerequisites
- Access to the Architecture Decision Records (ADRs).
- Understanding of the target tech stack.

## Execution Procedure
1. **Alignment Check**: Does the design follow the defined architecture (e.g., Modular Monolith)?
2. **Trade-off Analysis**: What are the pros and cons of the chosen approach? Is there a simpler alternative?
3. **Dependency Review**: Does the change introduce unnecessary or risky dependencies?
4. **Complexity Audit**: Is the code over-engineered? Is the logic easy to follow?
5. **Bottleneck Identification**: Will this design cause performance or scalability issues?
6. **Feedback Loop**: Provide actionable suggestions and a "Go/No-Go" decision.

## Technical Patterns
- ADR (Architectural Decision Record).
- Design Review Meetings.
- Static Analysis.

## Examples
- Reviewing a proposal to move from a modular monolith to microservices and rejecting it as premature optimization.

## Validation Criteria
- The review identifies at least one potential risk or improvement.
- The final design is documented in an ADR.
- All reviewers' concerns are addressed or documented.

## Common Errors
- Focus on "nitpicks" instead of structural flaws.
- Approving designs without verifying their impact on other modules.

## Security Rules
- Ensure the design doesn't introduce new security vulnerabilities.

## Deliverables
- Architecture Review Report.
- Updated ADRs.
- Approved Design Spec.
