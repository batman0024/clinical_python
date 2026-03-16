“””
streamlit_app.py — GraphRAG ADaM Spec→Code Mapping Toolkit
Enhanced UI with advanced features for clinical data programming workflows.
“””

import streamlit as st
from pathlib import Path
import tempfile
import json
import time
import pandas as pd
from datetime import datetime

from graphrag_adam.config import Paths, Options
from graphrag_adam.cli import build_kg
from graphrag_adam.graph.rag import GraphRAG
from graphrag_adam.graph.kg import KnowledgeGraph
from graphrag_adam.viz.d3_html import write_d3_html
from graphrag_adam.mapping.rules import RULES, get_rules_by_dataset, list_all_target_vars
from graphrag_adam.mapping.synonyms import normalize_endpoint, get_vars_for_dataset
from graphrag_adam.mapping.generator import suggest_mapping_and_derivation
from graphrag_adam.ingestion.sdtm_data import get_domain_summary

# ─────────────────────────────────────────────────────────────────────────────

# PAGE CONFIG & CUSTOM CSS

# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
page_title=“GraphRAG ADaM”,
page_icon=“⬡”,
layout=“wide”,
initial_sidebar_state=“expanded”,
)

st.markdown(”””

<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600&family=DM+Sans:wght@300;400;500;600&family=Space+Mono:wght@400;700&display=swap');

/* ── Root variables ── */
:root {
    --bg:         #0d1117;
    --bg2:        #161b22;
    --bg3:        #21262d;
    --border:     #30363d;
    --accent:     #00d4aa;
    --accent2:    #4a9eff;
    --accent3:    #ff7b54;
    --text:       #e6edf3;
    --text-dim:   #8b949e;
    --success:    #3fb950;
    --warning:    #d29922;
    --danger:     #f85149;
    --font-mono:  'JetBrains Mono', monospace;
    --font-ui:    'DM Sans', sans-serif;
}

/* ── Global ── */
html, body, [class*="css"] {
    font-family: var(--font-ui) !important;
    background-color: var(--bg) !important;
    color: var(--text) !important;
}

.stApp { background-color: var(--bg) !important; }

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem !important; max-width: 100% !important; }

/* ── Custom header bar ── */
.app-header {
    background: linear-gradient(135deg, #0d1117 0%, #161b22 50%, #0d2030 100%);
    border-bottom: 1px solid var(--border);
    padding: 1.2rem 2rem;
    margin: -1.5rem -1rem 1.5rem -1rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    position: relative;
    overflow: hidden;
}
.app-header::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: repeating-linear-gradient(
        90deg,
        transparent,
        transparent 80px,
        rgba(0,212,170,0.03) 80px,
        rgba(0,212,170,0.03) 81px
    );
}
.app-header-logo {
    font-family: var(--font-mono);
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--accent);
    letter-spacing: -1px;
}
.app-header-title {
    font-family: var(--font-ui);
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--text);
}
.app-header-sub {
    font-size: 0.75rem;
    color: var(--text-dim);
    font-family: var(--font-mono);
}
.app-header-badge {
    margin-left: auto;
    background: rgba(0,212,170,0.1);
    border: 1px solid rgba(0,212,170,0.3);
    color: var(--accent);
    padding: 0.2rem 0.6rem;
    border-radius: 4px;
    font-size: 0.7rem;
    font-family: var(--font-mono);
    letter-spacing: 0.05em;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: var(--bg2) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] .stMarkdown h3 {
    color: var(--accent) !important;
    font-family: var(--font-mono) !important;
    font-size: 0.7rem !important;
    letter-spacing: 0.15em !important;
    text-transform: uppercase !important;
    border-bottom: 1px solid var(--border);
    padding-bottom: 0.5rem;
    margin-bottom: 0.75rem;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: var(--bg3) !important;
    border: 1px dashed var(--border) !important;
    border-radius: 6px !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: var(--accent) !important;
}

/* ── Buttons ── */
.stButton > button {
    font-family: var(--font-mono) !important;
    font-size: 0.8rem !important;
    font-weight: 600 !important;
    border-radius: 4px !important;
    transition: all 0.2s ease !important;
}
.stButton > button[kind="primary"] {
    background: var(--accent) !important;
    color: #0d1117 !important;
    border: none !important;
    width: 100% !important;
    padding: 0.6rem !important;
    letter-spacing: 0.05em !important;
}
.stButton > button[kind="primary"]:hover {
    background: #00e8bb !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0,212,170,0.3) !important;
}
.stButton > button[kind="secondary"] {
    background: transparent !important;
    color: var(--text-dim) !important;
    border: 1px solid var(--border) !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: var(--accent2) !important;
    color: var(--accent2) !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: var(--bg2) !important;
    border-bottom: 1px solid var(--border) !important;
    gap: 0 !important;
    padding: 0 1rem !important;
}
.stTabs [data-baseweb="tab"] {
    font-family: var(--font-mono) !important;
    font-size: 0.78rem !important;
    color: var(--text-dim) !important;
    padding: 0.7rem 1.2rem !important;
    border-bottom: 2px solid transparent !important;
    margin-bottom: -1px !important;
}
.stTabs [aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom-color: var(--accent) !important;
    background: transparent !important;
}
.stTabs [data-baseweb="tab-panel"] {
    padding: 1.5rem 0 !important;
}

/* ── Metric cards ── */
.metric-card {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 1rem 1.2rem;
    position: relative;
    overflow: hidden;
    transition: border-color 0.2s;
}
.metric-card:hover { border-color: var(--accent2); }
.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
}
.metric-value {
    font-family: var(--font-mono);
    font-size: 1.8rem;
    font-weight: 700;
    color: var(--accent);
    line-height: 1;
}
.metric-label {
    font-size: 0.72rem;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-top: 0.3rem;
    font-family: var(--font-mono);
}
.metric-delta {
    font-size: 0.7rem;
    color: var(--success);
    font-family: var(--font-mono);
}

