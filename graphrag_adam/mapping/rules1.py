"""
rules.py — Extended ADaM derivation rule library (no LLM required).

Each rule contains:
  - id         : unique rule identifier
  - when       : trigger keywords/phrases (for matching)
  - target_vars: list of ADaM variables this rule produces
  - adam_ds    : target ADaM dataset
  - adam_class : ADSL | BDS | ADTTE | ADAE | ADCM | ADEX
  - desc       : human-readable derivation description
  - sources    : list of {domain, vars} source mappings
  - pseudo     : ordered derivation pseudocode steps
  - cnsr_hierarchy: (ADTTE only) ordered censoring rules
  - bds_param  : (BDS only) PARAMCD / PARAM values produced
"""

from typing import Dict, Any, Optional, List
import re

# ---------------------------------------------------------------------------
# RULE LIBRARY
# ---------------------------------------------------------------------------

RULES: List[Dict[str, Any]] = [

    # ------------------------------------------------------------------ ADTTE
    {
        "id": "ADTTE_OS",
        "when": ["overall survival", "os", "death", "mortality"],
        "target_vars": ["AVAL", "CNSR", "ADT", "STARTDT", "EVNTDESC", "CNSDTDSC"],
        "adam_ds": "ADTTE",
        "adam_class": "ADTTE",
        "desc": "Overall Survival: AVAL = days from randomization to death or censor date.",
        "sources": [
            {"domain": "ADSL", "vars": ["TRTSDT", "RANDDT", "DTHDT", "DTHDTF"]},
            {"domain": "DS",   "vars": ["DSDECOD", "DSTERM", "DSSTDTC", "DSSCAT"]},
            {"domain": "SV",   "vars": ["SVSTDTC", "SVENDTC"]},
        ],
        "pseudo": [
            "Step 1 — Death flag: DTHFL = 'Y' if DS record with DSDECOD='DEATH' exists or ADSL.DTHDT not null",
            "Step 2 — Event date: ADT = ADSL.DTHDT if DTHFL='Y'",
            "Step 3 — Censoring hierarchy (apply in order, first non-null wins):",
            "         C1: Last study visit date from SV (SVENDTC of last record)",
            "         C2: Last contact date from DS where DSSCAT='LAST KNOWN ALIVE'",
            "         C3: ADSL.TRTEDT (last treatment date)",
            "         C4: ADSL.RANDDT (randomization date) as minimum censor",
            "Step 4 — CNSR = 0 if DTHFL='Y' (event); else CNSR = 1 (censored)",
            "Step 5 — AVAL = ADT - STARTDT + 1 (in days, ISO date subtraction)",
            "Step 6 — EVNTDESC = 'DEATH' if event; else censoring reason string",
            "Step 7 — PARAMCD = 'OS'; PARAM = 'Overall Survival'",
        ],
        "cnsr_hierarchy": [
            {"order": 1, "source": "SV",   "var": "SVENDTC",  "condition": "last record per subject"},
            {"order": 2, "source": "DS",   "var": "DSSTDTC",  "condition": "DSSCAT = 'LAST KNOWN ALIVE'"},
            {"order": 3, "source": "ADSL", "var": "TRTEDT",   "condition": "not null"},
            {"order": 4, "source": "ADSL", "var": "RANDDT",   "condition": "fallback minimum"},
        ],
    },

    {
        "id": "ADTTE_PFS",
        "when": ["progression-free survival", "pfs", "progression", "disease progression"],
        "target_vars": ["AVAL", "CNSR", "ADT", "STARTDT", "EVNTDESC"],
        "adam_ds": "ADTTE",
        "adam_class": "ADTTE",
        "desc": "PFS: AVAL = days from randomization to first progression or death.",
        "sources": [
            {"domain": "ADSL", "vars": ["TRTSDT", "RANDDT"]},
            {"domain": "RS",   "vars": ["RSDTC", "RSSTRESC", "RSDECOD", "RSCAT", "RSSCAT"]},
            {"domain": "DS",   "vars": ["DSDECOD", "DSSTDTC"]},
            {"domain": "SV",   "vars": ["SVENDTC"]},
        ],
        "pseudo": [
            "Step 1 — Progression date: PROGDT = min(RS.RSDTC) where RSSTRESC='PD' or RSDECOD='PROGRESSIVE DISEASE'",
            "Step 2 — Death date: DTHDT = ADSL.DTHDT",
            "Step 3 — Event date: ADT = min(PROGDT, DTHDT) — earliest non-null",
            "Step 4 — CNSR = 0 if ADT from progression or death; else 1",
            "Step 5 — Censoring hierarchy (same as OS, apply if no event)",
            "Step 6 — AVAL = ADT - STARTDT + 1 (days)",
            "Step 7 — PARAMCD = 'PFS'; PARAM = 'Progression-Free Survival'",
        ],
        "cnsr_hierarchy": [
            {"order": 1, "source": "RS",   "var": "RSDTC",   "condition": "last evaluable assessment"},
            {"order": 2, "source": "SV",   "var": "SVENDTC", "condition": "last visit"},
            {"order": 3, "source": "ADSL", "var": "TRTEDT",  "condition": "not null"},
        ],
    },

    {
        "id": "ADTTE_DOR",
        "when": ["duration of response", "dor", "response duration"],
        "target_vars": ["AVAL", "CNSR", "ADT", "STARTDT"],
        "adam_ds": "ADTTE",
        "adam_class": "ADTTE",
        "desc": "DOR: time from first response to progression/death, in responders only.",
        "sources": [
            {"domain": "RS", "vars": ["RSDTC", "RSSTRESC", "RSDECOD"]},
            {"domain": "DS", "vars": ["DSDECOD", "DSSTDTC"]},
        ],
        "pseudo": [
            "Step 1 — Restrict to subjects with confirmed response (CR or PR)",
            "Step 2 — STARTDT = first RS date where RSSTRESC in ('CR','PR')",
            "Step 3 — Event date = first RS date of PD, or death date",
            "Step 4 — CNSR = 0 if progression/death; 1 otherwise",
            "Step 5 — AVAL = ADT - STARTDT + 1 (days)",
            "Step 6 — PARAMCD = 'DOR'",
        ],
        "cnsr_hierarchy": [],
    },

    # ------------------------------------------------------------------ ADSL
    {
        "id": "ADSL_FLAGS",
        "when": ["itt", "safety", "pps", "population flag", "analysis population",
                 "saffl", "ittfl", "ppsfl", "fasfl", "randfl"],
        "target_vars": ["SAFFL", "ITTFL", "PPSFL", "FASFL", "RANDFL", "ENRLFL"],
        "adam_ds": "ADSL",
        "adam_class": "ADSL",
        "desc": "Population flags driven by protocol inclusion/exclusion and dosing.",
        "sources": [
            {"domain": "EX", "vars": ["EXTRT", "EXSTDTC", "EXDOSE"]},
            {"domain": "DM", "vars": ["USUBJID", "RFSTDTC", "ARMCD", "ACTARMCD"]},
            {"domain": "DS", "vars": ["DSDECOD", "DSCAT"]},
        ],
        "pseudo": [
            "RANDFL = 'Y' if DM.ARMCD not in ('NOTASSGN','SCRNFAIL')",
            "ENRLFL = 'Y' if subject signed ICF (per DS or DM.RFSTDTC not null)",
            "SAFFL  = 'Y' if received >= 1 dose (EX record with EXDOSE > 0 exists)",
            "ITTFL  = 'Y' if randomized per SAP definition (usually = RANDFL)",
            "FASFL  = 'Y' per Full Analysis Set criteria in SAP",
            "PPSFL  = 'Y' per Per-Protocol Set criteria in SAP",
        ],
    },

    {
        "id": "ADSL_DEMOG",
        "when": ["age", "sex", "race", "demographics", "baseline", "trtsdt",
                 "trtedtc", "trt01p", "treatment start"],
        "target_vars": ["AGE", "AGEGR1", "SEX", "RACE", "ETHNIC",
                        "TRTSDT", "TRTEDT", "TRT01P", "TRT01A", "EOSSTT"],
        "adam_ds": "ADSL",
        "adam_class": "ADSL",
        "desc": "Demographic and treatment variables derived from DM and EX.",
        "sources": [
            {"domain": "DM", "vars": ["AGE", "SEX", "RACE", "ETHNIC", "BRTHDTC",
                                       "RFSTDTC", "RFENDTC", "ARMCD", "ARM", "ACTARM"]},
            {"domain": "EX", "vars": ["EXSTDTC", "EXENDTC", "EXTRT", "EXDOSE"]},
            {"domain": "DS", "vars": ["DSDECOD", "DSSCAT", "DSSTDTC"]},
        ],
        "pseudo": [
            "AGE    = DM.AGE (as-is) or floor((RFSTDTC - BRTHDTC) / 365.25)",
            "AGEGR1 = categorize AGE per SAP cut-points (e.g. '<65', '>=65')",
            "SEX    = DM.SEX",
            "RACE   = DM.RACE",
            "TRTSDT = min(EX.EXSTDTC) per subject (first dose date)",
            "TRTEDT = max(EX.EXENDTC) per subject (last dose date)",
            "TRT01P = DM.ARM (planned treatment)",
            "TRT01A = DM.ACTARM (actual treatment)",
            "EOSSTT = DS.DSDECOD where DSCAT='DISPOSITION EVENT'",
        ],
    },

    # ------------------------------------------------------------------ ADAE
    {
        "id": "ADAE_BASE",
        "when": ["adverse event", "adae", "ae", "toxicity", "teae",
                 "treatment emergent", "aestdtc", "severity"],
        "target_vars": ["ASTDT", "AENDT", "AVAL", "TRTEMFL", "AESEQ",
                        "AESEVN", "AESER", "AESDTH"],
        "adam_ds": "ADAE",
        "adam_class": "ADAE",
        "desc": "ADAE: treatment-emergent AE flags, severity grading, relatedness.",
        "sources": [
            {"domain": "AE",   "vars": ["AETERM", "AEDECOD", "AESTDTC", "AEENDTC",
                                         "AESEV", "AESER", "AEREL", "AEOUT", "AESDTH",
                                         "AELLT", "AELLTCD", "AEPTCD"]},
            {"domain": "ADSL", "vars": ["TRTSDT", "TRTEDT", "SAFFL"]},
        ],
        "pseudo": [
            "ASTDT  = convert AE.AESTDTC to SAS date (ISO 8601)",
            "AENDT  = convert AE.AEENDTC to SAS date",
            "TRTEMFL= 'Y' if ASTDT >= ADSL.TRTSDT and ASTDT <= ADSL.TRTEDT + 30",
            "AESEVN = map AESEV to numeric (MILD=1, MODERATE=2, SEVERE=3)",
            "AESEQ  = sequence number within subject",
            "Merge ADSL for TRTSDT, TRTEDT, SAFFL",
            "Keep only SAFFL='Y' subjects per SAP",
        ],
    },

    # ------------------------------------------------------------------ ADLB / ADVS (BDS)
    {
        "id": "BDS_LAB",
        "when": ["lab", "laboratory", "adlb", "lbtest", "lbtestcd",
                 "baseline lab", "change from baseline", "chg", "base"],
        "target_vars": ["AVAL", "AVALC", "BASE", "CHG", "PCHG", "BNRIND",
                        "ANRIND", "PARAMCD", "PARAM", "ADT", "ABLFL"],
        "adam_ds": "ADLB",
        "adam_class": "BDS",
        "desc": "ADLB BDS: lab values with baseline, change from baseline, reference range indicators.",
        "sources": [
            {"domain": "LB",   "vars": ["LBTESTCD", "LBTEST", "LBORRES", "LBORRESU",
                                         "LBSTRESC", "LBSTRESN", "LBSTRESU",
                                         "LBDTC", "LBBLFL", "LBNRIND",
                                         "LBSTNRLO", "LBSTNRHI"]},
            {"domain": "ADSL", "vars": ["TRTSDT", "SAFFL"]},
        ],
        "pseudo": [
            "PARAMCD = LB.LBTESTCD; PARAM = LB.LBTEST",
            "AVAL    = LB.LBSTRESN (numeric standardized value)",
            "AVALC   = LB.LBSTRESC (character standardized value)",
            "ADT     = convert LB.LBDTC to SAS date",
            "ABLFL   = 'Y' for baseline record per SAP definition",
            "         (typically last non-missing pre-dose value)",
            "BASE    = AVAL where ABLFL='Y' (merged back)",
            "CHG     = AVAL - BASE (post-baseline only)",
            "PCHG    = (CHG / BASE) * 100 (if BASE != 0)",
            "ANRIND  = 'LOW'/'NORMAL'/'HIGH' per LBSTNRLO/LBSTNRHI",
            "BNRIND  = ANRIND at baseline",
        ],
    },

    {
        "id": "BDS_VS",
        "when": ["vital signs", "advs", "vs", "blood pressure", "weight",
                 "height", "bmi", "pulse", "temperature"],
        "target_vars": ["AVAL", "BASE", "CHG", "PCHG", "PARAMCD", "ADT", "ABLFL"],
        "adam_ds": "ADVS",
        "adam_class": "BDS",
        "desc": "ADVS BDS: vital sign measurements with baseline and change from baseline.",
        "sources": [
            {"domain": "VS",   "vars": ["VSTESTCD", "VSTEST", "VSORRES", "VSORRESU",
                                         "VSSTRESC", "VSSTRESN", "VSSTRESU", "VSDTC",
                                         "VSBLFL"]},
            {"domain": "ADSL", "vars": ["TRTSDT"]},
        ],
        "pseudo": [
            "PARAMCD = VS.VSTESTCD; PARAM = VS.VSTEST",
            "AVAL    = VS.VSSTRESN",
            "ADT     = convert VS.VSDTC to SAS date",
            "ABLFL   = 'Y' for last pre-dose record per PARAMCD per subject",
            "BASE    = AVAL at ABLFL='Y'",
            "CHG     = AVAL - BASE",
            "BMI: if PARAMCD='BMI' and missing, derive = WEIGHT(kg) / HEIGHT(m)^2",
        ],
    },

    # ------------------------------------------------------------------ ADEX
    {
        "id": "ADEX_BASE",
        "when": ["exposure", "adex", "dose", "dosing", "cumulative dose",
                 "duration of treatment", "dose intensity"],
        "target_vars": ["AVAL", "PARAMCD", "ASTDT", "AENDT", "EXDOSE",
                        "TOTDOSE", "TRTDUR"],
        "adam_ds": "ADEX",
        "adam_class": "BDS",
        "desc": "ADEX: per-subject dose summary including total dose and treatment duration.",
        "sources": [
            {"domain": "EX", "vars": ["EXTRT", "EXDOSE", "EXDOSU", "EXSTDTC",
                                       "EXENDTC", "EXDOSFRQ", "EXROUTE"]},
        ],
        "pseudo": [
            "ASTDT   = min(EX.EXSTDTC) per subject",
            "AENDT   = max(EX.EXENDTC) per subject",
            "TRTDUR  = AENDT - ASTDT + 1 (days)",
            "TOTDOSE = sum(EXDOSE * duration_per_record) per subject",
            "PARAMCD options: 'TOTDOSE', 'TRTDUR', 'DOSEINT'",
            "Dose intensity = TOTDOSE / planned total dose * 100",
        ],
    },

    # ------------------------------------------------------------------ ADRS
    {
        "id": "ADRS_BASE",
        "when": ["response", "adrs", "best overall response", "bor", "recist",
                 "complete response", "partial response", "cr", "pr", "sd", "pd",
                 "objective response", "orr"],
        "target_vars": ["AVALC", "AVAL", "PARAMCD", "ADT", "RSSTRESC", "BORFL"],
        "adam_ds": "ADRS",
        "adam_class": "BDS",
        "desc": "ADRS: tumor response per RECIST or protocol-defined criteria.",
        "sources": [
            {"domain": "RS", "vars": ["RSDTC", "RSSTRESC", "RSDECOD",
                                       "RSCAT", "RSSCAT", "RSEVAL"]},
            {"domain": "TU", "vars": ["TUTESTCD", "TUSTRESC", "TUDTC"]},
            {"domain": "TR", "vars": ["TRTESTCD", "TRSTRESC", "TRDTC"]},
        ],
        "pseudo": [
            "AVALC   = RS.RSSTRESC (CR/PR/SD/PD/NE/NA)",
            "AVAL    = map AVALC to numeric: CR=1, PR=2, SD=3, PD=4, NE=5",
            "ADT     = RS.RSDTC converted to SAS date",
            "BORFL   = 'Y' for best overall response record per subject",
            "BOR logic: best (lowest AVAL) non-PD response, or PD if no better",
            "PARAMCD options: 'OVRLRESP', 'BOR', 'BORSRES'",
            "Confirmation logic: 2 consecutive assessments >= 4 weeks apart",
        ],
    },

    # ------------------------------------------------------------------ ADCM
    {
        "id": "ADCM_BASE",
        "when": ["concomitant medication", "adcm", "cm", "prior medication",
                 "conmed", "prior therapy"],
        "target_vars": ["ASTDT", "AENDT", "CMDECOD", "CMCAT", "ONTRTFL", "PREFL"],
        "adam_ds": "ADCM",
        "adam_class": "ADCM",
        "desc": "ADCM: concomitant and prior medications with on-treatment flags.",
        "sources": [
            {"domain": "CM",   "vars": ["CMTRT", "CMDECOD", "CMCAT", "CMSCAT",
                                         "CMSTDTC", "CMENDTC", "CMINDC", "CMROUTE"]},
            {"domain": "ADSL", "vars": ["TRTSDT", "TRTEDT"]},
        ],
        "pseudo": [
            "ASTDT   = convert CM.CMSTDTC to SAS date",
            "AENDT   = convert CM.CMENDTC to SAS date (or TRTEDT if ongoing)",
            "PREFL   = 'Y' if ASTDT < ADSL.TRTSDT",
            "ONTRTFL = 'Y' if medication overlaps with treatment period",
            "         (ASTDT <= TRTEDT and (AENDT >= TRTSDT or AENDT missing))",
        ],
    },
]


