
import re

# Simple token regex
TOKEN = re.compile(r"[A-Za-z0-9_./%-]+")

# Common ADaM variables (extend as needed)
ADAM_VARS = {
    "ADSL": ["USUBJID","TRT01P","TRT01A","AGE","SEX","RACE","SAFFL","ITTFL","PPSFL","TRTSDT","TRTEDT"],
    "ADTTE": ["USUBJID","PARAM","PARAMCD","AVAL","CNSR","STARTDT","ADT","ADY","EVNTDESC"],
    "ADAE": ["USUBJID","AETERM","AEDECOD","AESER","AESTDT","AEENDT","AESEV","AEREL","TRTEMFL"],
    "ADLB": ["USUBJID","PARAM","PARAMCD","AVAL","CHG","BASETYPE","VISIT","AVISITN"]
}
# Build a set
ADAM_VAR_SET = set(v for lst in ADAM_VARS.values() for v in lst)

# Domain variable-like patterns (capitalized + underscores)
VARLIKE = re.compile(r"[A-Z]{2,}[A-Z0-9_]{0,}")

# Endpoints / estimands keywords
ENDPOINT_HINTS = [
    "primary endpoint", "secondary endpoint", "overall survival", "progression-free survival",
    "objective response rate", "time to event", "TTF", "TTE", "responder", "CR", "PR", "BOR",
    "RECIST", "baseline", "washout", "censor", "imputation", "non-inferiority", "superiority"
]
