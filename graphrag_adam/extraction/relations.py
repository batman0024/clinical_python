
from typing import Dict, List


def infer_relations_from_entities(chunk: Dict, ents: Dict) -> List[Dict]:
    """
    Produce relations like:
    - chunk --mentions--> ADaM variable
    - ADaM variable --defined_by--> chunk (if endpoint hint present)
    """
    rels = []
    for v in ents.get("adam_vars", []):
        rels.append({"src": chunk["id"], "dst": f"ADAM::{v}", "type": "mentions"})
        if ents.get("endpoint_hints"):
            for hint in ents["endpoint_hints"]:
                rels.append({"src": f"ADAM::{v}", "dst": chunk["id"], "type": f"defined_by::{hint}"})
    return rels
