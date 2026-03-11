import pytest
from unittest.mock import AsyncMock, MagicMock
from sql_ops_agent.orchestrator import AgentOrchestrator, AgentResult
from sql_ops_agent.rag.retriever import RetrievalResult, DocChunk
from sql_ops_agent.llm.base import ChatResult

@pytest.mark.asyncio
async def test_citation_guardrail_fail_closed():
    # Setup
    mock_llm = AsyncMock()
    mock_retriever = MagicMock()
    mock_executor = AsyncMock()
    
    orchestrator = AgentOrchestrator(mock_llm, mock_retriever, mock_executor)
    
    # 1. Mock Retrieval: Returns 1 legitimate chunk
    mock_retriever.retrieve.return_value = RetrievalResult(
        chunks=[DocChunk(doc_id="valid_doc", chunk_id="0", source_title="Valid", source_path="mock_path", text="content")],
        scores=[1.0],
        insufficient_evidence=False
    )
    
    # 2. Mock LLM: Returns an answer with an INVALID citation (hallucination)
    # The valid citation is "valid_doc:0", but LLM says "fake_doc:99"
    mock_llm.chat.return_value = ChatResult(
        text='{"plan": "answer", "sql": null, "answer_text": "Fact.", "citations": ["fake_doc:99"]}',
        usage={}
    )
    
    # Run
    result = await orchestrator.run("test query")
    
    # Assert
    assert result.outcome == "NO_ANSWER"
    assert "blocked due to invalid citations" in result.answer
    assert "invalid_citations" in result.blocked_reason
    assert len(result.citations) == 0  # Should strip bad citations or return none? 
    # Logic returns valid_citations (which is empty here)
