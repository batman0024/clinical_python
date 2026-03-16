
from typing import List, Dict
from .patterns import TOKEN

def tokenize(text: str):
    return [t.lower() for t in TOKEN.findall(text)]

def make_doc_chunks(protocol_chunks, sap_chunks):
    return protocol_chunks + sap_chunks
