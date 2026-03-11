import pytest
from unittest.mock import AsyncMock, MagicMock
from sql_ops_agent.orchestrator import AgentOrchestrator
from sql_ops_agent.llm.base import ChatResult


@pytest.fixture
def mock_llm():
    llm = AsyncMock()
    llm.model = "test-model"  # Needed for metrics
    return llm


@pytest.fixture
def mock_retriever():
    retriever = MagicMock()
    # Mock return value for retrieve
    mock_res = MagicMock()
    mock_res.insufficient_evidence = False
    mock_res.chunks = []
    mock_res.scores = []
    retriever.retrieve.return_value = mock_res
    return retriever


@pytest.fixture
def mock_executor():
    return AsyncMock()


@pytest.mark.asyncio
async def test_agent_run_basic(mock_llm, mock_retriever, mock_executor):
    # Setup LLM response
    # Explicitly make it return the object when awaited
    async def mock_chat(*args, **kwargs):
        return ChatResult(text='{"plan": "test", "sql": "SELECT 1", "answer_text": "done"}', usage={})

    mock_llm.chat.side_effect = mock_chat

    orchestrator = AgentOrchestrator(mock_llm, mock_retriever, mock_executor)

    res = await orchestrator.run("test query")

    assert res.outcome == "SUCCESS"
    # Guardrails add LIMIT 200 automatically
    assert "SELECT 1" in res.sql_executed
    assert "LIMIT 200" in res.sql_executed
    mock_executor.run.assert_called_once()


@pytest.mark.asyncio
async def test_agent_guardrail_block(mock_llm, mock_retriever, mock_executor):
    # Setup LLM to return unsafe SQL
    async def mock_chat(*args, **kwargs):
        return ChatResult(text='{"plan": "drop", "sql": "DROP TABLE users", "answer_text": "dropping"}', usage={})

    mock_llm.chat.side_effect = mock_chat

    orchestrator = AgentOrchestrator(mock_llm, mock_retriever, mock_executor)

    res = await orchestrator.run("drop table")

    assert res.outcome == "BLOCKED_GUARDRAILS"
    assert "write_or_ddl_not_allowed" in res.blocked_reason
    mock_executor.run.assert_not_called()
