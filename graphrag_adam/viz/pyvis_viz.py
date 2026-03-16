
from pyvis.network import Network


def pyvis_graph(kg, out_html="graph.html"):
    data = kg.to_json()
    net = Network(height="800px", width="100%", bgcolor="#0b1020", font_color="#e5e7eb")
    for n in data["nodes"]:
        color = "#10b981" if n.get("kind")=="adam_var" else ("#60a5fa" if n.get("kind")=="sdtm_var" else "#eab308")
        net.add_node(n["id"], label=n.get("name") or n.get("header") or n["id"], title=n.get("text","")[:500], color=color)
    for e in data["links"]:
        net.add_edge(e["source"], e["target"], title=e.get("type",""))
    net.show(out_html)
    return out_html
