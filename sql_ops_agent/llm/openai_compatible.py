import os
import json
import httpx
import structlog
from typing import List
from sql_ops_agent.llm.base import ChatMessage, ChatResult

logger = structlog.get_logger()


class OpenAICompatibleClient:
    def __init__(self, base_url: str, api_key: str, model: str, allow_mock_fallback: bool):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.allow_mock_fallback = allow_mock_fallback
        self.demo_mode = os.getenv("DEMO_MODE") == "1"

    def _get_mock_response(self, messages: List[ChatMessage]) -> ChatResult:
        # Construct a safe JSON response demonstrating the agent
        # Look for the last user message to make it slightly contextual
        user_query = "this query"
        for m in reversed(messages):
            if m.role == "user":
                user_query = m.content
                break

        mock_json = {
            "plan": f"DEMO MODE: Processing query '{user_query}' without a live LLM.",
            "sql": "SELECT * FROM users LIMIT 5",
            "answer_text": "This is a canned DEMO_MODE response because no live LLM was reachable.",
            "citations": [],
        }

        # Determine if context was provided to simulate citations
        for m in messages:
            if m.role == "system" and "Context:\n" in m.content:
                lines = m.content.split("\n")
                for line in lines:
                    if line.startswith("[") and "]" in line:
                        # Extract something looking like [doc_id:chunk_id]
                        citation = line[1 : line.find("]")]
                        mock_json["citations"].append(citation)
                        break  # Just use one

        return ChatResult(text=json.dumps(mock_json), usage={"prompt_tokens": 10, "completion_tokens": 20})

    async def chat(
        self, messages: List[ChatMessage], *, temperature: float = 0.0, stop: List[str] | None = None
    ) -> ChatResult:

        if self.demo_mode:
            logger.info("llm_demo_mode_active")
            return self._get_mock_response(messages)

        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
        }
        if stop:
            payload["stop"] = stop

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
                res.raise_for_status()
                data = res.json()

                text = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})

                return ChatResult(text=text, usage=usage)
        except Exception as e:
            if self.allow_mock_fallback:
                logger.warning("llm_connection_failed", error=str(e), fallback="mock")
                return self._get_mock_response(messages)
            raise e
