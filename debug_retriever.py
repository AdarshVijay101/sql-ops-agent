from pathlib import Path
from sql_ops_agent.rag.retriever import SimpleRetriever


def debug_retrieval():
    r = SimpleRetriever(Path("rag/docs"))
    res = r.retrieve("Show me all users", k=5)
    print("Chunks found:")
    for c in res.chunks:
        print(f"ID: {c.doc_id}:{c.chunk_id}")


debug_retrieval()
