# SQL Ops Agent (Production-Grade Local-First)

**A secure, observable, and evaluatable NL-to-SQL agent that runs entirely on your machine.**

This project demonstrates a production-grade approach to building LLM agents:
- **Safety First**: Deterministic Guardrails (AST parsing) prevent destructive queries.
- **Grounded**: RAG-based citation enforcement with strict "No-Answer" thresholds.
- **Observable**: Structured JSON logging and Prometheus metrics (`/metrics`).
- **Evaluatable**: Integrated benchmark harness (`bench/cases.yaml`) effectively measuring safety and correctness.

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

### Prerequisites
- Docker & Docker Compose
- A GGUF model (e.g., Mistral/Llama3) in `./models/` if using local CPU inference.

### Run with Docker Compose
```bash
# 1. Start the stack (API + Local LLM + DB)
docker compose up --build

# 2. Check health
curl http://localhost:8080/healthz
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
