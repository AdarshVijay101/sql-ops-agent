from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
from pydantic import BaseModel
from typing import List, Any, Dict, Optional
import os
from pathlib import Path

from sql_ops_agent.observability.logging import configure_logging, request_id_var
import uuid
import structlog
from sql_ops_agent.observability.metrics import REQUESTS_TOTAL, REQUEST_LATENCY_SECONDS
from sql_ops_agent.llm.openai_compatible import OpenAICompatibleClient
from sql_ops_agent.rag.retriever import SimpleRetriever
from sql_ops_agent.sql.executor import SQLExecutor, ExecConfig
from sql_ops_agent.orchestrator import AgentOrchestrator

# Configure logging at startup
configure_logging()

app = FastAPI(
    title="SQL Ops Agent",
    description="Local-first SQL Ops Agent with guardrails and RAG",
    version="0.1.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# --- Dependency Injection (Simple Global for Demo) ---
# In a real app, use Depends() or lifespan context
orchestrator: Optional[AgentOrchestrator] = None


@app.on_event("startup")
async def startup_event():
    global orchestrator

    # Load config from env
    llm_base = os.getenv("LLM_BASE_URL", "http://localhost:8000/v1")
    llm_key = os.getenv("LLM_API_KEY", "local-token")
    db_url = os.getenv("DB_URL", "duckdb:///data/demo.duckdb")
    model_name = os.getenv("LLM_MODEL", "local-model")
    allow_mock = os.getenv("ALLOW_MOCK_FALLBACK", "true").lower() == "true"

    # Initialize components
    llm = OpenAICompatibleClient(base_url=llm_base, api_key=llm_key, model=model_name, allow_mock_fallback=allow_mock)

    # RAG docs dir (assume 'docs' folder in root or mounted volume)
    docs_path = Path(os.getenv("RAG_INDEX_PATH", "docs"))
    if not docs_path.exists():
        docs_path.mkdir(exist_ok=True)
        # Create a sample doc if empty for demo
        if not list(docs_path.glob("*.md")):
            (docs_path / "sample.md").write_text("# Sample Runbook\n\nTo restart app, run `restart.sh`.")

    retriever = SimpleRetriever(docs_path)

    executor = SQLExecutor(ExecConfig(dsn=db_url))

    orchestrator = AgentOrchestrator(llm, retriever, executor)


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "orchestrator": orchestrator is not None}


class RunRequest(BaseModel):
    query: str


class RunResponse(BaseModel):
    outcome: str
    answer: str
    sql: Optional[str] = None
    rows: Optional[List[Dict[str, Any]]] = None
    citations: List[Dict[str, Any]] = []
    retrieved: List[Dict[str, Any]] = []
    invalid_citations: List[Dict[str, Any]] = []
    blocked_reason: Optional[str] = None
    metrics: Dict[str, Any] = {}


logger = structlog.get_logger()

# ... (omitting irrelevant lines below by targeting only the specific area) ...


@app.post("/v1/agent/run", response_model=RunResponse)
async def run_agent(req: RunRequest):
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    req_id = str(uuid.uuid4())
    token = request_id_var.set(req_id)

    REQUESTS_TOTAL.labels(outcome="attempt").inc()
    import time

    start_time = time.time()

    log = logger.bind(query=req.query)
    try:
        with REQUEST_LATENCY_SECONDS.time():
            result = await orchestrator.run(req.query)

        duration_ms = (time.time() - start_time) * 1000
        REQUESTS_TOTAL.labels(outcome="success").inc()

        log.info("request_completed", outcome=result.outcome, latency_ms=round(duration_ms, 2))

        RunResponse_res = RunResponse(
            outcome=result.outcome,
            answer=result.answer,
            sql=result.sql_executed,
            rows=result.rows,
            citations=result.citations or [],
            retrieved=[
                {"doc_id": c["doc_id"], "chunk_id": c["chunk_id"], "score": c.get("score")}
                for c in (result.retrieved_context or [])
            ],
            invalid_citations=result.invalid_citations or [],
            blocked_reason=result.blocked_reason,
            metrics={"latency_ms": round(duration_ms, 2)},
        )
        request_id_var.reset(token)
        return RunResponse_res
    except Exception as e:
        REQUESTS_TOTAL.labels(outcome="error").inc()
        duration_ms = (time.time() - start_time) * 1000
        log.error("request_failed", error=str(e), latency_ms=round(duration_ms, 2))
        request_id_var.reset(token)
        raise HTTPException(status_code=500, detail=str(e))
