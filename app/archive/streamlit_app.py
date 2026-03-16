
import streamlit as st
from pathlib import Path
import tempfile
import os
import json
from io import StringIO

from graphrag_adam.config import Paths, Options
from graphrag_adam.cli import build_kg
from graphrag_adam.graph.rag import GraphRAG
from graphrag_adam.viz.d3_html import write_d3_html

st.set_page_config(page_title="GraphRAG ADaM", layout="wide")

st.title("GraphRAG ADaM — Spec→Code Mapping Toolkit")

with st.sidebar:
    st.header("Inputs")
    prot_file = st.file_uploader("Protocol (PDF)", type=["pdf"], accept_multiple_files=False)
    sap_file = st.file_uploader("SAP (DOCX)", type=["docx"], accept_multiple_files=False)
    sdtm_files = st.file_uploader("SDTM files (.sas7bdat / .xpt)", type=["sas7bdat", "xpt"], accept_multiple_files=True)
    spec_file = st.file_uploader("SDTM Spec (Excel, optional)", type=["xlsx", "xls"], accept_multiple_files=False)
    shells_file = st.file_uploader("Shells (DOCX, optional)", type=["docx"], accept_multiple_files=False)
    build_btn = st.button("Build Knowledge Graph", type="primary")

if 'state' not in st.session_state:
    st.session_state.state = {}

if build_btn:
    if not prot_file or not sap_file or not sdtm_files:
        st.error("Please upload Protocol PDF, SAP DOCX and at least one SDTM file.")
    else:
        with st.spinner("Saving inputs and building knowledge graph..."):
            workdir = Path(tempfile.mkdtemp(prefix="graphrag_adam_"))
            up_protocol = workdir / "protocol.pdf"
            up_protocol.write_bytes(prot_file.read())
            up_sap = workdir / "sap.docx"
            up_sap.write_bytes(sap_file.read())
            sdtm_dir = workdir / "sdtm"
            sdtm_dir.mkdir(exist_ok=True)
            for f in sdtm_files:
                (sdtm_dir / f.name).write_bytes(f.read())
            up_spec = None
            if spec_file:
                up_spec = workdir / spec_file.name
                up_spec.write_bytes(spec_file.read())
            up_shells = None
            if shells_file:
                up_shells = workdir / shells_file.name
                up_shells.write_bytes(shells_file.read())

            paths = Paths(protocol_pdf=up_protocol,
                          sap_docx=up_sap,
                          sdtm_dir=sdtm_dir,
                          sdtm_spec_excel=up_spec,
                          shells_docx=up_shells,
                          output_dir=workdir / "outputs")
            opts = Options()
            kg, chunks, sdtm = build_kg(paths, opts)

            # Persist in session
            st.session_state.state.update({
                'workdir': str(workdir),
                'paths': paths,
                'kg_json': kg.to_json(),
                'chunks': chunks,
                'sdtm_domains': list(sdtm.keys())
            })
        st.success("Knowledge graph built.")

state = st.session_state.state

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Interactive Knowledge Graph")
    if state.get('kg_json'):
        ghtml = Path(state['workdir']) / "outputs" / "graph.html"
        ghtml.parent.mkdir(parents=True, exist_ok=True)
        write_d3_html(state['kg_json'], ghtml, embed_data=True)
        html_str = ghtml.read_text(encoding='utf-8')
        st.components.v1.html(html_str, height=700, scrolling=True)
    else:
        st.info("Upload files and click *Build Knowledge Graph* to view the graph.")

with col2:
    st.subheader("Ask a question")
    q = st.text_area("Example: How do I calculate the primary endpoint for subject 101?", height=110)
    if st.button("Answer"):
        if not state.get('kg_json'):
            st.error("Please build the knowledge graph first.")
        else:
            from graphrag_adam.graph.kg import KnowledgeGraph
            kg = KnowledgeGraph()
            # rebuild graph from JSON for RAG (we only need chunks for search)
            # However, GraphRAG uses chunks list, not the network itself
            chunks = state['chunks']
            rag = GraphRAG(kg, chunks)
            ans = rag.answer(q)
            st.markdown(f"**Target variable**: `{ans['target_var']}`")
            st.markdown(f"**Matched rule**: `{ans['rule_id']}`")
            der = ans.get('derivation', {})
            st.markdown("**Derivation description**:")
            st.write(der.get('description',''))
            if der.get('pseudocode'):
                st.markdown("**Pseudocode:**")
                for line in der['pseudocode']:
                    st.write(f"- {line}")
            code = der.get('python_scaffold','')
            if code:
                st.markdown("**Python scaffold:**")
                st.code(code, language='python')
                st.download_button("Download scaffold", data=code.encode('utf-8'), file_name='derivation_scaffold.py')
            if ans.get('evidence'):
                st.markdown("**Top evidence:**")
                for ev in ans['evidence']:
                    ch = ev['chunk']
                    st.write(f"- **{ch['doc'].upper()}**: {ch['header']} — score={ch['score']:.3f}")

st.markdown("---")
with st.expander("Debug / Session info"):
    if state.get('workdir'):
        st.write(f"Workdir: {state['workdir']}")
    if state.get('sdtm_domains'):
        st.write({"SDTM domains": state['sdtm_domains']})
