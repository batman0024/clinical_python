
from typing import Dict, Any
import pandas as pd


def load_sdtm_spec(path) -> Dict[str, Any]:
    """
    Expected sheets: Variables (DOMAIN, VARNAME, LABEL, TYPE, ORIGIN, Codelist)
    This is flexible—tries to guess common column names.
    """
    xls = pd.ExcelFile(path, engine="openpyxl")
    out = {"variables": []}
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet, engine="openpyxl")
        cols = {str(c).lower().strip(): c for c in df.columns}
        # heuristic mapping
        candidates = {"domain", "varname", "variable", "label", "type", "origin", "codelist", "role"}
        if len(set(cols.keys()) & candidates) >= 2:
            for _, r in df.iterrows():
                varname = str(r.get(cols.get("varname", cols.get("variable", "")), "")).upper()
                out["variables"].append({
                    "domain": str(r.get(cols.get("domain",""), "")).upper(),
                    "varname": varname,
                    "label": str(r.get(cols.get("label",""), "")),
                    "type": str(r.get(cols.get("type",""), "")),
                    "origin": str(r.get(cols.get("origin",""), "")),
                    "codelist": str(r.get(cols.get("codelist",""), "")),
                    "role": str(r.get(cols.get("role",""), "")),
                    "sheet": sheet
                })
    return out
