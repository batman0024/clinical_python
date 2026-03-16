"""
synonyms.py — ADaM variable and endpoint normalization (no LLM required).

Provides:
  - ALIASES         : phrase → canonical endpoint name
  - VAR_ALIASES     : phrase/keyword → ADaM variable name(s)
  - normalize_var() : resolve question text → most relevant ADaM variable(s)
  - normalize_endpoint() : resolve question text → canonical endpoint string
"""

import re
from typing import List, Optional, Dict

# ---------------------------------------------------------------------------
# ENDPOINT-LEVEL ALIASES
# Maps natural language phrases → canonical endpoint identifier
# ---------------------------------------------------------------------------
ALIASES: Dict[str, List[str]] = {
    "overall survival": [
        "OS", "OVERALL SURVIVAL", "SURVIVAL", "TIME TO DEATH",
        "MORTALITY", "DEATH EVENT", "ALL CAUSE MORTALITY",
    ],
    "progression-free survival": [
        "PFS", "PROGRESSION FREE SURVIVAL", "PROGRESSION-FREE SURVIVAL",
        "TIME TO PROGRESSION", "TTP", "TIME TO PD",
    ],
    "duration of response": [
        "DOR", "DURATION OF RESPONSE", "RESPONSE DURATION",
        "TIME FROM RESPONSE",
    ],
    "objective response rate": [
        "ORR", "RESPONSE RATE", "OBJECTIVE RESPONSE",
        "OVERALL RESPONSE RATE", "CONFIRMED RESPONSE RATE",
    ],
    "best overall response": [
        "BOR", "BEST RESPONSE", "BEST OVERALL RESPONSE",
        "RECIST RESPONSE",
    ],
    "adverse event": [
        "AE", "ADVERSE EVENT", "TEAE", "TREATMENT EMERGENT",
        "TOXICITY", "SAFETY EVENT", "SAE", "SERIOUS ADVERSE EVENT",
    ],
    "laboratory": [
        "LAB", "LABORATORY", "LABS", "LB", "HAEMATOLOGY",
        "HEMATOLOGY", "CHEMISTRY", "BIOCHEMISTRY",
    ],
    "vital signs": [
        "VS", "VITAL SIGNS", "VITALS", "BLOOD PRESSURE",
        "HEART RATE", "PULSE", "WEIGHT", "HEIGHT", "BMI", "TEMPERATURE",
    ],
    "exposure": [
        "EXPOSURE", "DOSE", "DOSING", "TREATMENT DURATION",
        "CUMULATIVE DOSE", "DOSE INTENSITY", "ADEX",
    ],
    "concomitant medication": [
        "CM", "CONMED", "CONCOMITANT MED", "PRIOR MEDICATION",
        "PRIOR THERAPY", "CONCOMITANT MEDICATION",
    ],
    "population flag": [
        "ITT", "SAFETY", "PPS", "POPULATION", "ANALYSIS SET",
        "SAFFL", "ITTFL", "PPSFL", "FASFL", "RANDFL", "ENRLFL",
        "FULL ANALYSIS SET", "FAS", "PER PROTOCOL",
    ],
    "demographics": [
        "DEMOGRAPHICS", "DEMOG", "AGE", "SEX", "RACE", "ETHNIC",
        "BASELINE CHARACTERISTICS", "TREATMENT START",
    ],
}

# ---------------------------------------------------------------------------
# VARIABLE-LEVEL ALIASES
# Maps keywords/phrases → specific ADaM variable name(s)
# Used to resolve what variable the user is actually asking about
# ---------------------------------------------------------------------------
VAR_ALIASES: Dict[str, List[str]] = {
    # ADTTE variables
    "AVAL":    ["aval", "analysis value", "time to event", "tte value",
                "days to event", "survival time"],
    "CNSR":    ["cnsr", "censor", "censoring", "censored", "censoring flag",
                "censor flag", "cnsr flag"],
    "ADT":     ["adt", "analysis date", "event date", "censor date",
                "death date", "progression date"],
    "STARTDT": ["startdt", "start date", "randomization date", "randdt",
                "trtsdt", "treatment start date", "reference start date"],
    "EVNTDESC":["evntdesc", "event description", "event reason"],
    "CNSDTDSC":["cnsdtdsc", "censor description", "censoring reason"],
    "PARAMCD": ["paramcd", "parameter code", "param code"],
    "PARAM":   ["param", "parameter name", "parameter label"],

    # BDS variables
    "BASE":    ["base", "baseline", "baseline value", "base value"],
    "CHG":     ["chg", "change", "change from baseline", "delta"],
    "PCHG":    ["pchg", "percent change", "percentage change",
                "percent change from baseline"],
    "ABLFL":   ["ablfl", "baseline flag", "baseline record flag"],
    "ANRIND":  ["anrind", "reference range indicator", "normal range",
                "low normal high", "out of range"],
    "BNRIND":  ["bnrind", "baseline reference range", "baseline normal"],
    "AVALC":   ["avalc", "character value", "response category",
                "character analysis value"],

    # ADSL variables
    "TRTSDT":  ["trtsdt", "treatment start", "first dose date",
                "start of treatment"],
    "TRTEDT":  ["trtedt", "treatment end", "last dose date",
                "end of treatment"],
    "TRT01P":  ["trt01p", "planned treatment", "treatment arm", "arm"],
    "TRT01A":  ["trt01a", "actual treatment", "actual arm"],
    "SAFFL":   ["saffl", "safety flag", "safety population"],
    "ITTFL":   ["ittfl", "itt flag", "intent to treat", "itt population"],
    "PPSFL":   ["ppsfl", "pps flag", "per protocol"],
    "RANDFL":  ["randfl", "randomized flag", "randomization flag"],
    "AGE":     ["age", "patient age", "subject age"],
    "AGEGR1":  ["agegr1", "age group", "age category"],
    "SEX":     ["sex", "gender"],
    "RACE":    ["race", "ethnicity", "ethnic"],
    "EOSSTT":  ["eosstt", "end of study", "study completion",
                "disposition", "discontinuation"],

    # ADAE variables
    "ASTDT":   ["astdt", "ae start date", "onset date", "start date"],
    "AENDT":   ["aendt", "ae end date", "resolution date", "end date"],
    "TRTEMFL": ["trtemfl", "treatment emergent", "teae flag",
                "on treatment ae"],
    "AESEVN":  ["aesevn", "severity grade", "ae severity", "ctcae grade"],
    "AESER":   ["aeser", "serious ae", "sae flag"],

    # ADEX variables
    "TOTDOSE": ["totdose", "total dose", "cumulative dose"],
    "TRTDUR":  ["trtdur", "treatment duration", "duration of treatment"],

    # ADRS variables
    "BORFL":   ["borfl", "best response flag", "bor flag"],
    "RSSTRESC": ["rsstresc", "response value", "recist category"],

    # ADCM variables
    "PREFL":   ["prefl", "prior medication flag", "prior med flag"],
    "ONTRTFL": ["ontrtfl", "on treatment flag", "concomitant flag"],
}

