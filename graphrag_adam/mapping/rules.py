
from typing import Dict, Any, Optional

# Minimal rule library for common endpoints
RULES = [
    {
        "id": "ADTTE_OS",
        "when": ["overall survival","os"],
        "adam_ds": "ADTTE",
        "desc": "Overall Survival: AVAL = days from randomization/start to death; CNSR per censoring rules.",
        "sources": [{"domain": "ADSL", "vars": ["TRTSDT","RANDDT"]},
                    {"domain": "AE", "vars": ["AECAT","AETERM","AEDECOD","AESTDTC"]},
                    {"domain": "DS", "vars": ["DSDECOD","DSTERM","DSSTDTC"]},
                    {"domain": "SV", "vars": ["SVSTDTC","SVENDTC"]}],
        "pseudo": [
            "ADT = event/censor date (death date if available else censor date)",
            "AVAL = ADT - STARTDT (in days)",
            "CNSR = 0 if death event observed; else 1 per censoring hierarchy"
        ]
    },
    {
        "id": "ADTTE_PFS",
        "when": ["progression-free survival","pfs"],
        "adam_ds": "ADTTE",
        "desc": "PFS: AVAL = days from randomization/start to progression or death; censor otherwise.",
        "sources": [{"domain": "ADSL", "vars": ["TRTSDT"]},
                    {"domain": "RS", "vars": ["RSDTC","RSSTRESC","RSDECOD"]},
                    {"domain": "DS", "vars": ["DSDECOD","DSSTDTC"]}],
        "pseudo": [
            "Determine earliest of progression date (RS) or death date (DS) as ADT",
            "AVAL = ADT - STARTDT (in days)",
            "CNSR = 0 if event; 1 if censored"
        ]
    },
    {
        "id": "ADSL_FLAGS",
        "when": ["itt","safety","pps","population flag"],
        "adam_ds": "ADSL",
        "desc": "Population flags: SAFFL, ITTFL, PPSFL driven by protocol inclusion/exclusion and dosing.",
        "sources": [{"domain": "EX","vars":["EXTRT","EXSTDTC"]},
                    {"domain": "DM","vars":["USUBJID","RFSTDTC"]}],
        "pseudo": [
            "SAFFL = 'Y' if subject received at least one dose",
            "ITTFL = 'Y' if randomized (RANDDT not null) or per SAP",
            "PPSFL = 'Y' per SAP analysis population definition"
        ]
    }
]

def match_rule_for_question(question: str, target_var: str) -> Optional[Dict[str,Any]]:
    q = question.lower()
    for r in RULES:
        if any(tok in q for tok in r["when"]):
            return r
    # fallback: choose ADTTE if mentions time/event
    if any(w in q for w in ["time to", "event", "survival", "censor"]):
        return next(r for r in RULES if r["id"].startswith("ADTTE_"))
    return RULES[0] if RULES else None
