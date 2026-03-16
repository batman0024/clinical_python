
import re

# Heuristic normalization for ADaM var target detection
ALIASES = {
    "primary endpoint": ["PRIMARY ENDPOINT", "PRIMARY EFFICACY ENDPOINT", "PRIMARY TTE", "PRIMARY OS", "PRIMARY PFS"],
    "overall survival": ["OS","OVERALL SURVIVAL"],
    "progression-free survival": ["PFS","PROGRESSION-FREE SURVIVAL"],
    "objective response rate": ["ORR","RESPONSE RATE"],
}

def normalize_var(question: str, candidate_vars):
    q = question.lower()
    # If explicit mention of ADaM variable
    for v in candidate_vars:
        if v.lower() in q:
            return v
    # map endpoint phrases → suggested ADaM construct
    w = re.findall(r"[a-z]+", q)
    if "overall" in w and "survival" in w or "os" in w:
        return "AVAL"  # ADTTE AVAL typically holds time; plus CNSR
    if "progression" in w or "pfs" in w:
        return "AVAL"
    if "primary" in w and "endpoint" in w:
        return "AVAL"
    if "response" in w or "orr" in w:
        return "AVAL"
    # fallback
    return next(iter(candidate_vars), "AVAL")
