
import re
from typing import List, Dict
from PyPDF2 import PdfReader


def read_pdf_text(path) -> str:
    reader = PdfReader(str(path))
    texts = []
    for page in reader.pages:
        try:
            txt = page.extract_text() or ""
        except Exception:
            txt = ""
        texts.append(txt)
    return "\n".join(texts)


def section_split(text: str) -> List[Dict]:
    # naive sectioning by lines with numbers/headers
    lines = text.splitlines()
    chunks, buf, header = [], [], "Protocol"
    for ln in lines:
        if re.match(r"^\s*(\d+(\.\d+)*)\s+\w+", ln):
            if buf:
                chunks.append({"header": header, "text": "\n".join(buf)})
                buf = []
            header = ln.strip()
        buf.append(ln)
    if buf:
        chunks.append({"header": header, "text": "\n".join(buf)})
    return chunks


def ingest_protocol_pdf(path, chunk_size=1500, overlap=200) -> List[Dict]:
    text = read_pdf_text(path)
    sections = section_split(text)
    # re-chunk long sections
    out = []
    step = max(1, chunk_size - overlap)
    for s in sections:
        t = s["text"]
        for i in range(0, max(1, len(t)), step):
            out.append({
                "doc": "protocol",
                "header": s["header"],
                "text": t[i:i+chunk_size],
                "span": (i, i+chunk_size)
            })
    return out
