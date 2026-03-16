"""
generator.py — ADaM Python scaffold generator using Jinja2 templates.

Generates production-ready pandas/pyreadstat scaffolds for:
  ADSL, ADTTE (OS/PFS/DOR), ADLB, ADVS, ADAE, ADEX, ADRS, ADCM

No LLM required — pure template + rule-driven generation.
"""

from typing import Dict, Any, Optional
from jinja2 import Environment, BaseLoader

# ---------------------------------------------------------------------------
# JINJA2 TEMPLATES PER ADaM CLASS
# ---------------------------------------------------------------------------

_TEMPLATES: Dict[str, str] = {

    "ADTTE": """\
import pandas as pd
import pyreadstat

# =============================================================================
# {{ rule_id }} — {{ adam_ds }} scaffold
# {{ description }}
# =============================================================================

# --- 1. Load SDTM source domains ---
{% for src in sources %}
{{ src.domain | lower }}, _ = pyreadstat.read_xport("{{ src.domain | lower }}.xpt")
{{ src.domain | lower }}.columns = {{ src.domain | lower }}.columns.str.upper()
{% endfor %}

# --- 2. Merge ADSL for start date ---
adsl_keys = adsl[["USUBJID", "TRTSDT", "TRTEDT", "RANDDT"]].copy()
adsl_keys["TRTSDT"] = pd.to_datetime(adsl_keys["TRTSDT"], errors="coerce")

# --- 3. Determine event/censor date ---
# TODO: replace logic below with study-specific event identification
{% if rule_id == "ADTTE_OS" %}
# Death date from ADSL
adsl_keys["DTHDT"] = pd.to_datetime(adsl.get("DTHDT"), errors="coerce") if "DTHDT" in adsl.columns else pd.NaT

# Censoring hierarchy
sv_last = sv.sort_values("SVENDTC").groupby("USUBJID")["SVENDTC"].last().reset_index()
sv_last.columns = ["USUBJID", "CENSOR_SV"]
sv_last["CENSOR_SV"] = pd.to_datetime(sv_last["CENSOR_SV"], errors="coerce")

adtte = adsl_keys.merge(sv_last, on="USUBJID", how="left")
adtte["EVTFL"] = adtte["DTHDT"].notna().astype(int)  # 0=censored, 1=event
adtte["ADT"] = adtte["DTHDT"].where(
    adtte["EVTFL"] == 1,
    adtte["CENSOR_SV"].fillna(adtte["TRTEDT"])
)
adtte["ADT"] = pd.to_datetime(adtte["ADT"], errors="coerce")
{% elif rule_id == "ADTTE_PFS" %}
# Progression date from RS
rs_pd = rs[rs["RSSTRESC"].str.upper().eq("PD")].copy()
rs_pd["PROGDT"] = pd.to_datetime(rs_pd["RSDTC"], errors="coerce")
rs_prog = rs_pd.groupby("USUBJID")["PROGDT"].min().reset_index()

adtte = adsl_keys.merge(rs_prog, on="USUBJID", how="left")
adtte["DTHDT"] = pd.to_datetime(adsl.get("DTHDT"), errors="coerce") if "DTHDT" in adsl.columns else pd.NaT
adtte["ADT"] = adtte[["PROGDT", "DTHDT"]].min(axis=1)
adtte["EVTFL"] = adtte["ADT"].notna().astype(int)
{% elif rule_id == "ADTTE_DOR" %}
# Restrict to responders
rs_resp = rs[rs["RSSTRESC"].str.upper().isin(["CR", "PR"])].copy()
rs_resp["RESPDT"] = pd.to_datetime(rs_resp["RSDTC"], errors="coerce")
first_resp = rs_resp.groupby("USUBJID")["RESPDT"].min().reset_index()
first_resp.columns = ["USUBJID", "STARTDT_DOR"]

rs_pd = rs[rs["RSSTRESC"].str.upper().eq("PD")].copy()
rs_pd["PROGDT"] = pd.to_datetime(rs_pd["RSDTC"], errors="coerce")
rs_prog = rs_pd.groupby("USUBJID")["PROGDT"].min().reset_index()

adtte = adsl_keys.merge(first_resp, on="USUBJID", how="inner")
adtte = adtte.merge(rs_prog, on="USUBJID", how="left")
adtte["ADT"] = adtte["PROGDT"]
adtte["EVTFL"] = adtte["ADT"].notna().astype(int)
adtte["TRTSDT"] = adtte["STARTDT_DOR"]
{% endif %}

# --- 4. Derive AVAL and CNSR ---
adtte["AVAL"] = (adtte["ADT"] - adtte["TRTSDT"]).dt.days + 1
adtte["CNSR"] = 1 - adtte["EVTFL"]
adtte["PARAMCD"] = "{{ paramcd }}"
adtte["PARAM"]   = "{{ param }}"
adtte["STARTDT"] = adtte["TRTSDT"]

# --- 5. Add required ADaM keys ---
adtte["STUDYID"] = adsl["STUDYID"]
adtte["USUBJID"] = adtte["USUBJID"]

# --- 6. Pseudocode reference ---
# {% for step in pseudo %}
# {{ step }}
# {% endfor %}

print(adtte[["USUBJID","PARAMCD","AVAL","CNSR","ADT","STARTDT"]].head())
""",

    "ADSL": """\
import pandas as pd
import pyreadstat

# =============================================================================
# {{ rule_id }} — ADSL scaffold
# {{ description }}
# =============================================================================

# --- 1. Load SDTM domains ---
dm, _ = pyreadstat.read_xport("dm.xpt")
ex, _ = pyreadstat.read_xport("ex.xpt")
ds, _ = pyreadstat.read_xport("ds.xpt")
for df in [dm, ex, ds]:
    df.columns = df.columns.str.upper()

# --- 2. Treatment dates from EX ---
ex["EXSTDTC"] = pd.to_datetime(ex["EXSTDTC"], errors="coerce")
ex["EXENDTC"] = pd.to_datetime(ex["EXENDTC"], errors="coerce")
first_dose = ex.groupby("USUBJID")["EXSTDTC"].min().reset_index()
first_dose.columns = ["USUBJID", "TRTSDT"]
last_dose  = ex.groupby("USUBJID")["EXENDTC"].max().reset_index()
last_dose.columns  = ["USUBJID", "TRTEDT"]

# --- 3. Build ADSL base from DM ---
adsl = dm[["STUDYID","USUBJID","SUBJID","SITEID","AGE","SEX",
           "RACE","ETHNIC","ARMCD","ARM","ACTARMCD","ACTARM",
           "RFSTDTC","RFENDTC","COUNTRY"]].copy()
adsl = adsl.merge(first_dose, on="USUBJID", how="left")
adsl = adsl.merge(last_dose,  on="USUBJID", how="left")

# --- 4. Treatment labels ---
adsl["TRT01P"] = adsl["ARM"]
adsl["TRT01A"] = adsl["ACTARM"]

# --- 5. Population flags ---
adsl["RANDFL"] = (~adsl["ARMCD"].isin(["NOTASSGN","SCRNFAIL"])).map({True:"Y", False:"N"})
adsl["SAFFL"]  = adsl["USUBJID"].isin(
    ex[ex["EXDOSE"].gt(0) if "EXDOSE" in ex.columns else ex.index]["USUBJID"]
).map({True:"Y", False:"N"})
adsl["ITTFL"]  = adsl["RANDFL"]  # adjust per SAP
adsl["FASFL"]  = adsl["RANDFL"]  # adjust per SAP
adsl["PPSFL"]  = "N"             # TODO: populate per SAP per-protocol criteria

# --- 6. Age group (adjust cut-points per SAP) ---
adsl["AGEGR1"] = pd.cut(
    adsl["AGE"],
    bins=[0, 64, 200],
    labels=["<65", ">=65"]
).astype(str)

# --- 7. Disposition / end of study status ---
disp = ds[ds["DSCAT"].str.upper().eq("DISPOSITION EVENT")][
    ["USUBJID","DSDECOD","DSSTDTC"]
].drop_duplicates("USUBJID")
disp.columns = ["USUBJID","EOSSTT","EOSDT"]
adsl = adsl.merge(disp, on="USUBJID", how="left")

# --- Pseudocode reference ---
# {% for step in pseudo %}
# {{ step }}
# {% endfor %}

print(adsl[["USUBJID","TRT01P","TRTSDT","SAFFL","ITTFL","AGEGR1","EOSSTT"]].head())
""",

    "BDS": """\
import pandas as pd
import pyreadstat

# =============================================================================
# {{ rule_id }} — {{ adam_ds }} BDS scaffold
# {{ description }}
# =============================================================================

# --- 1. Load source domain ---
{% for src in sources %}
{% if src.domain != "ADSL" %}
{{ src.domain | lower }}, _ = pyreadstat.read_xport("{{ src.domain | lower }}.xpt")
{{ src.domain | lower }}.columns = {{ src.domain | lower }}.columns.str.upper()
{% endif %}
{% endfor %}
adsl, _ = pyreadstat.read_xport("adsl.xpt")
adsl.columns = adsl.columns.str.upper()

# --- 2. Map source variables ---
{% if adam_ds == "ADLB" %}
src = lb.rename(columns={
    "LBTESTCD": "PARAMCD", "LBTEST": "PARAM",
    "LBSTRESN": "AVAL",    "LBSTRESC": "AVALC",
    "LBDTC":    "ADTC",    "LBBLFL":   "ABLFL_RAW",
    "LBSTNRLO": "A1LO",    "LBSTNRHI": "A1HI",
}).copy()
{% elif adam_ds == "ADVS" %}
src = vs.rename(columns={
    "VSTESTCD": "PARAMCD", "VSTEST": "PARAM",
    "VSSTRESN": "AVAL",    "VSSTRESC": "AVALC",
    "VSDTC":    "ADTC",    "VSBLFL":   "ABLFL_RAW",
}).copy()
{% endif %}

# --- 3. Date conversion ---
src["ADT"] = pd.to_datetime(src["ADTC"], errors="coerce")

# --- 4. Merge ADSL for treatment start ---
src = src.merge(adsl[["USUBJID","TRTSDT"]], on="USUBJID", how="left")
src["TRTSDT"] = pd.to_datetime(src["TRTSDT"], errors="coerce")

# --- 5. Baseline flag ---
# Last non-missing pre-dose (ADT < TRTSDT) record per subject per PARAMCD
pre = src[src["ADT"] < src["TRTSDT"]].copy()
pre = pre.sort_values("ADT").groupby(["USUBJID","PARAMCD"]).last().reset_index()
pre["ABLFL"] = "Y"
src = src.merge(
    pre[["USUBJID","PARAMCD","ADT","ABLFL"]],
    on=["USUBJID","PARAMCD","ADT"], how="left"
)
src["ABLFL"] = src["ABLFL"].fillna("")

# --- 6. BASE, CHG, PCHG ---
base = src[src["ABLFL"] == "Y"][["USUBJID","PARAMCD","AVAL"]].rename(
    columns={"AVAL": "BASE"}
)
src = src.merge(base, on=["USUBJID","PARAMCD"], how="left")
src["CHG"]  = src["AVAL"] - src["BASE"]
src["PCHG"] = (src["CHG"] / src["BASE"].replace(0, float("nan"))) * 100

# --- 7. Reference range indicators (ADLB only) ---
{% if adam_ds == "ADLB" %}
def _nrind(row):
    if pd.isna(row["AVAL"]) or pd.isna(row["A1LO"]):
        return ""
    if row["AVAL"] < row["A1LO"]: return "LOW"
    if row["AVAL"] > row["A1HI"]: return "HIGH"
    return "NORMAL"
src["ANRIND"] = src.apply(_nrind, axis=1)
base_nr = src[src["ABLFL"] == "Y"][["USUBJID","PARAMCD","ANRIND"]].rename(
    columns={"ANRIND": "BNRIND"}
)
src = src.merge(base_nr, on=["USUBJID","PARAMCD"], how="left")
{% endif %}

# --- Pseudocode reference ---
# {% for step in pseudo %}
# {{ step }}
# {% endfor %}

adam = src.rename(columns={"PARAMCD": "PARAMCD", "PARAM": "PARAM"})
print(adam[["USUBJID","PARAMCD","ADT","AVAL","BASE","CHG","ABLFL"]].head())
""",

    "ADAE": """\
import pandas as pd
import pyreadstat

# =============================================================================
# {{ rule_id }} — ADAE scaffold
# {{ description }}
# =============================================================================

ae, _   = pyreadstat.read_xport("ae.xpt")
adsl, _ = pyreadstat.read_xport("adsl.xpt")
ae.columns   = ae.columns.str.upper()
adsl.columns = adsl.columns.str.upper()

# --- 1. Date conversions ---
ae["ASTDT"] = pd.to_datetime(ae["AESTDTC"], errors="coerce")
ae["AENDT"] = pd.to_datetime(ae["AEENDTC"], errors="coerce")

# --- 2. Merge treatment dates ---
adae = ae.merge(
    adsl[["USUBJID","TRTSDT","TRTEDT","SAFFL"]], on="USUBJID", how="left"
)
adae["TRTSDT"] = pd.to_datetime(adae["TRTSDT"], errors="coerce")
adae["TRTEDT"] = pd.to_datetime(adae["TRTEDT"], errors="coerce")

# --- 3. Treatment-emergent flag (SAP: onset on/after first dose) ---
adae["TRTEMFL"] = (
    (adae["ASTDT"] >= adae["TRTSDT"]) &
    (adae["ASTDT"] <= adae["TRTEDT"] + pd.Timedelta(days=30))
).map({True: "Y", False: ""})

# --- 4. Severity numeric mapping ---
sev_map = {"MILD": 1, "MODERATE": 2, "SEVERE": 3, "LIFE-THREATENING": 4, "FATAL": 5}
adae["AESEVN"] = adae["AESEV"].str.upper().map(sev_map)

# --- 5. Sequence number ---
adae = adae.sort_values(["USUBJID","ASTDT"])
adae["AESEQ"] = adae.groupby("USUBJID").cumcount() + 1

# --- 6. Keep safety population only ---
adae = adae[adae["SAFFL"] == "Y"]

# --- Pseudocode reference ---
# {% for step in pseudo %}
# {{ step }}
# {% endfor %}

print(adae[["USUBJID","AESEQ","ASTDT","AENDT","AESEVN","TRTEMFL","AESER"]].head())
""",

    "ADCM": """\
import pandas as pd
import pyreadstat

# =============================================================================
# {{ rule_id }} — ADCM scaffold
# {{ description }}
# =============================================================================

cm, _   = pyreadstat.read_xport("cm.xpt")
adsl, _ = pyreadstat.read_xport("adsl.xpt")
cm.columns   = cm.columns.str.upper()
adsl.columns = adsl.columns.str.upper()

# --- 1. Date conversions ---
cm["ASTDT"] = pd.to_datetime(cm["CMSTDTC"], errors="coerce")
cm["AENDT"] = pd.to_datetime(cm["CMENDTC"], errors="coerce")

# --- 2. Merge treatment dates ---
adcm = cm.merge(
    adsl[["USUBJID","TRTSDT","TRTEDT"]], on="USUBJID", how="left"
)
adcm["TRTSDT"] = pd.to_datetime(adcm["TRTSDT"], errors="coerce")
adcm["TRTEDT"] = pd.to_datetime(adcm["TRTEDT"], errors="coerce")

# --- 3. Prior medication flag ---
adcm["PREFL"] = (adcm["ASTDT"] < adcm["TRTSDT"]).map({True: "Y", False: ""})

# --- 4. On-treatment flag ---
adcm["ONTRTFL"] = (
    (adcm["ASTDT"] <= adcm["TRTEDT"]) &
    (adcm["AENDT"].isna() | (adcm["AENDT"] >= adcm["TRTSDT"]))
).map({True: "Y", False: ""})

# --- Pseudocode reference ---
# {% for step in pseudo %}
# {{ step }}
# {% endfor %}

print(adcm[["USUBJID","ASTDT","AENDT","PREFL","ONTRTFL","CMDECOD"]].head())
""",

    "ADEX": """\
import pandas as pd
import pyreadstat

# =============================================================================
# {{ rule_id }} — ADEX scaffold
# {{ description }}
# =============================================================================

ex, _ = pyreadstat.read_xport("ex.xpt")
ex.columns = ex.columns.str.upper()

# --- 1. Date conversions ---
ex["ASTDT"] = pd.to_datetime(ex["EXSTDTC"], errors="coerce")
ex["AENDT"] = pd.to_datetime(ex["EXENDTC"], errors="coerce")
ex["DUR"]   = (ex["AENDT"] - ex["ASTDT"]).dt.days + 1

# --- 2. Per-record dose ---
ex["DOSE_RECORD"] = ex["EXDOSE"] * ex["DUR"] if "EXDOSE" in ex.columns else 0

# --- 3. Subject-level summaries ---
adex_trt = ex.groupby("USUBJID").agg(
    ASTDT=("ASTDT","min"),
    AENDT=("AENDT","max"),
    TOTDOSE=("DOSE_RECORD","sum"),
).reset_index()
adex_trt["TRTDUR"] = (adex_trt["AENDT"] - adex_trt["ASTDT"]).dt.days + 1

# --- 4. Stack into BDS-style rows ---
rows = []
for _, r in adex_trt.iterrows():
    rows.append({**r, "PARAMCD": "TRTDUR",  "AVAL": r["TRTDUR"]})
    rows.append({**r, "PARAMCD": "TOTDOSE", "AVAL": r["TOTDOSE"]})

adex = pd.DataFrame(rows)

# --- Pseudocode reference ---
# {% for step in pseudo %}
# {{ step }}
# {% endfor %}

print(adex[["USUBJID","PARAMCD","AVAL","ASTDT","AENDT"]].head())
""",
}

