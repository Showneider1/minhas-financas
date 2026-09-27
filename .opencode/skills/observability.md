# Skill: observability

## Objective
Implement monitoring, logging, and tracing to proactively identify and resolve issues in the production environment.

## Context
Used by the DevOps and Performance Engineers to maintain system health.

## Prerequisites
- Structured logging implementation.
- Access to monitoring tools (e.g., Prometheus, Grafana, ELK).

## Execution Procedure
1. **Structured Logging**:
    - Use a standard format (JSON).
    - Include Correlation IDs to track requests across services (API $\rightarrow$ AI $\rightarrow$ DB).
    - Define log levels: `DEBUG`, `INFO`, `WARN`, `ERROR`, `FATAL`.
2. **Metrics Collection**:
    - **System Metrics**: CPU, Memory, Disk I/O.
    - **Application Metrics**: Request rate, Error rate, Latency (RED pattern).
    - **Business Metrics**: New users, Transaction volume.
3. **Alerting**:
    - Define thresholds for critical errors (e.g., 5xx error rate > 1%).
    - Set up notifications via Slack/Email.
4. **Tracing**: Implement distributed tracing to find bottlenecks in the AI pipeline.
5. **Health Checks**: Implement `/health` endpoints for all services.

## Technical Patterns
- ELK Stack (Elasticsearch, Logstash, Kibana) or LGTM (Loki, Grafana, Tempo, Mimir).
- Prometheus for metrics.
- OpenTelemetry for tracing.

## Examples
- An alert that triggers when the database connection pool reaches 90% capacity.

## Validation Criteria
- All critical errors are logged with a stack trace.
- Dashboard provides a real-time view of system health.
- Mean Time to Detection (MTTD) is minimized.

## Common Errors
- Logging too much data ("Log Spam"), increasing costs and noise.
- Logging sensitive PII (Passwords, Tokens).

## Security Rules
- Sanitize logs to remove sensitive information.
- Restrict access to monitoring dashboards.

## Deliverables
- Monitoring Dashboards.
- Alerting Configuration.
- Logging Policy.
