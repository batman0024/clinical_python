
from typing import Dict, Any
from graphrag_adam.graph.search import SimpleIndexer
from graphrag_adam.extraction.ner import extract_entities
from graphrag_adam.mapping.synonyms import normalize_var
from graphrag_adam.mapping.rules import match_rule_for_question
from graphrag_adam.mapping.generator import suggest_mapping_and_derivation


class GraphRAG:
    def __init__(self, kg, chunks):
        self.kg = kg
        self.chunks = chunks
        self.indexer = SimpleIndexer(chunks)

    def answer(self, question: str, sdtm_data=None):
        hits = self.indexer.search(question, topk=8)
        evidence = []
        candidate_vars = set()
        for h in hits:
            ent = extract_entities(h)
            evidence.append({"chunk": h, "entities": ent})
            for v in ent.get("adam_vars", []):
                candidate_vars.add(v)

        target = normalize_var(question, candidate_vars)
        rule = match_rule_for_question(question, target)
        mapping = suggest_mapping_and_derivation(rule, target, sdtm_data)

        return {
            "question": question,
            "target_var": target,
            "rule_id": rule.get("id") if rule else None,
            "derivation": mapping,
            "evidence": evidence[:5]
        }
