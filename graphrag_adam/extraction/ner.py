
from typing import Dict, Any
from .patterns import VARLIKE, ENDPOINT_HINTS, ADAM_VAR_SET


def extract_entities(chunk: Dict) -> Dict[str, Any]:
    """
    Extract candidate variables and endpoint phrases from chunk text
    """
    text = chunk.get("text", "")
    vars_ = set(m.group(0) for m in VARLIKE.finditer(text))
    vars_adam = [v for v in vars_ if v in ADAM_VAR_SET]
    hints = [h for h in ENDPOINT_HINTS if h.lower() in text.lower()]
    return {
        "adam_vars": vars_adam,
        "vars_allcaps": list(vars_),
        "endpoint_hints": hints
    }
