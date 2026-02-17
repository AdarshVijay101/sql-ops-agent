from __future__ import annotations
from dataclasses import dataclass
from typing import List
from rank_bm25 import BM25Okapi
import re
from pathlib import Path

@dataclass
class DocChunk:
    doc_id: str
    text: str
    metadata: dict

class SimpleRetriever:
    def __init__(self, docs_dir: Path):
        self.docs_dir = docs_dir
        self.chunks: List[DocChunk] = []
        self.bm25: BM25Okapi | None = None
        self.index_docs()

    def index_docs(self):
        # 1. Load markdown files
        # 2. Split by headers or paragraphs
        # 3. Build BM25
        
        self.chunks = []
        tokenized_corpus = []

        if not self.docs_dir.exists():
            # If dir doesn't exist, we just have empty index (safe fail)
            return

        for f in self.docs_dir.glob("*.md"):
            content = f.read_text(encoding="utf-8")
            # Simple chunking by double newline or headers
            # A more robust one would use langchain/llama_index splitters
            # Here we do a naive split for "minimal dependency"
            raw_chunks = re.split(r"\n\s*\n", content) 
            
            for i, txt in enumerate(raw_chunks):
                if not txt.strip():
                    continue
                
                chunk = DocChunk(
                    doc_id=f.stem,
                    text=txt.strip(),
                    metadata={"source": f.name, "chunk_index": i}
                )
                self.chunks.append(chunk)
                
                # Simple tokenization
                tokenized_corpus.append(txt.lower().split())
        
        if tokenized_corpus:
            self.bm25 = BM25Okapi(tokenized_corpus)

    def retrieve(self, query: str, k: int = 3, score_threshold: float = 0.0) -> List[DocChunk]:
        if not self.bm25 or not self.chunks:
            return []
            
        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)
        
        # Zip scores with chunks
        scored_chunks = list(zip(self.chunks, scores))
        
        # sort by score desc
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        
        # Filter and top-k
        results = []
        for chunk, score in scored_chunks[:k]:
            if score >= score_threshold:
                 results.append(chunk)
        
        return results
