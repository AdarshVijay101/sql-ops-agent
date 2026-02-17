from prometheus_client import Counter, Histogram

# Metrics definition
AGENT_RUN_TOTAL = Counter("agent_run_total", "Total number of agent runs", ["status"])
AGENT_LATENCY_SECONDS = Histogram("agent_latency_seconds", "End-to-end agent latency", ["stage"])
SQL_EXECUTED_TOTAL = Counter("sql_executed_total", "Total SQL queries executed", ["status"])
SQL_BLOCKED_TOTAL = Counter("sql_blocked_total", "Total SQL queries blocked by guardrails", ["reason"])
RAG_RETRIEVAL_LATENCY = Histogram("rag_retrieval_latency_seconds", "Retrieval latency")
LLM_TOKENS_TOTAL = Counter("llm_tokens_total", "Tokens used", ["type", "model"])
