# SQL Ops Agent (Production-Grade Local-First)

**A secure, observable, and evaluatable NL-to-SQL agent that runs entirely on your machine.**

This project demonstrates a production-grade approach to building LLM agents:
- **Safety First**: Deterministic Guardrails (AST parsing) prevent destructive queries.
- **Grounded**: RAG-based citation enforcement with strict "No-Answer" thresholds.
- **Observable**: Structured JSON logging and Prometheus metrics (`/metrics`).
- **Demo Mode**: Runs out-of-the-box with a deterministic "Mock LLM" if no local model is available.

## Architecture

```mermaid
flowchart LR
U[User] --> API[FastAPI /v1/agent/run]
API --> RAG[BM25 Retriever]
RAG -->|top-k chunks| ORCH[Orchestrator]
ORCH --> LLM[OpenAI-compatible LLM]
LLM --> GR[SQL Guardrails (sqlglot)]
GR -->|allowed| EX[SQL Executor]
EX --> DB[(DuckDB/Postgres)]
ORCH --> OBS[Logs + Prometheus Metrics]
ORCH --> API
```

## Quickstart

### Option 1: Docker (Recommended)
This requires no local setup other than Docker.
```bash
docker compose up --build
```
*Note: If no LLM server is detected at `http://host.docker.internal:8000`, the agent automatically falls back to **Demo Mode**, returning safe, canned responses for testing.*

### Option 2: Local Python
```bash
make run
```

### Usage Examples

**1. Safe Query**
```bash
curl -X POST "http://localhost:8080/v1/agent/run" \
     -H "Content-Type: application/json" \
     -d '{"query": "Show top 5 orders by amount"}'
```
*Expected: Returns JSON with answer, SQL executed, and rows.*

**2. Blocked Unsafe Query (Guardrails)**
```bash
curl -X POST "http://localhost:8080/v1/agent/run" \
     -H "Content-Type: application/json" \
     -d '{"query": "Drop the orders table"}'
```
*Expected: Returns blocked status with reason `write_or_ddl_not_allowed`.*

**3. Runbook Retrieval**
```bash
curl -X POST "http://localhost:8080/v1/agent/run" \
     -H "Content-Type: application/json" \
     -d '{"query": "How do I deploy?"}'
```
*Expected: Returns answer citing `deployment.md`.*

## Safety & Guardrails
We use **sqlglot** to parse and validate SQL ASTs before execution:
- **Read-Only**: Only `SELECT` statements are allowed. `DROP`, `DELETE`, `INSERT` are rejected at the parser level.
- **Allowed Tables**: Queries can only access whitelisted tables.
- **Row Limits**: `LIMIT 200` is automatically injected if missing or too high.

## Observability
- **Metrics**: Exposes Prometheus metrics at `http://localhost:8080/metrics`.
- **Logs**: JSON structured logs with `request_id` propagation.

## Evaluation
Run the built-in benchmark harness to verify performance:
```bash
python sql_ops_agent/eval/harness.py
```
*Outputs a report covering Safety Recall, Citation Accuracy, and Answer Correctness.*

## CI/CD
The project includes a GitHub Actions workflow that:
1. Runs `ruff` linting and `pytest` testing.
2. Builds the Docker image.
3. Publishes the image to **GitHub Container Registry (GHCR)** on push to main.

To run the published image:
```bash
docker run -p 8080:8080 ghcr.io/<your-username>/sql-ops-agent:latest
```
