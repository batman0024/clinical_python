from typing import Dict, Any
from .codegen_python import (
    gen_adsl_flags,
    gen_adtte_os,
    gen_adtte_pfs
)

def suggest_mapping_and_derivation(rule: Dict[str, Any], target_var: str, sdtm_data=None):
    """
    Returns a unified structure describing the mapping/derivation:
    {
        "adam_ds": "...",
        "description": "...",
        "sources": [...],
        "pseudocode": [...],
        "python_scaffold": "..."
    }
    """

    if rule is None:
        return {
            "adam_ds": "UNKNOWN",
            "description": "No matching rule found for the question.",
            "sources": [],
            "pseudocode": [],
            "python_scaffold": "# No rule available\n"
        }

    adam_ds = rule.get("adam_ds", "UNKNOWN")
    rid = rule.get("id", "")

    # Select the correct scaffold generator
    if adam_ds == "ADSL":
        code = gen_adsl_flags()
    elif adam_ds == "ADTTE" and rid == "ADTTE_OS":
        code = gen_adtte_os()
    elif adam_ds == "ADTTE" and rid == "ADTTE_PFS":
        code = gen_adtte_pfs()
    else:
        code = "# TODO: Add rule-specific scaffold\npass\n"

    return {
        "adam_ds": adam_ds,
        "description": rule.get("desc", ""),
        "sources": rule.get("sources", []),
        "pseudocode": rule.get("pseudo", []),
        "python_scaffold": code
    }