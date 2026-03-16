"""
search.py — BM25 search index over document chunks.

Improvements over original:
  - True BM25 (k1/b length normalization) vs raw TF-IDF
  - Header field boosting (3x weight for matches in section header)
  - Variable-name exact match boost
  - Zero-result fallback to most recent chunks
"""

import math
from typing import List, Dict
from collections import Counter, defaultdict
from graphrag_adam.extraction.chunking import tokenize

# BM25 hyperparameters
K1 = 1.5   # term frequency saturation
B  = 0.75  # length normalization factor


class SimpleIndexer:
    def __init__(self, chunks: List[Dict]):
        self.chunks     = chunks
        self.N          = len(chunks)
        self.doc_tokens = [tokenize(c.get("text", "")) for c in chunks]
        self.hdr_tokens = [tokenize(c.get("header", "")) for c in chunks]
        self.avg_dl     = (
            sum(len(t) for t in self.doc_tokens) / max(self.N, 1)
        )
        # Document frequency per token
        self.dfs: Dict[str, int] = defaultdict(int)
        for toks in self.doc_tokens:
            for t in set(toks):
                self.dfs[t] += 1
        # Header frequency per token (separate for boosting)
        self.hdfs: Dict[str, int] = defaultdict(int)
        for toks in self.hdr_tokens:
            for t in set(toks):
                self.hdfs[t] += 1

    def _bm25_score(self, q_tokens: List[str], doc_idx: int) -> float:
        """BM25 score for body text."""
        toks = self.doc_tokens[doc_idx]
        if not toks:
            return 0.0
        tf   = Counter(toks)
        dl   = len(toks)
        score = 0.0
        for t in q_tokens:
            if t not in tf:
                continue
            df  = self.dfs.get(t, 1)
            idf = math.log((self.N - df + 0.5) / (df + 0.5) + 1.0)
            tf_norm = (tf[t] * (K1 + 1)) / (
                tf[t] + K1 * (1 - B + B * dl / max(self.avg_dl, 1))
            )
            score += idf * tf_norm
        return score

    def _header_boost(self, q_tokens: List[str], doc_idx: int) -> float:
        """Extra score for query tokens found in section header."""
        hdr = self.hdr_tokens[doc_idx]
        if not hdr:
            return 0.0
        hdr_set = set(hdr)
        return sum(3.0 for t in q_tokens if t in hdr_set)

    def _var_boost(self, q_tokens: List[str], doc_idx: int) -> float:
        """
        Boost if query contains an ADaM/SDTM variable name (all-caps token)
        and that variable appears in the chunk text.
        """
        chunk_text = self.chunks[doc_idx].get("text", "").upper()
        boost = 0.0
        for t in q_tokens:
            if t.upper() == t and len(t) >= 3:  # looks like a variable name
                if t.upper() in chunk_text:
                    boost += 2.0
        return boost

    def score(self, q_tokens: List[str], doc_idx: int) -> float:
        return (
            self._bm25_score(q_tokens, doc_idx)
            + self._header_boost(q_tokens, doc_idx)
            + self._var_boost(q_tokens, doc_idx)
        )

    def search(self, query: str, topk: int = 10) -> List[Dict]:
        q_toks  = tokenize(query)
        # Also add uppercase tokens for variable matching
        q_toks_upper = list(set(q_toks + [t.upper() for t in q_toks]))

        scored = [
            (i, self.score(q_toks_upper, i))
            for i in range(self.N)
        ]
        scored.sort(key=lambda x: x[1], reverse=True)

        # Fallback: if all scores are 0, return most recent chunks
        if all(s == 0.0 for _, s in scored):
            scored = list(enumerate([0.0] * self.N))

        results = []
        for i, s in scored[:topk]:
            c = self.chunks[i].copy()
            c["score"] = round(s, 4)
            results.append(c)
        return results

    def search_by_var(self, var_name: str, topk: int = 5) -> List[Dict]:
        """Direct variable-name search — returns chunks mentioning this var."""
        var_upper = var_name.upper()
        hits = [
            {**c, "score": 1.0}
            for c in self.chunks
            if var_upper in c.get("text", "").upper()
               or var_upper in c.get("header", "").upper()
        ]
        return hits[:topk]
