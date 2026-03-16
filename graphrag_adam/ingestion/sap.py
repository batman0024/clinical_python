
from typing import List, Dict
from docx import Document


def read_docx_text(path) -> str:
    doc = Document(str(path))
    paras = [p.text for p in doc.paragraphs]
    return "\n".join(paras)


def ingest_sap_docx(path, chunk_size=1500, overlap=200) -> List[Dict]:
    text = read_docx_text(path)
    out = []
    step = max(1, chunk_size - overlap)
    for i in range(0, max(1, len(text)), step):
        out.append({
            "doc": "sap",
            "header": "SAP Section",
            "text": text[i:i+chunk_size],
            "span": (i, i+chunk_size)
        })
    return out
