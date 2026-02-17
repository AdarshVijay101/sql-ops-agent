from __future__ import annotations
import httpx
import time
from typing import List, Any
from .base import ChatMessage, ChatResult
from sql_ops_agent.observability.metrics import LLM_LATENCY_SECONDS

class OpenAICompatibleClient:
    """
    Works with local servers that implement an OpenAI-compatible API,
    such as llama-cpp-python server or vLLM's OpenAI-compatible server.
    """

    def __init__(self, base_url: str, api_key: str | None, model: str, timeout_s: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_s = timeout_s

    async def chat(
        self, 
        messages: List[ChatMessage], 
        *, 
        temperature: float = 0.0,
        stop: List[str] | None = None
    ) -> ChatResult:
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
        finally:
            # Measure latency regardless of success/fail
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
