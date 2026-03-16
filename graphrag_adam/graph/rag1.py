"""
rag.py — GraphRAG answer engine combining BM25 retrieval + graph traversal.

Answering pipeline:
  1. BM25 search over document chunks
  2. NER to extract variable mentions from top chunks
  3. Graph traversal to find derivation chain for target variable
  4. Rule matching + code generation
  5. Return unified evidence package
"""

from typing import Dict, Any, Optional, List
from graphrag_adam.graph.search import SimpleIndexer
from graphrag_adam.extraction.ner import extract_entities
from graphrag_adam.mapping.synonyms import normalize_var, normalize_endpoint
from graphrag_adam.mapping.rules import (
    match_rule_for_question,
    get_rule_by_id,
    list_all_target_vars,
)
from graphrag_adam.mapping.generator import suggest_mapping_and_derivation


class GraphRAG:
    def __init__(self, kg, chunks: List[Dict]):
        self.kg       = kg
        self.chunks   = chunks
        self.indexer  = SimpleIndexer(chunks)
        # Pre-build var→chunk index for fast graph-chunk linking
        self._var_chunk_index = self._build_var_chunk_index()

    # ------------------------------------------------------------------
    # INDEXING
    # ------------------------------------------------------------------

    def _build_var_chunk_index(self) -> Dict[str, List[str]]:
        """Map ADaM/SDTM variable names → chunk IDs that mention them."""
        index: Dict[str, List[str]] = {}
        all_vars = set(list_all_target_vars().keys())
        for chunk in self.chunks:
            text = chunk.get("text", "").upper()
            for var in all_vars:
                if var in text:
                    index.setdefault(var, []).append(chunk["id"])
        return index

    # ------------------------------------------------------------------
    # MAIN ANSWER METHOD
    # ------------------------------------------------------------------

    def answer(self, question: str,
               sdtm_data: Optional[Dict[str, Any]] = None,
               topk_chunks: int = 8) -> Dict[str, Any]:
        """
        Answer a free-text question about ADaM derivation.

        Returns
        -------
        {
          question        : str,
          target_var      : str,
          all_target_vars : list,
          rule_id         : str | None,
          derivation      : dict (from generator),
          graph_context   : dict (derivation chain from KG),
          evidence        : list of top chunks with entities,
          chunk_sources   : list of chunk IDs mentioning target var,
        }
        """
        # Step 1 — BM25 retrieval
        hits = self.indexer.search(question, topk=topk_chunks)

        # Step 2 — Entity extraction from top chunks
        evidence       = []
        candidate_vars = set()
        for h in hits:
            ent = extract_entities(h)
            evidence.append({
                "chunk_id": h.get("id", ""),
                "doc":      h.get("doc", ""),
                "header":   h.get("header", ""),
                "score":    round(h.get("score", 0.0), 4),
                "entities": ent,
            })
            for v in ent.get("adam_vars", []):
                candidate_vars.add(v)
            for v in ent.get("sdtm_vars", []):
                candidate_vars.add(v)

        # Step 3 — Variable & endpoint normalization
        endpoint    = normalize_endpoint(question)
        target_var  = normalize_var(question, list(candidate_vars))
        all_targets = normalize_var(
            question, list(candidate_vars), return_all=True
        )
        if isinstance(all_targets, str):
            all_targets = [all_targets]

        # Step 4 — Rule matching (uses scored matching from rules.py)
        rule = match_rule_for_question(question, target_var)

        # Step 5 — Graph traversal for derivation chain
        graph_context = self._get_graph_context(target_var, rule)

        # Step 6 — Code generation
        mapping = suggest_mapping_and_derivation(rule, target_var, sdtm_data)

        # Step 7 — Chunk sources from graph index
        chunk_sources = self._var_chunk_index.get(target_var, [])

        return {
            "question":        question,
            "endpoint":        endpoint,
            "target_var":      target_var,
            "all_target_vars": all_targets,
            "rule_id":         rule.get("id") if rule else None,
            "derivation":      mapping,
            "graph_context":   graph_context,
            "evidence":        evidence[:5],
            "chunk_sources":   chunk_sources[:10],
        }

    # ------------------------------------------------------------------
    # GRAPH CONTEXT RETRIEVAL
    # ------------------------------------------------------------------

    def _get_graph_context(self, target_var: str,
                           rule: Optional[Dict]) -> Dict[str, Any]:
        """
        Walk the knowledge graph from the target variable node to surface:
          - Its derivation rule
          - SDTM source variables
          - Co-occurring ADaM variables
          - Document evidence chunks
          - Censoring hierarchy (ADTTE)
          - Dataset membership
        """
        chain = self.kg.get_derivation_chain(target_var)

        # Enrich with rule info if graph rule node exists
        rule_node_data = {}
        if rule:
            rule_node_id = f"RULE::{rule.get('id','')}"
            if self.kg.G.has_node(rule_node_id):
                rule_node_data = dict(self.kg.G.nodes[rule_node_id])

        # Resolve SDTM source labels
        sdtm_resolved = []
        for sn in chain.get("sdtm_sources", []):
            if self.kg.G.has_node(sn):
                d = self.kg.G.nodes[sn]
                sdtm_resolved.append({
                    "node_id": sn,
                    "domain":  d.get("domain", ""),
                    "var":     d.get("name", ""),
                })

        # Resolve co-occurring var labels
        co_resolved = []
        for cn in chain.get("co_vars", []):
            if self.kg.G.has_node(cn):
                co_resolved.append(self.kg.G.nodes[cn].get("name", cn))

        # Censoring hierarchy if available
        cnsr_chain = []
        cnsr_node = "ADAM::CNSR"
        if self.kg.G.has_node(cnsr_node):
            for u, v, d in self.kg.G.edges(data=True):
                if u == cnsr_node and d.get("type") == "CENSORED_BY":
                    if self.kg.G.has_node(v):
                        nd = self.kg.G.nodes[v]
                        cnsr_chain.append({
                            "domain": nd.get("domain", ""),
                            "var":    nd.get("name", ""),
                            "weight": d.get("weight", 0),
                        })
            cnsr_chain.sort(key=lambda x: x["weight"], reverse=True)

        return {
            "variable":          target_var,
            "dataset":           chain.get("node_data", {}).get("dataset", ""),
            "rules":             chain.get("rules", []),
            "rule_node":         rule_node_data,
            "sdtm_sources":      sdtm_resolved,
            "co_occurring_vars": co_resolved,
            "document_chunks":   chain.get("chunks", []),
            "censoring_chain":   cnsr_chain,
            "graph_stats":       self.kg.stats(),
        }

    # ------------------------------------------------------------------
    # DATASET-LEVEL QUERY
    # ------------------------------------------------------------------

    def get_dataset_overview(self, adam_ds: str) -> Dict[str, Any]:
        """
        Return all variables, rules, and SDTM sources for one ADaM dataset.
        Useful for generating a full dataset scaffold.
        """
        sub_kg = self.kg.get_subgraph_for_dataset(adam_ds)
        vars_in_ds, rules_in_ds, sdtm_in_ds = [], [], []

        for nid, d in sub_kg.G.nodes(data=True):
            if d.get("kind") == "adam_var":
                vars_in_ds.append(d.get("name", nid))
            elif d.get("kind") == "rule":
                rules_in_ds.append(d.get("name", nid))
            elif d.get("kind") == "sdtm_var":
                sdtm_in_ds.append(f"{d.get('domain','')}.{d.get('name','')}")

        return {
            "adam_ds":      adam_ds,
            "variables":    vars_in_ds,
            "rules":        rules_in_ds,
            "sdtm_sources": sdtm_in_ds,
            "stats":        sub_kg.stats(),
        }
