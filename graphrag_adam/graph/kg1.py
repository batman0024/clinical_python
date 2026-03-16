"""
kg.py — Knowledge Graph for GraphRAG ADaM.

Node types:
  adam_var    : ADaM variable (e.g. ADAM::AVAL)
  sdtm_var    : SDTM variable (e.g. SDTM::LB::LBSTRESN)
  adam_ds     : ADaM dataset cluster (e.g. DS::ADLB)
  sdtm_domain : SDTM domain cluster (e.g. DOM::LB)
  rule        : Derivation rule node (e.g. RULE::ADTTE_OS)
  text_chunk  : Document chunk from protocol/SAP

Edge types:
  DERIVED_FROM    : adam_var → sdtm_var
  MEMBER_OF       : adam_var → adam_ds  /  sdtm_var → sdtm_domain
  GOVERNED_BY     : adam_var → rule
  RULE_USES       : rule → sdtm_var
  DOCUMENTED_IN   : adam_var/rule → text_chunk
  CO_OCCURS       : adam_var ↔ adam_var (same derivation rule)
  CENSORED_BY     : CNSR → censor source sdtm_var
  BASE_OF         : BASE → AVAL (BDS relationship)
"""

import networkx as nx
import itertools
from typing import Dict, Any, List, Optional, Tuple


