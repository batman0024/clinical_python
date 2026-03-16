
import math
from typing import List, Dict
from collections import Counter, defaultdict
from graphrag_adam.extraction.chunking import tokenize


class SimpleIndexer:
    def __init__(self, chunks: List[Dict]):
        self.chunks = chunks
        self.N = len(chunks)
        self.doc_tokens = [tokenize(c.get("text", "")) for c in chunks]
        self.dfs = defaultdict(int)
        for toks in self.doc_tokens:
            for t in set(toks):
                self.dfs[t] += 1

    def score(self, q_tokens, doc_idx):
        toks = self.doc_tokens[doc_idx]
        if not toks:
            return 0.0
        tf = Counter(toks)
        score = 0.0
        for t in q_tokens:
            if t in tf:
                df = self.dfs.get(t, 1)
                idf = math.log((self.N + 1) / (df + 1)) + 1.0
                score += (tf[t] / len(toks)) * idf
        return score

    def search(self, query: str, topk=10):
        q_toks = tokenize(query)
        scored = [(i, self.score(q_toks, i)) for i in range(self.N)]
        scored.sort(key=lambda x: x[1], reverse=True)
        results = []
        for i, s in scored[:topk]:
            c = self.chunks[i].copy()
            c["score"] = s
            results.append(c)
        return results