/* ── Code blocks ── */
.stCodeBlock, pre, code {
    font-family: var(--font-mono) !important;
    background: #0d1117 !important;
    border: 1px solid var(--border) !important;
    border-radius: 4px !important;
}

/* ── Expanders ── */
.streamlit-expanderHeader {
    background: var(--bg2) !important;
    border: 1px solid var(--border) !important;
    border-radius: 4px !important;
    font-family: var(--font-mono) !important;
    font-size: 0.8rem !important;
    color: var(--text-dim) !important;
}
.streamlit-expanderHeader:hover { color: var(--accent) !important; }

/* ── Evidence cards ── */
.evidence-card {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent2);
    border-radius: 4px;
    padding: 0.8rem 1rem;
    margin-bottom: 0.5rem;
    font-size: 0.82rem;
}
.evidence-header {
    font-family: var(--font-mono);
    font-size: 0.72rem;
    color: var(--accent2);
    margin-bottom: 0.4rem;
}
.evidence-text { color: var(--text-dim); line-height: 1.5; }
.evidence-score {
    font-family: var(--font-mono);
    font-size: 0.65rem;
    color: var(--text-dim);
    float: right;
}

/* ── Rule cards ── */
.rule-card {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 1rem;
    margin-bottom: 0.5rem;
    cursor: pointer;
    transition: all 0.15s;
}
.rule-card:hover {
    border-color: var(--accent);
    background: rgba(0,212,170,0.05);
}
.rule-id {
    font-family: var(--font-mono);
    font-size: 0.8rem;
    color: var(--accent);
    font-weight: 600;
}
.rule-ds {
    font-size: 0.7rem;
    color: var(--accent2);
    font-family: var(--font-mono);
    float: right;
}
.rule-desc { font-size: 0.82rem; color: var(--text-dim); margin-top: 0.3rem; }

/* ── Status badges ── */
.badge {
    display: inline-block;
    padding: 0.15rem 0.5rem;
    border-radius: 3px;
    font-family: var(--font-mono);
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.05em;
}
.badge-green  { background: rgba(63,185,80,0.15); color: var(--success); border: 1px solid rgba(63,185,80,0.3); }
.badge-blue   { background: rgba(74,158,255,0.15); color: var(--accent2); border: 1px solid rgba(74,158,255,0.3); }
.badge-orange { background: rgba(255,123,84,0.15); color: var(--accent3); border: 1px solid rgba(255,123,84,0.3); }
.badge-teal   { background: rgba(0,212,170,0.1);  color: var(--accent);  border: 1px solid rgba(0,212,170,0.3); }

/* ── Tables ── */
.stDataFrame { border: 1px solid var(--border) !important; border-radius: 4px !important; }
.stDataFrame [data-testid="stDataFrameResizable"] { background: var(--bg2) !important; }

/* ── Text inputs ── */
.stTextArea textarea, .stTextInput input, .stSelectbox select {
    background: var(--bg3) !important;
    border: 1px solid var(--border) !important;
    border-radius: 4px !important;
    color: var(--text) !important;
    font-family: var(--font-mono) !important;
    font-size: 0.82rem !important;
}
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px rgba(0,212,170,0.15) !important;
}

/* ── Progress / spinner ── */
.stProgress > div > div { background: var(--accent) !important; }
.stSpinner > div { border-top-color: var(--accent) !important; }

/* ── Alerts ── */
.stAlert { border-radius: 4px !important; font-family: var(--font-mono) !important; font-size: 0.8rem !important; }

/* ── Sidebar section separator ── */
.sidebar-section {
    border-top: 1px solid var(--border);
    padding-top: 0.8rem;
    margin-top: 0.8rem;
}
.sidebar-label {
    font-family: var(--font-mono);
    font-size: 0.65rem;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-bottom: 0.4rem;
}

/* ── Dividers ── */
hr { border-color: var(--border) !important; }

/* ── Pseudo-step list ── */
.pseudo-step {
    display: flex;
    gap: 0.8rem;
    padding: 0.45rem 0;
    border-bottom: 1px solid rgba(48,54,61,0.5);
    font-size: 0.82rem;
    align-items: flex-start;
}
.pseudo-step:last-child { border-bottom: none; }
.pseudo-num {
    font-family: var(--font-mono);
    font-size: 0.65rem;
    color: var(--accent);
    background: rgba(0,212,170,0.1);
    border: 1px solid rgba(0,212,170,0.2);
    border-radius: 3px;
    padding: 0.1rem 0.35rem;
    white-space: nowrap;
    margin-top: 2px;
}
.pseudo-text { color: var(--text-dim); line-height: 1.4; }

/* ── SDTM domain pills ── */
.domain-pill {
    display: inline-block;
    background: rgba(74,158,255,0.1);
    border: 1px solid rgba(74,158,255,0.25);
    color: var(--accent2);
    padding: 0.2rem 0.55rem;
    border-radius: 3px;
    font-family: var(--font-mono);
    font-size: 0.7rem;
    margin: 0.1rem;
}

/* ── Graph container ── */
.graph-container {
    border: 1px solid var(--border);
    border-radius: 6px;
    overflow: hidden;
    background: #0a0e13;
}

/* ── History item ── */
.history-item {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 0.6rem 0.8rem;
    margin-bottom: 0.4rem;
    cursor: pointer;
    transition: border-color 0.15s;
    font-size: 0.8rem;
}
.history-item:hover { border-color: var(--accent2); }
.history-q { color: var(--text); font-family: var(--font-mono); font-size: 0.75rem; }
.history-meta { color: var(--text-dim); font-size: 0.68rem; margin-top: 0.2rem; }

/* ── Select box ── */
[data-testid="stSelectbox"] > div > div {
    background: var(--bg3) !important;
    border-color: var(--border) !important;
    color: var(--text) !important;
}

/* ── Checkbox ── */
.stCheckbox label { font-family: var(--font-mono) !important; font-size: 0.78rem !important; }

/* ── Slider ── */
.stSlider > div > div > div { background: var(--accent) !important; }
</style>

“””, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────