# ---------------------------------------------------------------------------
# SCORING-BASED RULE MATCHING  (replaces simple keyword loop)
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> List[str]:
    """Lowercase, split on non-alphanumeric boundaries."""
    return re.findall(r"[a-z0-9]+", text.lower())


def _score_rule(rule: Dict[str, Any], q_tokens: List[str],
                target_var: Optional[str]) -> float:
    """
    Score a rule against query tokens and optional target variable.

    Scoring:
      +2  per 'when' phrase fully present in query
      +1  per 'when' single token present in query
      +3  if target_var matches a rule target_var exactly
      +1  if target_var matches rule adam_ds
    """
    score = 0.0
    q_text = " ".join(q_tokens)

    for phrase in rule.get("when", []):
        phrase_tokens = _tokenize(phrase)
        if all(t in q_tokens for t in phrase_tokens):
            score += 2.0 if len(phrase_tokens) > 1 else 1.0

    if target_var:
        tv = target_var.upper()
        if tv in [v.upper() for v in rule.get("target_vars", [])]:
            score += 3.0
        if tv == rule.get("adam_ds", "").upper():
            score += 1.0

    return score


def match_rule_for_question(
    question: str,
    target_var: Optional[str] = None,
    top_n: int = 1,
) -> Optional[Dict[str, Any]]:
    """
    Return the best-matching rule for a question string.

    Parameters
    ----------
    question   : free-text question from the user
    target_var : optional ADaM variable name hint (e.g. 'AVAL', 'CNSR')
    top_n      : if > 1, returns a list of top N rules instead of single rule

    Returns
    -------
    Single rule dict (top_n=1) or list of rule dicts (top_n>1), or None.
    """
    q_tokens = _tokenize(question)
    scored = [
        (rule, _score_rule(rule, q_tokens, target_var))
        for rule in RULES
    ]
    scored.sort(key=lambda x: x[1], reverse=True)

    # Filter out zero-score rules (no match at all)
    matched = [(r, s) for r, s in scored if s > 0]

    if not matched:
        # Final fallback: return first ADTTE rule if time/event language detected
        time_words = {"time", "event", "survival", "censor", "hazard", "endpoint"}
        if time_words & set(q_tokens):
            return RULES[0]
        return None

    if top_n == 1:
        return matched[0][0]
    return [r for r, _ in matched[:top_n]]


def get_rule_by_id(rule_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a rule directly by its ID."""
    return next((r for r in RULES if r["id"] == rule_id), None)


def get_rules_by_dataset(adam_ds: str) -> List[Dict[str, Any]]:
    """Return all rules targeting a specific ADaM dataset."""
    return [r for r in RULES if r["adam_ds"].upper() == adam_ds.upper()]


def get_rules_by_class(adam_class: str) -> List[Dict[str, Any]]:
    """Return all rules of a given ADaM class (ADSL, BDS, ADTTE, ADAE, etc.)."""
    return [r for r in RULES if r.get("adam_class", "").upper() == adam_class.upper()]


def list_all_target_vars() -> Dict[str, str]:
    """Return mapping of every target variable → its rule ID."""
    result = {}
    for rule in RULES:
        for var in rule.get("target_vars", []):
            result[var] = rule["id"]
    return result
