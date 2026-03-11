from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol, Any, List


@dataclass(frozen=True)
class ChatMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass(frozen=True)
class ChatResult:
    text: str
    usage: dict[str, Any] = field(default_factory=dict)  # tokens, latency, etc.


class LLMClient(Protocol):
    """
    Protocol for a provider-agnostic LLM client.
    """

    async def chat(
        self, messages: List[ChatMessage], *, temperature: float = 0.0, stop: List[str] | None = None
    ) -> ChatResult: ...
