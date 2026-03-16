
import json
from pathlib import Path


def export_graph_json(kg, out_path: Path):
    data = kg.to_json()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return out_path
