from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
from pydantic import BaseModel
from typing import List, Any, Dict, Optional
import os
from pathlib import Path

from sql_ops_agent.observability.logging import configure_logging
from sql_ops_agent.observability.metrics import AGENT_RUN_TOTAL, AGENT_LATENCY_SECONDS
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
    
    # Initialize components
    llm = OpenAICompatibleClient(base_url=llm_base, api_key=llm_key, model=model_name)
    
    # RAG docs dir (assume 'docs' folder in root or mounted volume)
    docs_path = Path("docs") 
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
    answer: str
    sql: Optional[str] = None
    rows: Optional[List[Dict[str, Any]]] = None
    citations: List[str] = []
    blocked_reason: Optional[str] = None

@app.post("/v1/agent/run", response_model=RunResponse)
async def run_agent(req: RunRequest):
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    AGENT_RUN_TOTAL.labels(status="attempt").inc()
    try:
        with AGENT_LATENCY_SECONDS.labels(stage="total").time():
            result = await orchestrator.run(req.query)
        
        AGENT_RUN_TOTAL.labels(status="success").inc()
        return RunResponse(
            answer=result.answer,
            sql=result.sql_executed,
            rows=result.rows,
            citations=result.citations or [],
            blocked_reason=result.blocked_reason
        )
    except Exception as e:
        AGENT_RUN_TOTAL.labels(status="error").inc()
        raise HTTPException(status_code=500, detail=str(e))

