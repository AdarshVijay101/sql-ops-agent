from __future__ import annotations
from dataclasses import dataclass
from typing import List
from pathlib import Path
import os
from .index import Indexer, DocChunk

@dataclass
class RetrievalResult:
    chunks: List[DocChunk]
    scores: List[float]
    insufficient_evidence: bool = False

class SimpleRetriever:
    def __init__(self, docs_dir: Path):
        self.indexer = Indexer()
        self.indexer.load_and_index(docs_dir)
        # Default threshold: if top score < 1.0 (BM25 scores vary, but 0 means no match)
        # BM25 scores are unbounded, but typically > 0 for matches.
        # We'll use a pragmatic default or env var.
        # Since BM25 scores depends on corpus size/length, hard threshold is tricky.
        # But for "no keywords match", score is 0.
        # We can also check if list is empty.
        
        # User requested NO_ANSWER_THRESHOLD env var.
        # A safe default for BM25 with small corpus is maybe 0.1?
        # Actually, if no terms match, score is 0.
        self.threshold = float(os.getenv("NO_ANSWER_THRESHOLD", "0.01"))

    def retrieve(self, query: str, k: int = 3) -> RetrievalResult:
        if not self.indexer.bm25 or not self.indexer.chunks:
            return RetrievalResult([], [], insufficient_evidence=True)
            
        tokenized_query = self.indexer._tokenize(query)
        scores = self.indexer.bm25.get_scores(tokenized_query)
        
        # Zip scores with chunks
        scored_chunks = list(zip(self.indexer.chunks, scores))
        
        # sort by score desc
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        
        # Filter and top-k
        top_k = scored_chunks[:k]
        
        if not top_k:
             return RetrievalResult([], [], insufficient_evidence=True)

        best_score = top_k[0][1]
        
        if best_score < self.threshold:
             return RetrievalResult([], [], insufficient_evidence=True)
             
        # Separate chunks and scores
        final_chunks = [c for c, s in top_k]
        final_scores = [s for c, s in top_k]
        
        return RetrievalResult(
            chunks=final_chunks,
            scores=final_scores,
            insufficient_evidence=False
        )
