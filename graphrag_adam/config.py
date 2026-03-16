
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List

@dataclass
class Paths:
    protocol_pdf: Path
    sap_docx: Path
    sdtm_dir: Path                 # dir with .sas7bdat/.xpt
    sdtm_spec_excel: Optional[Path] = None
    shells_docx: Optional[Path] = None
    output_dir: Path = Path("outputs")

@dataclass
class Options:
    chunk_size: int = 1500                    # characters per chunk
    chunk_overlap: int = 200
    max_neighbors: int = 30
    use_pyvis: bool = False                   # optional viz
    d3_embed_data: bool = True                # embed graph json into HTML
    stopwords: Optional[List[str]] = None
