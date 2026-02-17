# Deployment Runbook

## How to Deploy
To deploy the application, use the standard deployment script.
`./scripts/deploy.sh --env=production`

## Rollback
If metrics degrade after deployment, rollback immediately:
`./scripts/rollback.sh --version=previous`

## P95 Latency High
If P95 latency exceeds 500ms:
1. Check database CPU usage.
2. Check for long-running queries in `pg_stat_activity`.
3. Scale up read replicas if load is read-heavy.
