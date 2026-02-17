# SQL Ops Agent (Local-First)

A production-grade SQL Ops Agent you can run locally:
- RAG over runbooks + schema docs
- Safe SQL planning + execution with guardrails (AST-based)
- Offline benchmark + golden tests
- Observability: JSON logs, /metrics, traces

## Quickstart (Docker)

1.  **Run with Docker Compose**:
    ```bash
    docker compose up --build
    ```

2.  **Access Endpoints**:
    - API Docs: [http://localhost:8080/docs](http://localhost:8080/docs)
    - Health: [http://localhost:8080/healthz](http://localhost:8080/healthz)
    - Metrics: [http://localhost:8080/metrics](http://localhost:8080/metrics)

## Local LLM Setup

The default configuration expects a local LLM server.

- **Option A: llama-cpp-python (CPU-friendly)**: 
  The `docker-compose.yml` includes a profile for this. You need to place a GGUF model in `models/` directory (created automatically or manually).
  
- **Option B: vLLM (GPU)**:
  Uncomment or use the vLLM service in `docker-compose.yml`.

## Development

1.  **Install Dependencies**:
    ```bash
    pip install -e ".[dev]"
    ```

2.  **Run Tests**:
    ```bash
    pytest
    ```