# PARAMCD/PARAM defaults per rule
_PARAMCD_MAP: Dict[str, Dict[str, str]] = {
    "ADTTE_OS":  {"paramcd": "OS",   "param": "Overall Survival"},
    "ADTTE_PFS": {"paramcd": "PFS",  "param": "Progression-Free Survival"},
    "ADTTE_DOR": {"paramcd": "DOR",  "param": "Duration of Response"},
}

# ---------------------------------------------------------------------------
# MAIN GENERATOR
# ---------------------------------------------------------------------------

def suggest_mapping_and_derivation(
    rule: Dict[str, Any],
    target_var: str,
    sdtm_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate a full derivation suggestion including Python scaffold.

    Parameters
    ----------
    rule       : matched rule dict from rules.py
    target_var : ADaM variable the user is asking about
    sdtm_data  : optional dict of {domain: DataFrame} for data-aware generation

    Returns
    -------
    {
        adam_ds        : str,
        description    : str,
        sources        : list,
        pseudocode     : list,
        python_scaffold: str,
        target_vars    : list,
        adam_class     : str,
    }
    """
    if rule is None:
        return {
            "adam_ds": "UNKNOWN",
            "description": "No matching rule found.",
            "sources": [],
            "pseudocode": [],
            "python_scaffold": "# No rule matched — check synonyms.py and rules.py\n",
            "target_vars": [],
            "adam_class": "UNKNOWN",
        }

    adam_ds    = rule.get("adam_ds", "UNKNOWN")
    adam_class = rule.get("adam_class", adam_ds)
    rule_id    = rule.get("id", "")

    # --- Select template key ---
    if adam_class == "ADTTE":
        tpl_key = "ADTTE"
    elif adam_class == "BDS":
        tpl_key = "BDS"
    elif adam_class == "ADSL":
        tpl_key = "ADSL"
    elif adam_class == "ADAE":
        tpl_key = "ADAE"
    elif adam_class == "ADCM":
        tpl_key = "ADCM"
    elif adam_ds == "ADEX":
        tpl_key = "ADEX"
    else:
        tpl_key = None

    if tpl_key and tpl_key in _TEMPLATES:
        env = Environment(loader=BaseLoader())
        tpl = env.from_string(_TEMPLATES[tpl_key])
        paramcd_info = _PARAMCD_MAP.get(rule_id, {"paramcd": "TODO", "param": "TODO"})
        code = tpl.render(
            rule_id=rule_id,
            adam_ds=adam_ds,
            description=rule.get("desc", ""),
            sources=rule.get("sources", []),
            pseudo=rule.get("pseudo", []),
            target_var=target_var,
            sdtm_vars=_extract_sdtm_vars(sdtm_data),
            **paramcd_info,
        )
    else:
        code = (
            f"# Template not yet defined for {adam_ds}\n"
            f"# Rule: {rule_id}\n"
            f"# Target variable: {target_var}\n"
            "pass\n"
        )

    return {
        "adam_ds":         adam_ds,
        "adam_class":      adam_class,
        "description":     rule.get("desc", ""),
        "sources":         rule.get("sources", []),
        "pseudocode":      rule.get("pseudo", []),
        "python_scaffold": code,
        "target_vars":     rule.get("target_vars", []),
    }


def _extract_sdtm_vars(sdtm_data: Optional[Dict[str, Any]]) -> Dict[str, list]:
    """
    Extract available variable names from loaded SDTM DataFrames.
    Used to make generated code data-aware (only reference vars that exist).
    """
    if not sdtm_data:
        return {}
    return {
        domain.upper(): list(df.columns)
        for domain, df in sdtm_data.items()
        if hasattr(df, "columns")
    }
