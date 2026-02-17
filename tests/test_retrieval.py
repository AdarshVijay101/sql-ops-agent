from pathlib import Path
from sql_ops_agent.rag.retriever import SimpleRetriever

def test_retrieval_basic(tmp_path):
    # Create dummy docs
    d1 = tmp_path / "deployment.md"
    d1.write_text("To deploy, run the deploy script.\n\nUse --force to overwrite.", encoding="utf-8")
    
    d2 = tmp_path / "schema.md"
    d2.write_text("The users table contains user data.\n\nThe orders table contains order data.", encoding="utf-8")
    
    retriever = SimpleRetriever(tmp_path)
    
    results = retriever.retrieve("how to deploy", k=1)
    assert len(results) == 1
    assert "deploy script" in results[0].text
    assert results[0].doc_id == "deployment"

def test_retrieval_no_match(tmp_path):
    # Empty dir
    retriever = SimpleRetriever(tmp_path)
    results = retriever.retrieve("anything")
    assert len(results) == 0
