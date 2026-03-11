# Builder stage
FROM python:3.11-slim AS builder
WORKDIR /app
RUN pip install -U pip build
COPY pyproject.toml README.md ./
COPY sql_ops_agent ./sql_ops_agent
# Create a wheel
RUN python -m build --wheel

# Runtime stage
FROM python:3.11-slim AS runtime
WORKDIR /app
# Create non-root user
RUN useradd -m appuser

# Copy wheel from builder and install
COPY --from=builder /app/dist/*.whl /app/dist/
RUN pip install /app/dist/*.whl --no-cache-dir

# Prepare mount paths for stateless deployments (DB and RAG docs)
RUN mkdir -p /app/data /app/docs && chown -R appuser:appuser /app/data /app/docs
ENV DB_URL="duckdb:////app/data/demo.duckdb"
ENV RAG_INDEX_PATH="/app/docs"

# Switch to non-root
USER appuser

# Expose API port
EXPOSE 8080

CMD ["python", "-m", "uvicorn", "sql_ops_agent.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
