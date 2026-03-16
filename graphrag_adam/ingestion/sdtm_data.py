
from pathlib import Path
from typing import Dict, Any
import pandas as pd


def load_sdtm_dir(sdtm_dir: Path) -> Dict[str, Any]:
    """
    Returns {domain_name: {"df": DataFrame, "meta": {"n_rows":..., "columns":[...]}}}
    Supports .sas7bdat and .xpt
    """
    result = {}
    sdtm_dir = Path(sdtm_dir)
    for p in sdtm_dir.glob("*"):
        if p.suffix.lower() in [".sas7bdat", ".xpt"]:
            try:
                fmt = "sas7bdat" if p.suffix.lower()==".sas7bdat" else "xport"
                df = pd.read_sas(str(p), format=fmt, encoding="utf-8")
                # pandas returns DataFrame
                dom = p.stem.upper()
                result[dom] = {
                    "df": df,
                    "meta": {
                        "n_rows": len(df),
                        "columns": [str(c).upper() for c in df.columns]
                    }
                }
            except Exception as e:
                print(f"[WARN] Could not read {p.name}: {e}")
    return result
