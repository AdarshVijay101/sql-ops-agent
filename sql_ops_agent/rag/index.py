from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path
import re
from rank_bm25 import BM25Okapi

@dataclass
class DocChunk:
    doc_id: str
    chunk_id: str
    text: str
    source_title: str
    source_path: str

class Indexer:
    """
    Handles loading documents, splitting them into chunks, and building the search index.
    """
    def __init__(self):
        self.chunks: List[DocChunk] = []
        self.bm25: Optional[BM25Okapi] = None

    def load_and_index(self, docs_dir: Path):
        self.chunks = []
        tokenized_corpus = []

        if not docs_dir.exists():
            return

        for f in docs_dir.glob("*.md"):
            self._process_file(f, tokenized_corpus)
            
        if tokenized_corpus:
            self.bm25 = BM25Okapi(tokenized_corpus)

    def _process_file(self, f: Path, tokenized_corpus: List[List[str]]):
        content = f.read_text(encoding="utf-8")
        title = f.stem.replace("_", " ").title()
        
        # Split by headers (Markdown headers #, ##, etc.) or double newlines
        # A simple robust way: split by empty lines to get paragraphs, 
        # but attaching headers is better context.
        # For this task, we'll keep it simple: Split by double newlines.
        raw_chunks = re.split(r"\n\s*\n", content)
        
        for i, txt in enumerate(raw_chunks):
            if not txt.strip():
                continue
            
            # Simple clean
            txt = txt.strip()
            
            chunk = DocChunk(
                doc_id=f.stem,
                chunk_id=f"{f.stem}_{i}",
                text=txt,
                source_title=title,
                source_path=f.name
            )
            self.chunks.append(chunk)
            tokenized_corpus.append(self._tokenize(txt))

    def _tokenize(self, text: str) -> List[str]:
        return text.lower().split()
