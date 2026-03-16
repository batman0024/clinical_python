
import argparse
from pathlib import Path
from graphrag_adam.config import Paths, Options
from graphrag_adam.ingestion.protocol import ingest_protocol_pdf
from graphrag_adam.ingestion.sap import ingest_sap_docx
from graphrag_adam.ingestion.sdtm_data import load_sdtm_dir
from graphrag_adam.ingestion.sdtm_spec import load_sdtm_spec
from graphrag_adam.ingestion.shells import parse_shells_docx
from graphrag_adam.extraction.ner import extract_entities
from graphrag_adam.extraction.relations import infer_relations_from_entities
from graphrag_adam.graph.kg import KnowledgeGraph
from graphrag_adam.graph.rag import GraphRAG
from graphrag_adam.viz.export_json import export_graph_json
from graphrag_adam.viz.d3_html import write_d3_html


def build_kg(paths: Paths, opts: Options):
    # 1) ingest
    protocol_chunks = ingest_protocol_pdf(paths.protocol_pdf, opts.chunk_size, opts.chunk_overlap)
    sap_chunks = ingest_sap_docx(paths.sap_docx, opts.chunk_size, opts.chunk_overlap)
    # tag IDs
    for i, c in enumerate(protocol_chunks):
        c["id"] = f"PROT::{i}"
    for i, c in enumerate(sap_chunks):
        c["id"] = f"SAP::{i}"

    # 2) load SDTM data & optional specs
    sdtm = load_sdtm_dir(paths.sdtm_dir)
    spec = load_sdtm_spec(paths.sdtm_spec_excel) if paths.sdtm_spec_excel else None
    shells = parse_shells_docx(paths.shells_docx) if paths.shells_docx else None

    # 3) build KG
    kg = KnowledgeGraph()
    for ch in (protocol_chunks + sap_chunks):
        kg.add_chunk(ch)

    # add SDTM vars
    for dom, payload in sdtm.items():
        for col in payload["meta"]["columns"]:
            kg.add_sdtm_var(dom, str(col).upper())

    # 4) add entities/relations from chunks
    for ch in (protocol_chunks + sap_chunks):
        ents = extract_entities(ch)
        for v in ents.get("adam_vars", []):
            kg.add_adam_var(v)
        for rel in infer_relations_from_entities(ch, ents):
            kg.add_edge(rel["src"], rel["dst"], rel["type"])

    return kg, protocol_chunks + sap_chunks, sdtm


def main():
    ap = argparse.ArgumentParser("graphrag-adam")
    ap.add_argument("--protocol", required=True, help="Path to Protocol PDF")
    ap.add_argument("--sap", required=True, help="Path to SAP DOCX")
    ap.add_argument("--sdtm-dir", required=True, help="Folder with SDTM .sas7bdat/.xpt")
    ap.add_argument("--spec", help="SDTM Spec Excel (optional)")
    ap.add_argument("--shells", help="TNF/TLF Shells DOCX (optional)")
    ap.add_argument("--outdir", default="outputs", help="Output folder")
    ap.add_argument("--ask", help="Ask a question after building KG")
    ap.add_argument("--visualize", action="store_true", help="Write D3 interactive HTML")
    args = ap.parse_args()

    paths = Paths(
        protocol_pdf=Path(args.protocol),
        sap_docx=Path(args.sap),
        sdtm_dir=Path(args.sdtm_dir),
        sdtm_spec_excel=Path(args.spec) if args.spec else None,
        shells_docx=Path(args.shells) if args.shells else None,
        output_dir=Path(args.outdir)
    )
    opts = Options()

    kg, chunks, sdtm = build_kg(paths, opts)

    paths.output_dir.mkdir(parents=True, exist_ok=True)
    gj = kg.to_json()
    export_graph_json(kg, paths.output_dir / "graph.json")

    if args.visualize:
        write_d3_html(gj, paths.output_dir / "graph.html", embed_data=True)
        print(f"[OK] Visualization: {paths.output_dir / 'graph.html'}")

    if args.ask:
        rag = GraphRAG(kg, chunks)
        ans = rag.answer(args.ask, sdtm_data=sdtm)
        (paths.output_dir / "answer.json").write_text(__import__("json").dumps(ans, indent=2), encoding="utf-8")
        print("[Answer]")
        print(f"Target var: {ans['target_var']}")
        print(f"ADaM rule: {ans['rule_id']}")
        print("Derivation:")
        print("\n".join(ans['derivation'].get('pseudocode', [])))
        print("\n--- Python scaffold ---\n")
        print(ans['derivation'].get('python_scaffold', ''))
        print("\n[Evidence]")
        for ev in ans['evidence']:
            ch = ev["chunk"]
            print(f"- {ch['doc'].upper()} :: {ch['header']} (score={ch['score']:.3f})")

if __name__ == '__main__':
    main()
