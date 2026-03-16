from pathlib import Path
import json

# SAFE: splice JSON via .replace("__DATA_JSON__", ...); avoid .format() with CSS/JS braces
D3_HTML_TEMPLATE = r"""<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>GraphRAG ADaM Knowledge Graph</title>
  <style>
    :root {
      --bg: #0b1020;
      --panel: #0f172a;
      --text: #ffffff;        /* brighter text */
      --muted: #d0d6e5;       /* brighter muted text */
      --edge: #64748b;
      --border: #1e293b;
      --badge: #1f2937;
    }
    html, body { height: 100%; }
    body {
      font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, "Noto Sans",
                   "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji", sans-serif;
      margin: 0; display: flex; height: 100vh; background: var(--bg); color: var(--text);
    }
    #left { flex: 1; display:flex; flex-direction:column; overflow:hidden; }
    #toolbar {
      display:flex; gap:10px; align-items:center;
      padding:10px 12px; border-bottom:1px solid var(--border); background: rgba(15,23,42,.6); backdrop-filter: blur(4px);
      flex-wrap: wrap;
    }
    #toolbar label { font-size: 12px; color: var(--muted); margin-right: 6px; }
    #toolbar input[type="range"] { width: 120px; }
    #viz { flex: 1; }
    #side { width: 460px; border-left: 1px solid var(--border); padding: 12px; overflow: auto; background: var(--panel); color: var(--text); }

    /* ********  LABEL COLOR FIX  ********
       We style both .node text and an explicit .graph-label class.
       This guarantees visibility even if external CSS interferes.
    */
    .node text,
    text.graph-label {
      pointer-events: none;
      font-size: var(--labelSize, 14px);
      fill: #ffffff;                         /* pure white labels */
      paint-order: stroke;
      stroke: rgba(0, 0, 0, 0.85);           /* dark halo for contrast */
      stroke-width: 3px;                      /* crisp but not blurry */
    }

    .badge { display:inline-block; padding:2px 6px; border-radius:6px; background: var(--badge); margin-right:6px; font-size:12px; color: var(--text); }
    .legend { display:flex; gap:12px; align-items:center; font-size:12px; color: var(--muted);}
    .legend .key { display:flex; gap:6px; align-items:center; }
    .legend .dot { width:10px; height:10px; border-radius:50%; display:inline-block; }
    .btn { background:#1f2937; color: var(--text); border:1px solid var(--border); padding:6px 10px; border-radius:6px; cursor:pointer; }
    .btn:hover { filter: brightness(1.2); }
    .sep { width:1px; height:22px; background:var(--border); margin:0 8px; }
    .scale { font-size:12px; color: var(--muted); min-width:64px; text-align:center; }
  </style>

  <!-- FIXED: Proper D3 import as a real script tag -->
  <script src="https://d3js.org/d3.v7.min.js"></script>
</head>
<body>
<div id="left">
  <div id="toolbar">
    <div class="legend">
      <div class="key"><span class="dot" style="background:#10b981"></span>ADaM var</div>
      <div class="key"><span class="dot" style="background:#60a5fa"></span>SDTM var</div>
      <div class="key"><span class="dot" style="background:#eab308"></span>Doc chunk</div>
    </div>
    <div class="sep"></div>
    <button id="zoomOut" class="btn">Zoom −</button>
    <button id="zoomIn" class="btn">Zoom +</button>
    <button id="zoomReset" class="btn">Reset (100%)</button>
    <span class="scale" id="scaleTxt">100%</span>
    <div class="sep"></div>
    <label>Link</label><input id="dist" type="range" min="40" max="200" value="90" />
    <label>Charge</label><input id="charge" type="range" min="-600" max="0" value="-180" />
    <label>Label</label><input id="label" type="range" min="10" max="20" value="14" />
    <div style="flex:1"></div>
    <button id="fit" class="btn">Fit to view</button>
    <button id="full" class="btn">Fullscreen</button>
  </div>
  <div id="viz"></div>
</div>
<div id="side"><h2 style="margin:8px 0 12px;">Details</h2><div id="details">Click an ADaM node</div></div>

<script>
const data = __DATA_JSON__;

// Compute initial drawing area (full height)
function getDims() { const side = 460; return { w: window.innerWidth - side, h: window.innerHeight - 52 }; }
let { w: width, h: height } = getDims();

const svg = d3.select("#viz").append("svg").attr("width", width).attr("height", height).style("background", "var(--bg)");
const g = svg.append("g"); // zoom/pan group

// D3 Zoom
const zoom = d3.zoom().scaleExtent([0.3, 5]).on("zoom", (event) => {
  g.attr("transform", event.transform);
  updateScaleText(event.transform.k);
});
svg.call(zoom).on("dblclick.zoom", null);

// UI scale output
const scaleTxt = document.getElementById("scaleTxt");
function updateScaleText(k) {
  const pct = Math.round((k || 1) * 100);
  scaleTxt.textContent = pct + "%";
}
updateScaleText(1);

// Visual styles
const nodeColor  = d => d.kind === "adam_var" ? "#10b981" : (d.kind === "sdtm_var" ? "#60a5fa" : "#eab308");
const nodeRadius = d => d.kind === "adam_var" ? 9 : (d.kind === "sdtm_var" ? 8 : 7);

// Data
const links = data.links.map(d => Object.create(d));
const nodes = data.nodes.map(d => Object.create(d));

// Forces
let linkDistance = 90, chargeStrength = -180, labelSize = 14;
document.documentElement.style.setProperty('--labelSize', labelSize + 'px');

const simulation = d3.forceSimulation(nodes)
  .force("link", d3.forceLink(links).id(d => d.id).distance(linkDistance).strength(0.35))
  .force("charge", d3.forceManyBody().strength(chargeStrength))
  .force("center", d3.forceCenter(width/2, height/2))
  .force("collision", d3.forceCollide().radius(d => nodeRadius(d) + 4));

const link = g.append("g").attr("stroke", "var(--edge)").attr("stroke-opacity", 0.9)
  .selectAll("line").data(links).join("line").attr("stroke-width", d => Math.sqrt(d.weight || 1));

const node = g.append("g").attr("stroke", "#0b1020").attr("stroke-width", 1.0)
  .selectAll("g").data(nodes).join("g")
  .attr("class","node")                        // ensure .node text selector applies
  .call(drag(simulation))
  .on("mouseover", function() { d3.select(this).select("circle").attr("stroke-width", 2.0).attr("stroke", "#94a3b8"); })
  .on("mouseout",  function() { d3.select(this).select("circle").attr("stroke-width", 1.0).attr("stroke", "#0b1020"); })
  .on("click", (_, d) => showDetails(d));

node.append("circle").attr("r", nodeRadius).attr("fill", nodeColor);

node.append("title").text(d => d.kind === "text_chunk" ? (d.header || "Text") : (d.name || d.id));

/* LABEL COLOR FIX: force label style inline + add a class for CSS fallback */
node.append("text")
  .attr("class","graph-label")
  .text(d => d.kind === "text_chunk" ? (d.header || "Section") : (d.name || d.id))
  .attr("x", 12)
  .attr("y", "0.35em")
  .attr("fill", "#ffffff")                         // bright white
  .style("paint-order", "stroke")
  .style("stroke", "rgba(0,0,0,0.85)")             // dark halo
  .style("stroke-width", "3px");                   // crisp halo

simulation.on("tick", () => {
  link.attr("x1", d => d.source.x).attr("y1", d => d.source.y).attr("x2", d => d.target.x).attr("y2", d => d.target.y);
  node.attr("transform", d => `translate(${d.x},${d.y})`);
});

function drag(simulation) {
  function dragstarted(event) { if (!event.active) simulation.alphaTarget(0.25).restart(); event.subject.fx = event.subject.x; event.subject.fy = event.subject.y; }
  function dragged(event) { event.subject.fx = event.x; event.subject.fy = event.y; }
  function dragended(event) { if (!event.active) simulation.alphaTarget(0); event.subject.fx = null; event.subject.fy = null; }
  return d3.drag().on("start", dragstarted).on("drag", dragged).on("end", dragended);
}

function showDetails(d) {
  const details = document.getElementById("details");
  details.innerHTML = "";
  const title = document.createElement("div");
  title.innerHTML = `<div class="badge">${d.kind}</div><h3 style="display:inline;margin-left:8px;">${d.name || d.id}</h3>`;
  details.appendChild(title);

  if (d.kind === "adam_var") {
    const nbrs = links.filter(l => l.source.id === d.id || l.target.id === d.id).map(l => l.source.id === d.id ? l.target : l.source);
    const ul = document.createElement("ul");
    nbrs.forEach(n => {
      const li = document.createElement("li");
      if (n.kind === "text_chunk") {
        const txt = (n.text || '').slice(0, 320).replaceAll('<','&lt;');
        li.innerHTML = `<b>${n.doc.toUpperCase()}</b>: ${n.header}<br/><small style="color:var(--muted)">${txt}...</small>`;
      } else {
        li.innerHTML = `<span style="color:var(--muted)">${n.kind}</span> → ${n.name || n.id}`;
      }
      ul.appendChild(li);
    });
    details.appendChild(ul);
  } else if (d.kind === "text_chunk") {
    const p = document.createElement("p");
    p.textContent = (d.text || '').slice(0, 1400);
    details.appendChild(p);
  }
}

// === Toolbar controls (kept same) ===
const distCtl = document.getElementById("dist");
const chargeCtl = document.getElementById("charge");
const labelCtl = document.getElementById("label");
const fitBtn = document.getElementById("fit");
const fullBtn = document.getElementById("full");
const zoomInBtn = document.getElementById("zoomIn");
const zoomOutBtn = document.getElementById("zoomOut");
const zoomResetBtn = document.getElementById("zoomReset");

distCtl.addEventListener("input", (e) => { simulation.force("link").distance(+e.target.value); simulation.alpha(0.8).restart(); });
chargeCtl.addEventListener("input", (e) => { simulation.force("charge").strength(+e.target.value); simulation.alpha(0.8).restart(); });
labelCtl.addEventListener("input", (e) => { document.documentElement.style.setProperty('--labelSize', (+e.target.value) + 'px'); });

fitBtn.addEventListener("click", () => {
  const bounds = g.node().getBBox();
  const fullWidth = width, fullHeight = height;
  const midX = bounds.x + bounds.width / 2, midY = bounds.y + bounds.height / 2;
  let scale = 0.85 / Math.max(bounds.width / fullWidth, bounds.height / fullHeight);
  scale = Math.max(0.3, Math.min(4.5, scale));
  const translate = [fullWidth / 2 - scale * midX, fullHeight / 2 - scale * midY];
  svg.transition().duration(600).call(zoom.transform, d3.zoomIdentity.translate(translate[0], translate[1]).scale(scale));
});

fullBtn.addEventListener("click", () => { if (!document.fullscreenElement) document.documentElement.requestFullscreen?.(); else document.exitFullscreen?.(); });
zoomInBtn.addEventListener("click", () => { svg.transition().duration(250).call(zoom.scaleBy, 1.2); });
zoomOutBtn.addEventListener("click", () => { svg.transition().duration(250).call(zoom.scaleBy, 1/1.2); });
zoomResetBtn.addEventListener("click", () => { svg.transition().duration(250).call(zoom.transform, d3.zoomIdentity); });

window.addEventListener("resize", () => {
  const dims = getDims(); width = dims.w; height = dims.h;
  svg.attr("width", width).attr("height", height);
  simulation.force("center", d3.forceCenter(width/2, height/2));
  simulation.alpha(0.3).restart();
});
</script>
</body></html>
"""

def write_d3_html(graph_json: dict, out_html: Path, embed_data=True, json_path=None):
    out_html.parent.mkdir(parents=True, exist_ok=True)
    if embed_data:
        data_json = json.dumps(graph_json)
    else:
        if json_path is None:
            json_path = out_html.parent / "graph.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(graph_json, f, ensure_ascii=False)
        data_json = f"await (await fetch('{json_path.name}')).json()"
    content = D3_HTML_TEMPLATE.replace("__DATA_JSON__", data_json)
    out_html.write_text(content, encoding="utf-8")
    return out_html