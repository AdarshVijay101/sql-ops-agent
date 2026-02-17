# How to Query Data

## Safe Query Practices
- Always use `LIMIT` to prevent fetching too many rows.
- Do not run `SELECT *` on large tables without a `WHERE` clause.
- Prefer aggregation for high-level metrics.

## Prohibited Actions
- `DROP`, `DELETE`, `UPDATE` are strictly forbidden for the agent.
- Queries accessing `passwords` or `secrets` tables are blocked.