class KnowledgeGraph:
    def __init__(self):
        self.G = nx.MultiDiGraph()

    # ------------------------------------------------------------------
    # NODE ADDITION
    # ------------------------------------------------------------------

    def add_chunk(self, chunk: Dict):
        node_id = chunk["id"]
        self.G.add_node(node_id, **{
            "kind":   "text_chunk",
            "doc":    chunk.get("doc", ""),
            "header": chunk.get("header", ""),
            "text":   chunk.get("text", ""),
            "label":  chunk.get("header", node_id)[:60],
        })

    def add_adam_var(self, var: str, dataset: str = "",
                     label: str = "", derivation_type: str = ""):
        node_id = f"ADAM::{var}"
        if not self.G.has_node(node_id):
            self.G.add_node(node_id,
                kind="adam_var",
                name=var,
                dataset=dataset.upper(),
                label=var,
                derivation_type=derivation_type,
            )
        # Auto-link to dataset cluster
        if dataset:
            self._ensure_dataset_node(dataset, "adam_ds")
            self._add_edge_once(node_id, f"DS::{dataset.upper()}",
                                "MEMBER_OF", weight=1.0)

    def add_sdtm_var(self, domain: str, varname: str, label: str = ""):
        node_id = f"SDTM::{domain.upper()}::{varname.upper()}"
        if not self.G.has_node(node_id):
            self.G.add_node(node_id,
                kind="sdtm_var",
                domain=domain.upper(),
                name=varname.upper(),
                label=f"{domain}.{varname}",
            )
        # Auto-link to domain cluster
        self._ensure_dataset_node(domain, "sdtm_domain")
        self._add_edge_once(node_id, f"DOM::{domain.upper()}",
                            "MEMBER_OF", weight=1.0)

    def add_rule_node(self, rule: Dict[str, Any]):
        """Add a derivation rule as a first-class graph node."""
        rule_id = rule.get("id", "UNKNOWN")
        node_id = f"RULE::{rule_id}"
        if not self.G.has_node(node_id):
            self.G.add_node(node_id,
                kind="rule",
                name=rule_id,
                label=rule_id,
                adam_ds=rule.get("adam_ds", ""),
                adam_class=rule.get("adam_class", ""),
                desc=rule.get("desc", "")[:120],
            )
        return node_id

    def _ensure_dataset_node(self, name: str, kind: str):
        prefix = "DS" if kind == "adam_ds" else "DOM"
        node_id = f"{prefix}::{name.upper()}"
        if not self.G.has_node(node_id):
            self.G.add_node(node_id,
                kind=kind,
                name=name.upper(),
                label=name.upper(),
            )

    # ------------------------------------------------------------------
    # EDGE ADDITION
    # ------------------------------------------------------------------

    def _add_edge_once(self, src: str, dst: str,
                       etype: str, weight: float = 1.0):
        """Add edge only if this (src, dst, type) doesn't already exist."""
        for _, _, d in self.G.edges(src, data=True):
            if d.get("type") == etype and _ == src:
                pass  # MultiDiGraph — check differently
        # Check existing edges between src→dst of this type
        existing = [
            d for u, v, d in self.G.edges(data=True)
            if u == src and v == dst and d.get("type") == etype
        ]
        if not existing:
            self.G.add_edge(src, dst, type=etype, weight=weight)

    def add_edge(self, src: str, dst: str,
                 etype: str, weight: float = 1.0):
        self.G.add_edge(src, dst, type=etype, weight=weight)

    # ------------------------------------------------------------------
    # RULE-DRIVEN GRAPH POPULATION
    # ------------------------------------------------------------------

    def populate_from_rule(self, rule: Dict[str, Any]):
        """
        Given a rule dict from rules.py, add all nodes and edges:
          - Rule node
          - ADaM target variable nodes
          - SDTM source variable nodes
          - DERIVED_FROM, GOVERNED_BY, RULE_USES, CO_OCCURS edges
          - Special edges: CENSORED_BY (ADTTE), BASE_OF (BDS)
        """
        rule_id   = rule.get("id", "UNKNOWN")
        adam_ds   = rule.get("adam_ds", "")
        rule_node = self.add_rule_node(rule)

        # Add ADaM target variables
        target_vars = rule.get("target_vars", [])
        adam_nodes  = []
        for var in target_vars:
            self.add_adam_var(var, dataset=adam_ds,
                              derivation_type=rule.get("adam_class", ""))
            adam_node = f"ADAM::{var}"
            adam_nodes.append(adam_node)
            # var ← governed by rule
            self._add_edge_once(adam_node, rule_node,
                                "GOVERNED_BY", weight=1.0)

        # Add SDTM source variables
        for src in rule.get("sources", []):
            domain = src.get("domain", "")
            for var in src.get("vars", []):
                self.add_sdtm_var(domain, var)
                sdtm_node = f"SDTM::{domain.upper()}::{var.upper()}"
                # rule uses SDTM var
                self._add_edge_once(rule_node, sdtm_node,
                                    "RULE_USES", weight=1.0)
                # ADaM target vars derived from SDTM vars
                for av in adam_nodes:
                    self._add_edge_once(av, sdtm_node,
                                        "DERIVED_FROM", weight=0.8)

        # CO_OCCURS edges between target vars in same rule
        for va, vb in itertools.combinations(adam_nodes, 2):
            self._add_edge_once(va, vb, "CO_OCCURS", weight=0.5)
            self._add_edge_once(vb, va, "CO_OCCURS", weight=0.5)

        # Special: censoring hierarchy edges for ADTTE
        if rule.get("adam_class") == "ADTTE":
            cnsr_node = f"ADAM::CNSR"
            if self.G.has_node(cnsr_node):
                for ch in rule.get("cnsr_hierarchy", []):
                    src_domain = ch.get("source", "")
                    src_var    = ch.get("var", "")
                    if src_domain and src_var:
                        self.add_sdtm_var(src_domain, src_var)
                        sdtm_node = f"SDTM::{src_domain.upper()}::{src_var.upper()}"
                        self._add_edge_once(
                            cnsr_node, sdtm_node, "CENSORED_BY",
                            weight=1.0 / (ch.get("order", 1))
                        )

        # Special: BASE→AVAL edge for BDS datasets
        if rule.get("adam_class") == "BDS":
            base_node = f"ADAM::BASE"
            aval_node = f"ADAM::AVAL"
            if self.G.has_node(base_node) and self.G.has_node(aval_node):
                self._add_edge_once(base_node, aval_node,
                                    "BASE_OF", weight=1.0)

    def populate_from_rules(self, rules: List[Dict[str, Any]]):
        """Populate entire graph from the full rule library."""
        for rule in rules:
            self.populate_from_rule(rule)

    # ------------------------------------------------------------------
    # DOCUMENT CHUNK LINKING
    # ------------------------------------------------------------------

    def link_chunk_to_vars(self, chunk_id: str,
                           adam_vars: List[str],
                           sdtm_vars: List[Tuple[str, str]]):
        """
        Link a text chunk to the ADaM/SDTM variables it mentions.
        adam_vars  : list of var names e.g. ['AVAL','CNSR']
        sdtm_vars  : list of (domain, var) tuples e.g. [('DS','DSDECOD')]
        """
        for var in adam_vars:
            node_id = f"ADAM::{var}"
            if self.G.has_node(node_id):
                self._add_edge_once(node_id, chunk_id,
                                    "DOCUMENTED_IN", weight=0.6)

        for domain, var in sdtm_vars:
            node_id = f"SDTM::{domain.upper()}::{var.upper()}"
            if self.G.has_node(node_id):
                self._add_edge_once(node_id, chunk_id,
                                    "DOCUMENTED_IN", weight=0.6)

    # ------------------------------------------------------------------
    # QUERYING
    # ------------------------------------------------------------------

    def neighbors(self, node_id: str,
                  max_deg: int = 50,
                  edge_types: Optional[List[str]] = None) -> List[str]:
        """
        Return neighbor node IDs, optionally filtered by edge type.
        Includes both successors and predecessors for undirected feel.
        """
        result = set()
        for u, v, d in self.G.edges(data=True):
            if edge_types and d.get("type") not in edge_types:
                continue
            if u == node_id:
                result.add(v)
            if v == node_id:
                result.add(u)
        return list(itertools.islice(result, max_deg))

    def get_derivation_chain(self, adam_var: str) -> Dict[str, Any]:
        """
        For a given ADaM variable, return its full derivation context:
        rule, SDTM sources, co-occurring vars, and document evidence.
        """
        node_id = f"ADAM::{adam_var}"
        if not self.G.has_node(node_id):
            return {"error": f"Variable {adam_var} not in graph"}

        rules, sdtm_sources, co_vars, chunks = [], [], [], []

        for u, v, d in self.G.edges(data=True):
            etype = d.get("type", "")
            if u == node_id:
                if etype == "GOVERNED_BY":
                    rules.append(v)
                elif etype == "DERIVED_FROM":
                    sdtm_sources.append(v)
                elif etype == "CO_OCCURS":
                    co_vars.append(v)
                elif etype == "DOCUMENTED_IN":
                    chunks.append(v)

        return {
            "variable":     adam_var,
            "rules":        rules,
            "sdtm_sources": sdtm_sources,
            "co_vars":      co_vars,
            "chunks":       chunks,
            "node_data":    dict(self.G.nodes[node_id]),
        }

    def get_subgraph_for_dataset(self, adam_ds: str) -> "KnowledgeGraph":
        """Return a sub-KG containing only nodes related to one ADaM dataset."""
        ds_node = f"DS::{adam_ds.upper()}"
        relevant = {ds_node}
        for nid, data in self.G.nodes(data=True):
            if data.get("dataset", "").upper() == adam_ds.upper():
                relevant.add(nid)
            if data.get("adam_ds", "").upper() == adam_ds.upper():
                relevant.add(nid)
        sub_g = KnowledgeGraph()
        sub_g.G = self.G.subgraph(relevant).copy()
        return sub_g

    def stats(self) -> Dict[str, Any]:
        """Return graph statistics for debugging."""
        kind_counts = {}
        for _, d in self.G.nodes(data=True):
            k = d.get("kind", "unknown")
            kind_counts[k] = kind_counts.get(k, 0) + 1
        edge_counts = {}
        for _, _, d in self.G.edges(data=True):
            t = d.get("type", "unknown")
            edge_counts[t] = edge_counts.get(t, 0) + 1
        return {
            "total_nodes": self.G.number_of_nodes(),
            "total_edges": self.G.number_of_edges(),
            "node_kinds":  kind_counts,
            "edge_types":  edge_counts,
        }

    # ------------------------------------------------------------------
    # SERIALIZATION
    # ------------------------------------------------------------------

    def add_bulk(self, nodes: List[Dict], edges: List[Dict]):
        for n in nodes:
            self.G.add_node(n["id"], **n["props"])
        for e in edges:
            self.add_edge(e["src"], e["dst"], e["type"],
                          e.get("weight", 1.0))

    def to_json(self) -> Dict[str, Any]:
        nodes, links = [], []
        for nid, data in self.G.nodes(data=True):
            nodes.append({"id": nid, **data})
        for u, v, d in self.G.edges(data=True):
            links.append({"source": u, "target": v, **d})
        return {"nodes": nodes, "links": links}
