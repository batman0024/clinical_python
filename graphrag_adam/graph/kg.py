
import networkx as nx
from typing import Dict, Any, List
import itertools


class KnowledgeGraph:
    def __init__(self):
        self.G = nx.MultiDiGraph()

    def add_chunk(self, chunk: Dict):
        node_id = chunk["id"]
        self.G.add_node(node_id, **{
            "kind": "text_chunk",
            "doc": chunk["doc"],
            "header": chunk.get("header", ""),
            "text": chunk.get("text", "")
        })

    def add_adam_var(self, var: str):
        node_id = f"ADAM::{var}"
        if not self.G.has_node(node_id):
            self.G.add_node(node_id, kind="adam_var", name=var)

    def add_sdtm_var(self, domain: str, varname: str):
        node_id = f"SDTM::{domain}::{varname}"
        if not self.G.has_node(node_id):
            self.G.add_node(node_id, kind="sdtm_var", domain=domain, name=varname)

    def add_edge(self, src: str, dst: str, etype: str, weight: float = 1.0):
        self.G.add_edge(src, dst, type=etype, weight=weight)

    def add_bulk(self, nodes: List[Dict], edges: List[Dict]):
        for n in nodes:
            self.G.add_node(n["id"], **n["props"])
        for e in edges:
            self.add_edge(e["src"], e["dst"], e["type"])

    def neighbors(self, node_id: str, max_deg=30):
        nbrs = itertools.islice(self.G.neighbors(node_id), 0, max_deg)
        return list(nbrs)

    def to_json(self):
        nodes, links = [], []
        for nid, data in self.G.nodes(data=True):
            nodes.append({"id": nid, **data})
        for u, v, d in self.G.edges(data=True):
            links.append({"source": u, "target": v, **d})
        return {"nodes": nodes, "links": links}