# Inverted lookup: keyword → variable name
_KEYWORD_TO_VAR: Dict[str, str] = {
    kw: var
    for var, keywords in VAR_ALIASES.items()
    for kw in keywords
}

# Inverted endpoint lookup: alias → canonical endpoint
_ALIAS_TO_ENDPOINT: Dict[str, str] = {
    alias.lower(): endpoint
    for endpoint, aliases in ALIASES.items()
    for alias in aliases
}


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def normalize_var(
    question: str,
    candidate_vars: Optional[List[str]] = None,
    return_all: bool = False,
) -> str | List[str]:
    """
    Resolve a question string to the most relevant ADaM variable name(s).

    Parameters
    ----------
    question       : free-text user question
    candidate_vars : optional list of variable names to prefer if found in text
    return_all     : if True, return all matched variables (sorted by confidence)

    Returns
    -------
    Single variable name string (return_all=False) or list (return_all=True).
    Defaults to 'AVAL' if nothing matched.
    """
    q_lower = question.lower()
    tokens = _tokenize(question)
    matched: Dict[str, int] = {}  # var → match score

    # 1. Exact mention of a candidate variable in question text
    if candidate_vars:
        for v in candidate_vars:
            if v.lower() in q_lower:
                matched[v] = matched.get(v, 0) + 5

    # 2. Check full question text against keyword→var mapping
    for kw, var in _KEYWORD_TO_VAR.items():
        if kw in q_lower:
            # weight multi-word matches higher
            weight = 2 if " " in kw else 1
            matched[var] = matched.get(var, 0) + weight

    # 3. Token-level scan for variable names directly mentioned (e.g. "cnsr")
    for token in tokens:
        token_upper = token.upper()
        if token_upper in VAR_ALIASES:
            matched[token_upper] = matched.get(token_upper, 0) + 4

    if not matched:
        return ["AVAL"] if return_all else "AVAL"

    sorted_vars = sorted(matched, key=lambda v: matched[v], reverse=True)
    return sorted_vars if return_all else sorted_vars[0]


def normalize_endpoint(question: str) -> Optional[str]:
    """
    Map a question to a canonical endpoint name from ALIASES.

    Returns e.g. 'overall survival', 'progression-free survival', or None.
    """
    q_lower = question.lower()
    tokens = _tokenize(question)

    best_match = None
    best_score = 0

    for endpoint, aliases in ALIASES.items():
        score = 0
        for alias in aliases:
            alias_lower = alias.lower()
            alias_tokens = _tokenize(alias)
            if alias_lower in q_lower:
                score += 2 if len(alias_tokens) > 1 else 1
            elif all(t in tokens for t in alias_tokens):
                score += 1
        if score > best_score:
            best_score = score
            best_match = endpoint

    return best_match if best_score > 0 else None


def get_vars_for_dataset(adam_ds: str) -> List[str]:
    """
    Return all ADaM variable names typically associated with a dataset.
    Uses VAR_ALIASES keys filtered by known dataset-variable mapping.
    """
    DS_VAR_MAP: Dict[str, List[str]] = {
        "ADTTE": ["AVAL", "CNSR", "ADT", "STARTDT", "PARAMCD", "PARAM",
                  "EVNTDESC", "CNSDTDSC"],
        "ADSL":  ["TRTSDT", "TRTEDT", "TRT01P", "TRT01A", "SAFFL", "ITTFL",
                  "PPSFL", "RANDFL", "AGE", "AGEGR1", "SEX", "RACE",
                  "ETHNIC", "EOSSTT"],
        "ADLB":  ["AVAL", "AVALC", "BASE", "CHG", "PCHG", "PARAMCD", "PARAM",
                  "ADT", "ABLFL", "ANRIND", "BNRIND"],
        "ADVS":  ["AVAL", "BASE", "CHG", "PCHG", "PARAMCD", "PARAM",
                  "ADT", "ABLFL"],
        "ADAE":  ["ASTDT", "AENDT", "TRTEMFL", "AESEVN", "AESER", "AESDTH"],
        "ADEX":  ["AVAL", "PARAMCD", "ASTDT", "AENDT", "TOTDOSE", "TRTDUR"],
        "ADRS":  ["AVALC", "AVAL", "PARAMCD", "ADT", "BORFL", "RSSTRESC"],
        "ADCM":  ["ASTDT", "AENDT", "PREFL", "ONTRTFL"],
    }
    return DS_VAR_MAP.get(adam_ds.upper(), [])
