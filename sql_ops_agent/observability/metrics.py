from prometheus_client import Counter, Histogram

# Service Metrics
REQUEST_LATENCY_SECONDS = Histogram(
    "request_latency_seconds", 
    "Total request latency in seconds"
)

REQUESTS_TOTAL = Counter(
    "requests_total", 
    "Total requests by outcome", 
    ["outcome"]  # SUCCESS, NO_ANSWER, BLOCKED_GUARDRAILS, SQL_ERROR, LLM_ERROR
)

# LLM Metrics
LLM_LATENCY_SECONDS = Histogram(
    "llm_latency_seconds", 
    "LLM call latency", 
    ["model"]
)

LLM_TOKENS_TOTAL = Counter(
    "llm_tokens_total", 
    "LLM Token usage", 
    ["type", "model"] # type=prompt|completion
)

# SQL Metrics
SQL_LATENCY_SECONDS = Histogram(
    "sql_latency_seconds", 
    "SQL execution latency"
)

SQL_EXECUTED_TOTAL = Counter(
    "sql_executed_total", 
    "SQL queries executed"
)

GUARDRAIL_BLOCKS_TOTAL = Counter(
    "guardrail_blocks_total", 
    "SQL queries blocked by reason", 
    ["reason"]
)

# RAG Metrics
RAG_RETRIEVAL_LATENCY_SECONDS = Histogram(
    "rag_retrieval_latency_seconds",
    "RAG retrieval latency"
)
