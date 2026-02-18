from __future__ import annotations
import httpx
import time
import json
import logging
from typing import List, Any
from .base import ChatMessage, ChatResult
from sql_ops_agent.observability.metrics import LLM_LATENCY_SECONDS

logger = logging.getLogger(__name__)

class MockLLMClient:
    """
    Deterministic Mock LLM for Demo Mode or Testing.
    Returns canned responses for standard demo queries.
    """
    def __init__(self, model: str = "demo-mock"):
        self.model = model

    async def chat(self, messages: List[ChatMessage], *, temperature: float = 0.0, stop=None) -> ChatResult:
        query = messages[-1].content.lower()
        logger.info(f"MockLLM received query: {query}")
        
        # Simulate latency
        time.sleep(0.1) 

        # Canned responses for the demo script
        if "top 5 orders" in query:
             resp_obj = {
                 "plan": "Select top 5 orders by amount desc (DEMO MODE)",
                 "sql": "SELECT * FROM orders ORDER BY amount DESC LIMIT 5",
                 "answer_text": "[DEMO] Here are the top 5 orders.",
                 "citations": ["schema"] 
             }
        elif "drop the orders" in query or "drop table" in query:
             resp_obj = {
                 "plan": "User wants to drop table. I will generate SQL to test guardrails (DEMO MODE)",
                 "sql": "DROP TABLE orders", 
                 "answer_text": "[DEMO] Attempting to drop table.",
                 "citations": []
             }
        elif "how do i deploy" in query or "how to deploy" in query:
             resp_obj = {
                 "plan": "Explain deployment from runbook (DEMO MODE)",
                 "sql": None,
                 "answer_text": "[DEMO] To deploy, run the deployment script as per the runbook.",
                 "citations": ["runbooks:runbooks_0"] 
             }
        else:
             resp_obj = {
                 "plan": "Unknown query (DEMO MODE)",
                 "sql": None,
                 "answer_text": "[DEMO] I don't know the answer to that in demo mode.",
                 "citations": []
             }
             
        return ChatResult(
            text=json.dumps(resp_obj),
            usage={"prompt_tokens": 100, "completion_tokens": 50, "latency_ms": 100}
        )

class OpenAICompatibleClient:
    """
    Works with local servers that implement an OpenAI-compatible API,
    such as llama-cpp-python server or vLLM's OpenAI-compatible server.
    """

    def __init__(self, base_url: str, api_key: str | None, model: str, timeout_s: float = 60.0, allow_mock_fallback: bool = True):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_s = timeout_s
        self.allow_mock_fallback = allow_mock_fallback
        self._mock_client = MockLLMClient(model=f"{model}-mock") if allow_mock_fallback else None

    async def chat(
        self, 
        messages: List[ChatMessage], 
        *, 
        temperature: float = 0.0,
        stop: List[str] | None = None
    ) -> ChatResult:
        
        # Try real client first
        try:
             return await self._chat_real(messages, temperature=temperature, stop=stop)
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout) as e:
             if self.allow_mock_fallback and self._mock_client:
                  logger.warning(f"LLM connection failed ({str(e)}). Falling back to MockLLM (Demo Mode).")
                  return await self._mock_client.chat(messages, temperature=temperature, stop=stop)
             raise e

    async def _chat_real(self, messages: List[ChatMessage], *, temperature: float = 0.0, stop: List[str] | None = None) -> ChatResult:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "temperature": temperature,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        if stop:
            payload["stop"] = stop

        t0 = time.time()
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                url = f"{self.base_url}/chat/completions"
                r = await client.post(url, json=payload, headers=headers)
                r.raise_for_status()
                data = r.json()
        except Exception:
            raise # Re-raise for the fallback in chat()
        finally:
            latency_s = time.time() - t0
            LLM_LATENCY_SECONDS.labels(model=self.model).observe(latency_s)

        latency_ms = int(latency_s * 1000)
        
        try:
            choice = data["choices"][0]
            text = choice["message"]["content"]
            usage = data.get("usage", {})
            usage["latency_ms"] = latency_ms
        except (KeyError, IndexError) as e:
             raise RuntimeError(f"Invalid response format from LLM: {data}") from e

        return ChatResult(text=text, usage=usage)
