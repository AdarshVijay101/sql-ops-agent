from __future__ import annotations
import httpx
import time
from typing import List, Any
from .base import ChatMessage, ChatResult

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
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            # vLLM and llama-cpp-python usually expose /v1/chat/completions
            # If base_url already includes /v1, we should handle that, but usually it's the host root.
            # We'll assume base_url is like "http://localhost:8000/v1" if user configured it so,
            # or "http://localhost:8000" and we append "/v1/...".
            # Standard convention: base_url includes /v1.
            
            url = f"{self.base_url}/chat/completions"
            
            try:
                r = await client.post(url, json=payload, headers=headers)
                r.raise_for_status()
                data = r.json()
            except httpx.HTTPError as e:
                # Basic error handling, could be improved to return a specific failure result
                raise RuntimeError(f"LLM request failed: {e}") from e

        latency_ms = int((time.time() - t0) * 1000)
        
        try:
            choice = data["choices"][0]
            text = choice["message"]["content"]
            usage = data.get("usage", {})
            usage["latency_ms"] = latency_ms
        except (KeyError, IndexError) as e:
             raise RuntimeError(f"Invalid response format from LLM: {data}") from e

        return ChatResult(text=text, usage=usage)