# SESSION STATE INIT

# ─────────────────────────────────────────────────────────────────────────────

def _init_state():
defaults = {
“kg_built”:      False,
“kg_json”:       None,
“chunks”:        [],
“sdtm_data”:     {},
“sdtm_domains”:  [],
“sdtm_meta”:     {},
“workdir”:       None,
“paths”:         None,
“build_time”:    None,
“graph_stats”:   {},
“qa_history”:    [],
“last_answer”:   None,
“selected_rule”: None,
“active_ds_filter”: “ALL”,
}
for k, v in defaults.items():
if k not in st.session_state:
st.session_state[k] = v

_init_state()
s = st.session_state

# ─────────────────────────────────────────────────────────────────────────────

# HEADER

# ─────────────────────────────────────────────────────────────────────────────

st.markdown(”””

<div class="app-header">
    <div class="app-header-logo">⬡ GR</div>
    <div>
        <div class="app-header-title">GraphRAG ADaM</div>
        <div class="app-header-sub">Spec → Code Mapping Toolkit · Clinical Data Programming</div>
    </div>
    <div class="app-header-badge">v2.0 · No LLM</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────

# SIDEBAR

# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
st.markdown(”### 📂 Input Files”)

```
prot_file  = st.file_uploader("Protocol (PDF)",               type=["pdf"],                   accept_multiple_files=False)
sap_file   = st.file_uploader("SAP (DOCX)",                   type=["docx"],                  accept_multiple_files=False)
sdtm_files = st.file_uploader("SDTM files (.sas7bdat / .xpt)",type=["sas7bdat", "xpt"],       accept_multiple_files=True)
spec_file  = st.file_uploader("SDTM Spec (Excel, optional)",  type=["xlsx", "xls"],           accept_multiple_files=False)
shells_file= st.file_uploader("Shells (DOCX, optional)",      type=["docx"],                  accept_multiple_files=False)

st.markdown('<div class="sidebar-section"></div>', unsafe_allow_html=True)
st.markdown("### ⚙️ Build Options")

col_a, col_b = st.columns(2)
with col_a:
    chunk_size = st.number_input("Chunk size", value=1200, step=100,
                                 min_value=400, max_value=3000,
                                 help="Max characters per chunk")
with col_b:
    topk = st.number_input("Top-K hits", value=8, step=1,
                           min_value=3, max_value=20,
                           help="Chunks to retrieve per query")

enrich_graph = st.checkbox("Enrich graph from spec",  value=True,
                            help="Use Excel spec to add derivation edges")
show_sdtm    = st.checkbox("Show SDTM nodes in graph", value=True)

st.markdown('<div class="sidebar-section"></div>', unsafe_allow_html=True)

build_btn = st.button("⬡  Build Knowledge Graph", type="primary")

# Status panel
if s["kg_built"]:
    st.markdown('<div class="sidebar-section"></div>', unsafe_allow_html=True)
    st.markdown("### 📊 Graph Status")
    gs = s.get("graph_stats", {})
    st.markdown(f"""
    <div style="font-family:var(--font-mono);font-size:0.72rem;color:var(--text-dim);line-height:2">
        <span style="color:var(--accent)">●</span> {gs.get('total_nodes',0)} nodes<br>
        <span style="color:var(--accent2)">●</span> {gs.get('total_edges',0)} edges<br>
        <span style="color:var(--accent3)">●</span> {len(s['sdtm_domains'])} SDTM domains<br>
        <span style="color:var(--success)">●</span> {len(s['chunks'])} chunks indexed<br>
        <span style="color:var(--text-dim)">⏱</span> Built {s.get('build_time','—')}
    </div>
    """, unsafe_allow_html=True)

    # SDTM domain pills
    if s["sdtm_domains"]:
        st.markdown('<div style="margin-top:0.5rem">' +
            "".join(f'<span class="domain-pill">{d}</span>'
                    for d in s["sdtm_domains"]) +
            '</div>', unsafe_allow_html=True)

st.markdown('<div class="sidebar-section"></div>', unsafe_allow_html=True)
st.markdown("""
<div style="font-family:var(--font-mono);font-size:0.62rem;color:var(--text-dim);line-height:1.8">
⚠️ Outputs are <b>assistive</b>.<br>
Review by qualified<br>statistician required for<br>regulated submissions.
</div>
""", unsafe_allow_html=True)
```

# ─────────────────────────────────────────────────────────────────────────────

# BUILD PIPELINE

# ─────────────────────────────────────────────────────────────────────────────

if build_btn:
if not prot_file or not sap_file or not sdtm_files:
st.error(“⚠️  Please upload Protocol PDF, SAP DOCX, and at least one SDTM file.”)
else:
progress_bar = st.progress(0, text=“Initialising…”)
status_box   = st.empty()

```
    steps = [
        (10, "Saving uploaded files to workspace…"),
        (25, "Ingesting Protocol PDF…"),
        (40, "Ingesting SAP DOCX…"),
        (55, "Loading SDTM datasets…"),
        (70, "Parsing Excel spec & shells…"),
        (85, "Building knowledge graph…"),
        (95, "Indexing chunks for retrieval…"),
        (100, "Done."),
    ]

    with st.spinner("Building knowledge graph — this may take a moment…"):
        workdir  = Path(tempfile.mkdtemp(prefix="graphrag_adam_"))
        out_dir  = workdir / "outputs"
        out_dir.mkdir(parents=True, exist_ok=True)

        # Save files
        progress_bar.progress(10, text=steps[0][1])
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

        for pct, msg in steps[1:]:
            progress_bar.progress(pct, text=msg)
            time.sleep(0.05)

        paths = Paths(
            protocol_pdf=up_protocol,
            sap_docx=up_sap,
            sdtm_dir=sdtm_dir,
            sdtm_spec_excel=up_spec,
            shells_docx=up_shells,
            output_dir=out_dir,
        )
        opts = Options(chunk_size=chunk_size, topk=topk)

        kg, chunks, sdtm = build_kg(paths, opts)
        graph_stats = kg.stats()

        # Persist to session
        s["kg_built"]     = True
        s["kg_json"]      = kg.to_json()
        s["chunks"]       = chunks
        s["sdtm_data"]    = sdtm
        s["sdtm_domains"] = list(sdtm.keys())
        s["workdir"]      = str(workdir)
        s["paths"]        = paths
        s["graph_stats"]  = graph_stats
        s["build_time"]   = datetime.now().strftime("%H:%M:%S")
        s["_kg"]          = kg   # keep live object

        # Build summary meta per domain
        try:
            s["sdtm_meta"] = get_domain_summary(sdtm)
        except Exception:
            s["sdtm_meta"] = []

    progress_bar.empty()
    st.success(f"✓  Knowledge graph built — {graph_stats.get('total_nodes',0)} nodes, "
               f"{graph_stats.get('total_edges',0)} edges, "
               f"{len(chunks)} indexed chunks.")
```

# ─────────────────────────────────────────────────────────────────────────────

# METRICS ROW (shown after build)

# ─────────────────────────────────────────────────────────────────────────────

if s[“kg_built”]:
gs   = s[“graph_stats”]
nk   = gs.get(“node_kinds”, {})
et   = gs.get(“edge_types”, {})

```
c1, c2, c3, c4, c5, c6 = st.columns(6)
cards = [
    (c1, gs.get("total_nodes", 0),         "Total Nodes"),
    (c2, gs.get("total_edges", 0),         "Total Edges"),
    (c3, nk.get("adam_var", 0),            "ADaM Vars"),
    (c4, nk.get("sdtm_var", 0),            "SDTM Vars"),
    (c5, nk.get("rule", 0),                "Rules"),
    (c6, len(s["chunks"]),                 "Chunks"),
]
for col, val, label in cards:
    with col:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{val}</div>
            <div class="metric-label">{label}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<div style='margin-bottom:1rem'></div>", unsafe_allow_html=True)
```

# ─────────────────────────────────────────────────────────────────────────────

# MAIN TABS

# ─────────────────────────────────────────────────────────────────────────────

tab_graph, tab_qa, tab_rules, tab_sdtm, tab_codegen, tab_spec, tab_debug = st.tabs([
“⬡ Graph”,
“💬 Ask & Evidence”,
“📋 Rule Library”,
“🗄️ SDTM Explorer”,
“⚙️ Code Generator”,
“📄 Spec Viewer”,
“🔧 Debug”,
])

# ══════════════════════════════════════════════════════════════════════════════

# TAB 1: GRAPH

# ══════════════════════════════════════════════════════════════════════════════

with tab_graph:
if not s[“kg_built”]:
st.info(“Upload files and click **Build Knowledge Graph** to view the graph.”)
else:
ctrl_col, graph_col = st.columns([1, 4])

```
    with ctrl_col:
        st.markdown("**Graph Controls**")

        # Dataset filter
        ds_options = ["ALL"] + sorted({
            n.get("dataset", "") or n.get("adam_ds", "")
            for n in s["kg_json"]["nodes"]
            if n.get("kind") in ("adam_var", "rule")
            and (n.get("dataset") or n.get("adam_ds"))
        })
        ds_filter = st.selectbox("Filter by dataset", ds_options, key="ds_filter")

        # Node type filter
        node_types = sorted({n.get("kind", "") for n in s["kg_json"]["nodes"]})
        sel_types  = st.multiselect("Node types", node_types,
                                    default=node_types, key="node_types")

        st.markdown("---")
        st.markdown("**Legend**")
        legend_items = [
            ("#00d4aa", "ADaM Variable"),
            ("#4a9eff", "SDTM Variable"),
            ("#f0b429", "Doc Chunk"),
            ("#ff7b54", "Rule"),
            ("#8b949e", "Dataset Cluster"),
        ]
        for color, label in legend_items:
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:6px;'
                f'font-size:0.75rem;color:#8b949e;margin-bottom:4px">'
                f'<div style="width:10px;height:10px;border-radius:50%;'
                f'background:{color};flex-shrink:0"></div>{label}</div>',
                unsafe_allow_html=True
            )

        st.markdown("---")
        # Download graph
        ghtml_path = Path(s["workdir"]) / "outputs" / "graph.html"
        if ghtml_path.exists():
            html_str = ghtml_path.read_text(encoding="utf-8")
            st.download_button(
                "⬇ Download graph.html",
                data=html_str.encode("utf-8"),
                file_name="adam_knowledge_graph.html",
                mime="text/html",
            )

        # Download graph JSON
        st.download_button(
            "⬇ Download graph.json",
            data=json.dumps(s["kg_json"], indent=2).encode("utf-8"),
            file_name="adam_knowledge_graph.json",
            mime="application/json",
        )

    with graph_col:
        ghtml_path = Path(s["workdir"]) / "outputs" / "graph.html"
        ghtml_path.parent.mkdir(parents=True, exist_ok=True)
        write_d3_html(s["kg_json"], ghtml_path, embed_data=True)
        html_str = ghtml_path.read_text(encoding="utf-8")

        st.markdown('<div class="graph-container">', unsafe_allow_html=True)
        st.components.v1.html(html_str, height=820, scrolling=False)
        st.markdown('</div>', unsafe_allow_html=True)
```

# ══════════════════════════════════════════════════════════════════════════════

# TAB 2: ASK & EVIDENCE

# ══════════════════════════════════════════════════════════════════════════════

with tab_qa:
qa_left, qa_right = st.columns([3, 2])

```
with qa_left:
    st.markdown("#### Ask a derivation question")

    # Suggested questions
    suggestions = [
        "How do I calculate the primary endpoint for subject 101?",
        "How is AVAL derived for overall survival?",
        "What censoring hierarchy applies to PFS?",
        "How are baseline lab values flagged?",
        "How is TRTEMFL defined for adverse events?",
        "What SDTM variables feed into ADSL population flags?",
        "How is change from baseline calculated for vital signs?",
    ]
    with st.expander("💡 Suggested questions", expanded=False):
        for sug in suggestions:
            if st.button(sug, key=f"sug_{sug[:20]}", use_container_width=True):
                st.session_state["_prefill_q"] = sug

    q = st.text_area(
        "Question",
        value=st.session_state.get("_prefill_q", ""),
        height=100,
        placeholder="e.g. How do I calculate the primary endpoint for subject 101?",
        label_visibility="collapsed",
    )

    col_ask, col_clear = st.columns([3, 1])
    with col_ask:
        ask_btn = st.button("Answer", type="primary", use_container_width=True)
    with col_clear:
        if st.button("Clear", use_container_width=True):
            st.session_state["_prefill_q"] = ""
            st.rerun()

    if ask_btn:
        if not s["kg_built"]:
            st.error("Please build the knowledge graph first.")
        elif not q.strip():
            st.warning("Please enter a question.")
        else:
            with st.spinner("Retrieving evidence and generating derivation…"):
                kg_obj = s.get("_kg") or KnowledgeGraph()
                rag    = GraphRAG(kg_obj, s["chunks"])
                ans    = rag.answer(q, sdtm_data=s["sdtm_data"], topk_chunks=int(topk))
                s["last_answer"] = ans
                # Save to history
                s["qa_history"].insert(0, {
                    "q":       q,
                    "rule_id": ans.get("rule_id", "—"),
                    "var":     ans.get("target_var", "—"),
                    "time":    datetime.now().strftime("%H:%M:%S"),
                })
                if len(s["qa_history"]) > 20:
                    s["qa_history"] = s["qa_history"][:20]

    # Answer display
    if s["last_answer"]:
        ans = s["last_answer"]
        st.markdown("---")

        # Header badges
        tv  = ans.get("target_var", "—")
        rid = ans.get("rule_id", "—")
        ep  = ans.get("endpoint", "—")
        avt = ans.get("all_target_vars", [])

        st.markdown(
            f'<div style="margin-bottom:0.8rem">'
            f'<span class="badge badge-teal">TARGET: {tv}</span>&nbsp;'
            f'<span class="badge badge-blue">RULE: {rid}</span>&nbsp;'
            f'<span class="badge badge-orange">ENDPOINT: {ep or "—"}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

        if len(avt) > 1:
            st.markdown(
                "**All inferred variables:** " +
                " ".join(f'<span class="badge badge-teal">{v}</span>' for v in avt),
                unsafe_allow_html=True
            )

        der = ans.get("derivation", {})

        # Description
        if der.get("description"):
            st.markdown(f"""
            <div style="background:var(--bg2);border:1px solid var(--border);
            border-left:3px solid var(--accent);border-radius:4px;
            padding:0.8rem 1rem;margin:0.8rem 0;font-size:0.85rem;
            color:var(--text-dim)">
            {der['description']}
            </div>
            """, unsafe_allow_html=True)

        # Pseudocode
        if der.get("pseudocode"):
            st.markdown("**Derivation steps:**")
            pseudo_html = '<div style="background:var(--bg2);border:1px solid var(--border);border-radius:4px;padding:0.6rem 0.8rem">'
            for i, step in enumerate(der["pseudocode"]):
                pseudo_html += f"""
                <div class="pseudo-step">
                    <span class="pseudo-num">{i+1:02d}</span>
                    <span class="pseudo-text">{step}</span>
                </div>"""
            pseudo_html += '</div>'
            st.markdown(pseudo_html, unsafe_allow_html=True)

        # SDTM sources
        sources = der.get("sources", [])
        if sources:
            st.markdown("**Source domains & variables:**")
            src_cols = st.columns(min(len(sources), 4))
            for i, src in enumerate(sources):
                with src_cols[i % len(src_cols)]:
                    vars_str = ", ".join(src.get("vars", []))
                    st.markdown(f"""
                    <div style="background:var(--bg2);border:1px solid var(--border);
                    border-radius:4px;padding:0.6rem;font-size:0.75rem">
                    <div style="color:var(--accent2);font-family:var(--font-mono);
                    font-weight:600;margin-bottom:0.3rem">{src.get('domain','')}</div>
                    <div style="color:var(--text-dim);line-height:1.6">{vars_str}</div>
                    </div>
                    """, unsafe_allow_html=True)

        # Graph context
        gc = ans.get("graph_context", {})
        if gc.get("censoring_chain"):
            st.markdown("**Censoring hierarchy:**")
            for item in gc["censoring_chain"]:
                st.markdown(
                    f'`{item["domain"]}.{item["var"]}`  '
                    f'<span style="color:var(--text-dim);font-size:0.75rem">'
                    f'weight={item["weight"]:.2f}</span>',
                    unsafe_allow_html=True
                )

        # Python scaffold
        code = der.get("python_scaffold", "")
        if code:
            with st.expander("**Python scaffold**", expanded=True):
                st.code(code, language="python")
                fname = f"{rid or 'derivation'}_scaffold.py"
                st.download_button(
                    f"⬇ Download {fname}",
                    data=code.encode("utf-8"),
                    file_name=fname,
                    mime="text/plain",
                )

with qa_right:
    st.markdown("#### Evidence & Graph Context")

    if s["last_answer"]:
        ans = s["last_answer"]
        ev  = ans.get("evidence", [])

        if ev:
            st.markdown(f"**Top {len(ev)} retrieval hits**")
            for item in ev:
                score = item.get("score", 0)
                bar_w = min(int(score * 80 + 10), 100)
                bar_c = "#00d4aa" if score > 0.3 else "#4a9eff" if score > 0.1 else "#8b949e"
                st.markdown(f"""
                <div class="evidence-card">
                    <div class="evidence-header">
                        {item.get('doc','').upper()} · {item.get('header','')[:60]}
                        <span class="evidence-score">score={score:.3f}</span>
                    </div>
                    <div style="height:3px;background:var(--bg3);border-radius:2px;margin-bottom:0.5rem">
                        <div style="height:3px;width:{bar_w}%;background:{bar_c};border-radius:2px"></div>
                    </div>
                    <div class="evidence-text">{item.get('text','')[:200]}…</div>
                </div>
                """, unsafe_allow_html=True)

                ents = item.get("entities", {})
                adam_v = ents.get("adam_vars", [])
                sdtm_v = [v for _, v in ents.get("sdtm_vars", [])]
                if adam_v or sdtm_v:
                    mentions = (
                        " ".join(f'<span class="badge badge-teal">{v}</span>' for v in adam_v) +
                        " ".join(f'<span class="badge badge-blue">{v}</span>' for v in sdtm_v[:4])
                    )
                    st.markdown(mentions, unsafe_allow_html=True)

        # Graph context summary
        gc = ans.get("graph_context", {})
        if gc.get("co_occurring_vars"):
            st.markdown("**Co-occurring ADaM variables:**")
            pills = " ".join(
                f'<span class="badge badge-teal">{v}</span>'
                for v in gc["co_occurring_vars"][:12]
            )
            st.markdown(pills, unsafe_allow_html=True)

    # Q&A history
    if s["qa_history"]:
        st.markdown("---")
        st.markdown("**Recent questions**")
        for h in s["qa_history"][:8]:
            st.markdown(f"""
            <div class="history-item">
                <div class="history-q">{h['q'][:80]}{'…' if len(h['q'])>80 else ''}</div>
                <div class="history-meta">
                    <span class="badge badge-teal" style="font-size:0.6rem">{h['var']}</span>&nbsp;
                    <span class="badge badge-orange" style="font-size:0.6rem">{h['rule_id']}</span>&nbsp;
                    {h['time']}
                </div>
            </div>
            """, unsafe_allow_html=True)
```

# ══════════════════════════════════════════════════════════════════════════════

# TAB 3: RULE LIBRARY

# ══════════════════════════════════════════════════════════════════════════════

with tab_rules:
rl_left, rl_right = st.columns([2, 3])

```
with rl_left:
    st.markdown("#### ADaM Rule Library")

    # Filter by class
    classes = sorted({r.get("adam_class", "OTHER") for r in RULES})
    sel_class = st.selectbox("Filter by class", ["ALL"] + classes, key="rule_class_filter")

    filtered_rules = [
        r for r in RULES
        if sel_class == "ALL" or r.get("adam_class") == sel_class
    ]

    for rule in filtered_rules:
        adam_class = rule.get("adam_class", "")
        badge_cls  = {
            "ADTTE": "badge-orange",
            "ADSL":  "badge-teal",
            "BDS":   "badge-blue",
            "ADAE":  "badge-green",
        }.get(adam_class, "badge-blue")

        if st.button(
            f"{rule['id']}  ·  {rule['adam_ds']}",
            key=f"rule_btn_{rule['id']}",
            use_container_width=True,
        ):
            s["selected_rule"] = rule

        # Show preview card
        st.markdown(f"""
        <div class="rule-card" style="margin-top:-0.5rem;border-top:none;border-radius:0 0 6px 6px">
            <span class="badge {badge_cls}">{adam_class}</span>
            <div class="rule-desc">{rule.get('desc','')[:100]}…</div>
        </div>
        """, unsafe_allow_html=True)

with rl_right:
    rule = s.get("selected_rule") or (RULES[0] if RULES else None)
    if rule:
        st.markdown(f"#### Rule detail: `{rule['id']}`")

        # Metadata
        st.markdown(f"""
        <div style="display:flex;gap:0.5rem;margin-bottom:1rem;flex-wrap:wrap">
            <span class="badge badge-teal">Dataset: {rule.get('adam_ds','')}</span>
            <span class="badge badge-blue">Class: {rule.get('adam_class','')}</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background:var(--bg2);border:1px solid var(--border);
        border-left:3px solid var(--accent);border-radius:4px;
        padding:0.8rem;font-size:0.83rem;color:var(--text-dim);margin-bottom:1rem">
        {rule.get('desc','')}
        </div>
        """, unsafe_allow_html=True)

        # Target variables
        tvars = rule.get("target_vars", [])
        if tvars:
            st.markdown("**Target variables:**")
            st.markdown(
                " ".join(f'<span class="badge badge-teal">{v}</span>' for v in tvars),
                unsafe_allow_html=True
            )

        # Source domains
        sources = rule.get("sources", [])
        if sources:
            st.markdown("**Source domains:**")
            src_data = []
            for src in sources:
                for v in src.get("vars", []):
                    src_data.append({"Domain": src["domain"], "Variable": v})
            if src_data:
                st.dataframe(
                    pd.DataFrame(src_data),
                    use_container_width=True,
                    hide_index=True,
                    height=160,
                )

        # Pseudocode
        st.markdown("**Derivation pseudocode:**")
        pseudo_html = '<div style="background:var(--bg2);border:1px solid var(--border);border-radius:4px;padding:0.6rem 0.8rem">'
        for i, step in enumerate(rule.get("pseudo", [])):
            pseudo_html += f"""
            <div class="pseudo-step">
                <span class="pseudo-num">{i+1:02d}</span>
                <span class="pseudo-text">{step}</span>
            </div>"""
        pseudo_html += '</div>'
        st.markdown(pseudo_html, unsafe_allow_html=True)

        # Censoring hierarchy
        if rule.get("cnsr_hierarchy"):
            st.markdown("**Censoring hierarchy:**")
            cnsr_df = pd.DataFrame(rule["cnsr_hierarchy"])
            st.dataframe(cnsr_df, use_container_width=True, hide_index=True, height=160)

        # Generate scaffold for this rule
        st.markdown("---")
        if st.button("⚙️  Generate Python scaffold for this rule",
                     key="gen_scaffold_rule", use_container_width=True):
            mapping = suggest_mapping_and_derivation(rule, "AVAL")
            code    = mapping.get("python_scaffold", "")
            st.code(code, language="python")
            st.download_button(
                f"⬇ Download {rule['id']}_scaffold.py",
                data=code.encode("utf-8"),
                file_name=f"{rule['id']}_scaffold.py",
            )
```

# ══════════════════════════════════════════════════════════════════════════════

# TAB 4: SDTM EXPLORER

# ══════════════════════════════════════════════════════════════════════════════

with tab_sdtm:
if not s[“sdtm_domains”]:
st.info(“Build the knowledge graph to explore SDTM domains.”)
else:
sdtm_top, sdtm_bottom = st.columns([1, 3])

```
    with sdtm_top:
        st.markdown("#### Domains")
        sel_domain = st.selectbox(
            "Select domain",
            s["sdtm_domains"],
            key="sdtm_domain_select",
            label_visibility="collapsed",
        )

    st.markdown("---")
    domain_entry = s["sdtm_data"].get(sel_domain, {})
    domain_meta  = domain_entry.get("meta", {})
    domain_df    = domain_entry.get("df")

    # Domain summary cards
    dc1, dc2, dc3, dc4, dc5 = st.columns(5)
    for col, val, label in [
        (dc1, domain_meta.get("n_rows", 0),                "Rows"),
        (dc2, domain_meta.get("n_cols", 0),                "Variables"),
        (dc3, len(domain_meta.get("date_vars", [])),       "Date Vars"),
        (dc4, len(domain_meta.get("codelist_vars", {})),   "Codelist Vars"),
        (dc5, domain_meta.get("sdtm_class", "—"),          "Class"),
    ]:
        with col:
            st.markdown(f"""
            <div class="metric-card" style="padding:0.7rem">
                <div class="metric-value" style="font-size:1.3rem">{val}</div>
                <div class="metric-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)

    tabs_sdtm = st.tabs(["Variables", "Data Preview", "Codelist Values", "Date Variables"])

    with tabs_sdtm[0]:
        var_profiles = domain_meta.get("variables", [])
        if var_profiles:
            var_df = pd.DataFrame([{
                "Variable":  v["varname"],
                "Label":     v.get("label", ""),
                "Type":      v.get("sas_type", ""),
                "Is Date":   "✓" if v.get("is_date") else "",
                "Null %":    f"{v.get('null_rate',0)*100:.1f}%",
                "Unique":    v.get("n_unique", 0),
                "Sample":    ", ".join(v.get("sample_values", [])[:3]),
            } for v in var_profiles])
            st.dataframe(var_df, use_container_width=True,
                         hide_index=True, height=420)

    with tabs_sdtm[1]:
        if domain_df is not None and not domain_df.empty:
            n_preview = st.slider("Rows to preview", 5, 50, 10, key="sdtm_preview_n")
            st.dataframe(
                domain_df.head(n_preview),
                use_container_width=True,
                hide_index=True,
                height=400,
            )
            st.download_button(
                f"⬇ Download {sel_domain}.csv",
                data=domain_df.to_csv(index=False).encode("utf-8"),
                file_name=f"{sel_domain}.csv",
            )

    with tabs_sdtm[2]:
        codelist_vars = domain_meta.get("codelist_vars", {})
        if codelist_vars:
            sel_cl_var = st.selectbox("Select variable",
                                      list(codelist_vars.keys()),
                                      key="sdtm_cl_var")
            if sel_cl_var:
                vals = codelist_vars[sel_cl_var]
                st.markdown(f"**{sel_cl_var}** — {len(vals)} unique values")
                cl_df = pd.DataFrame({"Value": vals})
                if domain_df is not None:
                    counts = domain_df[sel_cl_var].value_counts().reset_index()
                    counts.columns = ["Value", "Count"]
                    cl_df = cl_df.merge(counts, on="Value", how="left").fillna(0)
                    cl_df["Count"] = cl_df["Count"].astype(int)
                st.dataframe(cl_df, use_container_width=True,
                             hide_index=True, height=300)
        else:
            st.info("No codelist variables detected in this domain.")

    with tabs_sdtm[3]:
        date_vars = domain_meta.get("date_vars", [])
        if date_vars and domain_df is not None:
            st.markdown(f"**{len(date_vars)} ISO 8601 date variables detected:**")
            for dv in date_vars:
                if dv in domain_df.columns:
                    sample_dates = domain_df[dv].dropna().head(5).tolist()
                    st.markdown(
                        f'`{dv}` &nbsp; '
                        + " · ".join(f'<code style="font-size:0.72rem">{d}</code>'
                                     for d in sample_dates),
                        unsafe_allow_html=True
                    )
        else:
            st.info("No ISO 8601 date variables detected.")
```

# ══════════════════════════════════════════════════════════════════════════════

# TAB 5: CODE GENERATOR

# ══════════════════════════════════════════════════════════════════════════════

with tab_codegen:
cg_left, cg_right = st.columns([1, 2])

```
with cg_left:
    st.markdown("#### Generate ADaM Scaffold")
    st.markdown('<div style="font-size:0.8rem;color:var(--text-dim);margin-bottom:1rem">Select a dataset and target variable to generate a Python derivation scaffold.</div>', unsafe_allow_html=True)

    ds_opts = sorted({r["adam_ds"] for r in RULES})
    sel_ds  = st.selectbox("ADaM Dataset", ds_opts, key="cg_ds")

    rules_for_ds = get_rules_by_dataset(sel_ds)
    rule_opts    = [r["id"] for r in rules_for_ds]
    sel_rule_id  = st.selectbox("Rule", rule_opts, key="cg_rule") if rule_opts else None

    vars_for_ds  = get_vars_for_dataset(sel_ds)
    sel_var      = st.selectbox("Target Variable", vars_for_ds or ["AVAL"],
                                key="cg_var")

    lang_opt = st.radio("Output language", ["Python (pandas)", "SAS (stub)"],
                        horizontal=True, key="cg_lang")

    st.markdown("---")
    st.markdown("**Custom study parameters**")
    study_id = st.text_input("STUDYID", value="STUDY001", key="cg_studyid")
    sdtm_path_hint = st.text_input("SDTM data path", value="./sdtm/", key="cg_path")

    gen_btn = st.button("⚙️  Generate scaffold", type="primary",
                        use_container_width=True, key="cg_gen_btn")

with cg_right:
    st.markdown("#### Generated Code")

    if gen_btn and sel_rule_id:
        rule    = next((r for r in RULES if r["id"] == sel_rule_id), None)
        mapping = suggest_mapping_and_derivation(rule, sel_var, s.get("sdtm_data"))
        code    = mapping.get("python_scaffold", "# No scaffold available")

        # Inject study-specific parameters
        code = code.replace("STUDY001", study_id)
        code = code.replace("./sdtm/", sdtm_path_hint)

        st.session_state["_last_gen_code"]    = code
        st.session_state["_last_gen_rule_id"] = sel_rule_id

    code_to_show = st.session_state.get("_last_gen_code", "")
    rule_id_show = st.session_state.get("_last_gen_rule_id", "")

    if code_to_show:
        st.code(code_to_show, language="python")
        dl_col1, dl_col2 = st.columns(2)
        with dl_col1:
            st.download_button(
                "⬇ Download .py",
                data=code_to_show.encode("utf-8"),
                file_name=f"{rule_id_show or sel_ds}_scaffold.py",
                use_container_width=True,
            )
        with dl_col2:
            # Export as markdown doc
            md_content = f"""# {rule_id_show} — Derivation Scaffold
```

Generated: {datetime.now().strftime(”%Y-%m-%d %H:%M”)}

## Pseudocode

“””
if sel_rule_id:
rule = next((r for r in RULES if r[“id”] == sel_rule_id), None)
if rule:
for step in rule.get(“pseudo”, []):
md_content += f”- {step}\n”
md_content += f”\n## Python Code\n\n`python\n{code_to_show}\n`\n”
st.download_button(
“⬇ Download .md”,
data=md_content.encode(“utf-8”),
file_name=f”{rule_id_show or sel_ds}_scaffold.md”,
use_container_width=True,
)
else:
st.markdown(”””
<div style="background:var(--bg2);border:1px dashed var(--border);
border-radius:6px;padding:3rem;text-align:center;
color:var(--text-dim);font-family:var(--font-mono);font-size:0.8rem">
Select a dataset, rule, and variable then click Generate
</div>
“””, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════

# TAB 6: SPEC VIEWER

# ══════════════════════════════════════════════════════════════════════════════

with tab_spec:
if not s[“kg_built”]:
st.info(“Build the knowledge graph to explore the specification.”)
else:
st.markdown(”#### Variable Reference”)

```
    # Build a combined variable table from rules
    all_vars = list_all_target_vars()
    var_rows = []
    for rule in RULES:
        for var in rule.get("target_vars", []):
            for src in rule.get("sources", []):
                for sv in src.get("vars", []):
                    var_rows.append({
                        "ADaM Variable": var,
                        "Dataset":       rule["adam_ds"],
                        "Class":         rule.get("adam_class", ""),
                        "Source Domain": src["domain"],
                        "Source Var":    sv,
                        "Rule":          rule["id"],
                    })

    if var_rows:
        var_table = pd.DataFrame(var_rows).drop_duplicates()

        # Filter controls
        spec_c1, spec_c2, spec_c3 = st.columns(3)
        with spec_c1:
            ds_filter_spec = st.multiselect(
                "Dataset", sorted(var_table["Dataset"].unique()),
                default=sorted(var_table["Dataset"].unique()),
                key="spec_ds_filter"
            )
        with spec_c2:
            class_filter_spec = st.multiselect(
                "Class", sorted(var_table["Class"].unique()),
                default=sorted(var_table["Class"].unique()),
                key="spec_class_filter"
            )
        with spec_c3:
            src_filter = st.multiselect(
                "Source Domain", sorted(var_table["Source Domain"].unique()),
                key="spec_src_filter"
            )

        filtered = var_table[
            var_table["Dataset"].isin(ds_filter_spec) &
            var_table["Class"].isin(class_filter_spec)
        ]
        if src_filter:
            filtered = filtered[filtered["Source Domain"].isin(src_filter)]

        st.markdown(f"**{len(filtered)} mappings** ({filtered['ADaM Variable'].nunique()} unique ADaM vars)")
        st.dataframe(filtered, use_container_width=True,
                     hide_index=True, height=500)

        # Export
        st.download_button(
            "⬇ Export variable mapping CSV",
            data=filtered.to_csv(index=False).encode("utf-8"),
            file_name="adam_variable_mapping.csv",
            mime="text/csv",
        )
```

# ══════════════════════════════════════════════════════════════════════════════

# TAB 7: DEBUG

# ══════════════════════════════════════════════════════════════════════════════

with tab_debug:
st.markdown(”#### Session & Graph Debug”)

```
d1, d2 = st.columns(2)

with d1:
    st.markdown("**Session state**")
    safe_state = {
        k: v for k, v in st.session_state.items()
        if k not in ("_kg", "kg_json", "chunks", "sdtm_data", "last_answer")
        and not k.startswith("_")
    }
    st.json(safe_state)

with d2:
    st.markdown("**Graph statistics**")
    if s.get("graph_stats"):
        st.json(s["graph_stats"])

    if s["kg_built"]:
        st.markdown("**SDTM domain summary**")
        if s.get("sdtm_meta"):
            st.dataframe(
                pd.DataFrame(s["sdtm_meta"]),
                use_container_width=True,
                hide_index=True,
            )

if s.get("workdir"):
    st.markdown(f"**Workspace:** `{s['workdir']}`")

if s.get("qa_history"):
    st.markdown("**Q&A history (full)**")
    st.dataframe(
        pd.DataFrame(s["qa_history"]),
        use_container_width=True,
        hide_index=True,
    )

if s["kg_built"]:
    st.markdown("---")
    st.markdown("**Graph JSON (first 50 nodes)**")
    preview = {
        "nodes": s["kg_json"]["nodes"][:50],
        "links": s["kg_json"]["links"][:50],
    }
    st.json(preview)