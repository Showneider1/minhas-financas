# Skill: ci-cd

## Objective
Automate the build, test, and deployment process to ensure a fast and reliable release cycle.

## Context
Managed by the DevOps Engineer across the entire monorepo.

## Prerequisites
- Version control (GitHub).
- Defined test suites.
- Containerization (Docker).

## Execution Procedure
1. **Pipeline Stages**:
    - **Lint/Format**: Check code style (ESLint, Prettier).
    - **Type Check**: Run `tsc` to verify TypeScript types.
    - **Unit/Integration Tests**: Run all automated tests.
    - **Build**: Compile the application and build Docker images.
    - **Deploy**: Push to the target environment (Development $\rightarrow$ Staging $\rightarrow$ Production).
2. **Trigger Logic**:
    - PRs to `main` trigger all checks.
    - Merges to `main` trigger deployment to Staging.
    - Tags trigger deployment to Production.
3. **Secret Management**: Use GitHub Actions Secrets for API keys and DB credentials.
4. **Artifact Management**: Store build artifacts and Docker images in a registry.

## Technical Patterns
- GitFlow or Trunk-Based Development.
- Blue-Green or Canary Deployments.
- Infrastructure as Code (IaC).

## Examples
- A GitHub Action that blocks a merge if any test fails or if `npm run lint` returns errors.

## Validation Criteria
- Pipeline runs successfully from commit to deploy.
- Deployment is automated and requires no manual SSH.
- Rollback is possible in < 5 minutes.

## Common Errors
- Making the pipeline too slow (lack of caching).
- Deploying secrets in plain text.

## Security Rules
- Use "Least Privilege" for CI/CD tokens.
- Scan dependencies for vulnerabilities in the pipeline (e.g., Snyk, npm audit).

## Deliverables
- `.github/workflows/*.yml`.
- Dockerfiles.
- Deployment Documentation.
