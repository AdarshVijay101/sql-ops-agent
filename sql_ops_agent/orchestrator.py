from __future__ import annotations
import structlog
from dataclasses import dataclass
from typing import List, Dict, Any
from pathlib import Path
import json

from sql_ops_agent.llm.base import ChatMessage
from sql_ops_agent.llm.openai_compatible import OpenAICompatibleClient
from sql_ops_agent.rag.retriever import SimpleRetriever
from sql_ops_agent.sql.guardrails import validate_and_rewrite, SQLPolicy, SQLBlocked
from sql_ops_agent.sql.executor import SQLExecutor

logger = structlog.get_logger()

@dataclass
class AgentResult:
    answer: str
    sql_executed: str | None = None
    rows: List[Dict[str, Any]] | None = None
    citations: List[str] = None
    blocked_reason: str | None = None

class AgentOrchestrator:
    def __init__(self, llm: OpenAICompatibleClient, retriever: SimpleRetriever, executor: SQLExecutor):
        self.llm = llm
        self.retriever = retriever
        self.executor = executor
        self.policy = SQLPolicy(allowed_schemas={"main", "public"}) # Default policy

    async def run(self, user_query: str) -> AgentResult:
        log = logger.bind(query=user_query)
        log.info("agent_run_start")

        # 1. Retrieve
        docs = self.retriever.retrieve(user_query, k=3)
        context_str = "\n\n".join([f"doc_id: {d.doc_id}\n{d.text}" for d in docs])
        citations = [d.doc_id for d in docs]
        
        # 2. Plan (Prompting)
        system_prompt = (
            "You are a SQL Ops Assistant. You have read-only access to the database.\n"
            "If the user asks a question that can be answered by SQL, generate a SINGLE SQL query.\n"
            "Format your response as valid JSON with fields: 'plan', 'sql', 'answer_text'.\n"
            "If you cannot answer, set 'sql' to null and explain why in 'answer_text'.\n"
            "If the user asks for documentation help, cite the doc_ids provided in context.\n\n"
            f"Context:\n{context_str}"
        )
        
        # We use a strict JSON mode if available, or just prompt engineering.
        # Minimal prompt engineering for the demo:
        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_query)
        ]
        
        try:
            chat_res = await self.llm.chat(messages, temperature=0.0)
            raw_text = chat_res.text
            
            # Simple JSON extraction (robust implementations use constrained decoding)
            # Find first { and last }
            start = raw_text.find("{")
            end = raw_text.rfind("}")
            if start == -1 or end == -1:
                 # Fallback
                 return AgentResult(answer=raw_text, citations=citations)
            
            json_str = raw_text[start:end+1]
            plan_data = json.loads(json_str)
            
            sql_candidate = plan_data.get("sql")
            answer_text = plan_data.get("answer_text", "")
            
            if not sql_candidate:
                 return AgentResult(answer=answer_text, citations=citations)

            # 3. Guardrails
            try:
                safe_sql = validate_and_rewrite(sql_candidate, self.policy)
            except SQLBlocked as e:
                log.warning("sql_blocked", reason=str(e))
                return AgentResult(
                    answer=f"I cannot execute the query because it violates safety policy: {str(e)}",
                    sql_executed=sql_candidate,
                    blocked_reason=str(e),
                    citations=citations
                )
            
            # 4. Execute
            rows = await self.executor.run(safe_sql)
            
            # 5. Synthesize final answer (optional check or re-prompting)
            # For minimal demo, we return the plan's explanation + rows
            # A full agent might feed rows back to LLM to summarize.
            
            return AgentResult(
                answer=answer_text,
                sql_executed=safe_sql,
                rows=rows,
                citations=citations
            )

        except Exception as e:
            log.error("agent_run_failed", error=str(e))
            return AgentResult(answer=f"Internal error: {str(e)}")
