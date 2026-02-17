from __future__ import annotations
import structlog
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import json
import time

from sql_ops_agent.llm.base import ChatMessage
from sql_ops_agent.llm.openai_compatible import OpenAICompatibleClient
from sql_ops_agent.rag.retriever import SimpleRetriever, RetrievalResult
from sql_ops_agent.sql.guardrails import validate_and_rewrite, SQLPolicy, SQLBlocked
from sql_ops_agent.sql.executor import SQLExecutor
from sql_ops_agent.observability.metrics import (
    REQUESTS_TOTAL, 
    RAG_RETRIEVAL_LATENCY_SECONDS,
    GUARDRAIL_BLOCKS_TOTAL,
    LLM_TOKENS_TOTAL
)

logger = structlog.get_logger()

@dataclass
class AgentResult:
    answer: str
    sql_executed: str | None = None
    rows: List[Dict[str, Any]] | None = None
    citations: List[Dict[str, Any]] = None
    blocked_reason: str | None = None
    outcome: str = "SUCCESS"

class AgentOrchestrator:
    def __init__(self, llm: OpenAICompatibleClient, retriever: SimpleRetriever, executor: SQLExecutor):
        self.llm = llm
        self.retriever = retriever
        self.executor = executor
        self.policy = SQLPolicy(allowed_schemas={"main", "public"})

    async def run(self, user_query: str) -> AgentResult:
        log = logger.bind(query=user_query)
        log.info("agent_run_start")
        
        # 1. Retrieve
        with RAG_RETRIEVAL_LATENCY_SECONDS.time():
            retrieval_res: RetrievalResult = self.retriever.retrieve(user_query, k=5)
        
        log.info("retrieval_complete", 
                 match_count=len(retrieval_res.chunks), 
                 best_score=retrieval_res.scores[0] if retrieval_res.scores else 0.0)

        if retrieval_res.insufficient_evidence:
             log.info("outcome_no_answer", reason="insufficient_evidence")
             REQUESTS_TOTAL.labels(outcome="NO_ANSWER").inc()
             return AgentResult(
                 answer="I cannot answer this question because retrieved documentation does not contain sufficient evidence.",
                 citations=[],
                 blocked_reason="insufficient_evidence",
                 outcome="NO_ANSWER"
             )

        formatted_citations = []
        context_str_parts = []
        for c, score in zip(retrieval_res.chunks, retrieval_res.scores):
             context_str_parts.append(f"[{c.doc_id}:{c.chunk_id}] (Title: {c.source_title})\n{c.text}")
             formatted_citations.append({
                 "doc_id": c.doc_id, 
                 "chunk_id": c.chunk_id, 
                 "title": c.source_title, 
                 "score": score
             })

        context_str = "\n\n".join(context_str_parts)

        # 2. Plan (Prompting)
        system_prompt = (
            "You are a SQL Ops Assistant. You have read-only access to the database.\n"
            "Use the provided Context to answer the user request.\n"
            "Rules:\n"
            "1. If the request requires SQL, generate a valid SQL query (SELECT only).\n"
            "2. Citations are MANDATORY. Verify every claim against the context. Use format [doc_id:chunk_id].\n"
            "3. If the context is insufficient, set 'sql' to null and say 'I don't know' in 'answer_text'.\n"
            "4. Format response as JSON: {\"plan\": \"...\", \"sql\": \"...\" or null, \"answer_text\": \"...\", \"citations\": [\"doc_id:chunk_id\"]}\n"
            "5. Do NOT guess column names. Use the schema in the Context.\n\n"
            f"Context:\n{context_str}"
        )
        
        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_query)
        ]
        
        try:
            # Metrics for tokens would be ideal here if return from llm.chat
            chat_res = await self.llm.chat(messages, temperature=0.0)
            raw_text = chat_res.text
            
            # Record explicit tokens if available
            prompt_tokens = chat_res.usage.get("prompt_tokens", 0)
            completion_tokens = chat_res.usage.get("completion_tokens", 0)
            if prompt_tokens:
                LLM_TOKENS_TOTAL.labels(type="prompt", model=self.llm.model).inc(prompt_tokens)
            if completion_tokens:
                LLM_TOKENS_TOTAL.labels(type="completion", model=self.llm.model).inc(completion_tokens)

            # JSON Parsing
            start = raw_text.find("{")
            end = raw_text.rfind("}")
            if start == -1 or end == -1:
                 log.warning("llm_json_parse_fail", text=raw_text)
                 REQUESTS_TOTAL.labels(outcome="LLM_ERROR").inc() # or partial success?
                 return AgentResult(answer=raw_text, citations=formatted_citations, outcome="LLM_ERROR")
            
            json_str = raw_text[start:end+1]
            try:
                plan_data = json.loads(json_str)
            except json.JSONDecodeError:
                 log.warning("llm_json_decode_fail", text=json_str)
                 REQUESTS_TOTAL.labels(outcome="LLM_ERROR").inc()
                 return AgentResult(answer=raw_text, citations=formatted_citations, outcome="LLM_ERROR")
            
            sql_candidate = plan_data.get("sql")
            answer_text = plan_data.get("answer_text", "")
            
            if not sql_candidate:
                 REQUESTS_TOTAL.labels(outcome="SUCCESS").inc() # Success (Answered without SQL)
                 return AgentResult(answer=answer_text, citations=formatted_citations, outcome="SUCCESS")

            # 3. Guardrails
            try:
                safe_sql = validate_and_rewrite(sql_candidate, self.policy)
            except SQLBlocked as e:
                log.warning("sql_blocked", reason=str(e))
                GUARDRAIL_BLOCKS_TOTAL.labels(reason=str(e)).inc()
                REQUESTS_TOTAL.labels(outcome="BLOCKED_GUARDRAILS").inc()
                return AgentResult(
                    answer=f"Query blocked by safety policy: {str(e)}",
                    sql_executed=sql_candidate,
                    blocked_reason=str(e),
                    citations=formatted_citations,
                    outcome="BLOCKED_GUARDRAILS"
                )
            
            # 4. Execute
            rows = await self.executor.run(safe_sql)
            
            REQUESTS_TOTAL.labels(outcome="SUCCESS").inc()
            return AgentResult(
                answer=answer_text,
                sql_executed=safe_sql,
                rows=rows,
                citations=formatted_citations,
                outcome="SUCCESS"
            )

        except Exception as e:
            log.error("agent_run_failed", error=str(e))
            REQUESTS_TOTAL.labels(outcome="LLM_ERROR").inc() # Catch-all
            return AgentResult(answer=f"Internal error: {str(e)}", outcome="LLM_ERROR")
