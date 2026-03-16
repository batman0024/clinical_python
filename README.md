
# GraphRAG ADaM — Spec→Code Mapping Toolkit (with Streamlit UI)

This package builds a GraphRAG-style knowledge graph from **Protocol (PDF)**, **SAP (DOCX)**, **SDTM data (.sas7bdat/.xpt)** and optional **SDTM specification (Excel)** and **TLF shells (DOCX)**. It then:

- Suggests **ADaM derivation mappings** for common endpoints (OS, PFS, flags, etc.)
- Answers questions like *"How do I calculate the primary endpoint for subject 101?"*
- Provides an **interactive visual knowledge graph** (D3) showing connections between **ADaM variables ⇄ SAP/Protocol chunks ⇄ SDTM variables**.
- Comes with a **Streamlit app** to run the full workflow.

> ⚠️ Outputs are **assistive**. Review by a qualified statistician/programmer is required for regulated submissions.

---

## Quick start

### 1) Create a virtual environment & install
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
# optional: install package in dev mode
pip install -e .
```

### 2) Run the Streamlit app
```bash
streamlit run app/streamlit_app.py
```

### 3) Use the UI
- Upload **Protocol (PDF)** and **SAP (DOCX)**.
- Upload SDTM files (**.sas7bdat** and/or **.xpt**). You can select multiple files.
- (Optional) Upload **SDTM spec (Excel)** and **Shells (DOCX)**.
- Click **Build Knowledge Graph** to parse and index.
- Ask questions (e.g., *"How do I calculate the primary endpoint?"*), view derivation rule suggestions and **download Python scaffold**.
- Explore the **interactive graph**.

---

## Command line (optional)
```bash
graphrag-adam   --protocol examples/data/protocol.pdf   --sap examples/data/sap.docx   --sdtm-dir examples/data/sdtm   --spec examples/data/sdtm_spec.xlsx   --shells examples/data/shells.docx   --outdir outputs   --visualize   --ask "How do I calculate the primary endpoint for subject 101?"
```

Outputs:
- `outputs/graph.json` — Graph data
- `outputs/graph.html` — Interactive D3 graph
- `outputs/answer.json` — RAG answer with derivation & evidence

---

## Notes
- **SAP/Protocol DOC**: please convert `.doc` → `.docx` for reliable parsing.
- **SDTM reading**: uses `pandas.read_sas` (via pyreadstat). Ensure files are valid and not password-protected.
- Extend the rule library in `graphrag_adam/mapping/rules.py` for your study specifics.
- Add aliases in `graphrag_adam/mapping/synonyms.py`.

