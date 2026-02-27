import re
import json
from collections import deque, defaultdict

TTL_PATH = "sdformat_model.ttl"
HTML_OUT = "ontology_graph.html"


def parse_ttl(path):
    classes = set()
    obj_props = []
    dt_props = []
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i].strip()
        m_class = re.match(r"^:([A-Za-z0-9_]+)\s+rdf:type\s+owl:Class\b", line)
        m_obj = re.match(r"^:([A-Za-z0-9_]+)\s+rdf:type\s+owl:ObjectProperty\b", line)
        m_dt = re.match(r"^:([A-Za-z0-9_]+)\s+rdf:type\s+owl:DatatypeProperty\b", line)
        if m_class:
            classes.add(m_class.group(1))
            while i < n and not lines[i].strip().endswith("."):
                i += 1
        elif m_obj:
            name = m_obj.group(1)
            dom = None
            ran = None
            while True:
                i += 1
                if i >= n:
                    break
                l2 = lines[i].strip()
                md = re.search(r"rdfs:domain\s+:(\w+)", l2)
                mr = re.search(r"rdfs:range\s+:(\w+)", l2)
                if md:
                    dom = md.group(1)
                if mr:
                    ran = mr.group(1)
                if l2.endswith("."):
                    break
            if dom and ran:
                obj_props.append({"name": name, "domain": dom, "range": ran})
        elif m_dt:
            name = m_dt.group(1)
            dom = None
            ran = None
            while True:
                i += 1
                if i >= n:
                    break
                l2 = lines[i].strip()
                md = re.search(r"rdfs:domain\s+:(\w+)", l2)
                mr = re.search(r"rdfs:range\s+([a-zA-Z0-9:_#]+)", l2)
                if md:
                    dom = md.group(1)
                if mr:
                    ran = mr.group(1)
                if l2.endswith("."):
                    break
            if dom and ran:
                dt_props.append({"name": name, "domain": dom, "range": ran})
        i += 1
    return classes, obj_props, dt_props


def build_layers(classes, obj_props):
    adj = defaultdict(list)
    indeg = defaultdict(int)
    for c in classes:
        adj[c] = adj[c]
        indeg[c] = indeg[c]
    for e in obj_props:
        d = e["domain"]
        r = e["range"]
        if d in classes and r in classes:
            adj[d].append(r)
            indeg[r] += 1
    roots = []
    if "Model" in classes:
        roots = ["Model"]
    else:
        roots = [c for c in classes if indeg[c] == 0]
        if not roots and classes:
            roots = [sorted(classes)[0]]
    layer = {}
    q = deque()
    for r in roots:
        layer[r] = 0
        q.append(r)
    while q:
        u = q.popleft()
        for v in adj[u]:
            if v not in layer:
                layer[v] = layer[u] + 1
                q.append(v)
    unassigned = [c for c in classes if c not in layer]
    if unassigned:
        max_layer = max(layer.values()) if layer else 0
        for idx, c in enumerate(unassigned, 1):
            layer[c] = max_layer + idx
    layers = defaultdict(list)
    for c, d in layer.items():
        layers[d].append(c)
    ordered_layers = []
    for d in sorted(layers.keys()):
        ordered_layers.append(layers[d])
    return ordered_layers, layer


def compute_positions(ordered_layers):
    node_w = 160
    node_h = 40
    x_gap = 60
    y_gap = 120
    max_count = max(len(l) for l in ordered_layers)
    width = max_count * (node_w + x_gap) + x_gap
    height = len(ordered_layers) * (node_h + y_gap) + y_gap
    positions = {}
    for li, layer_nodes in enumerate(ordered_layers):
        count = len(layer_nodes)
        total_w = count * (node_w + x_gap)
        start_x = (width - total_w) / 2 + x_gap / 2
        y = y_gap + li * (node_h + y_gap)
        for idx, name in enumerate(layer_nodes):
            x = start_x + idx * (node_w + x_gap)
            positions[name] = (int(x), int(y))
    return positions, width, height, node_w, node_h


def make_html(classes, obj_props, dt_props, positions, width, height, node_w, node_h):
    nodes_svg = []
    edges_svg = []
    labels_svg = []
    for e in obj_props:
        d = e["domain"]
        r = e["range"]
        if d in positions and r in positions:
            x1, y1 = positions[d]
            x2, y2 = positions[r]
            x1c = x1 + node_w / 2
            y1c = y1 + node_h / 2
            x2c = x2 + node_w / 2
            y2c = y2 + node_h / 2
            edges_svg.append(f'<line x1="{x1c}" y1="{y1c}" x2="{x2c}" y2="{y2c}" class="edge" />')
            mx = (x1c + x2c) / 2
            my = (y1c + y2c) / 2 - 6
            labels_svg.append(f'<text x="{mx}" y="{my}" class="edge-label">{e["name"]}</text>')
    dt_map = defaultdict(list)
    for p in dt_props:
        dt_map[p["domain"]].append(p["name"])
    for name, (x, y) in positions.items():
        nodes_svg.append(f'<rect x="{x}" y="{y}" rx="6" ry="6" width="{node_w}" height="{node_h}" class="node" />')
        nodes_svg.append(f'<text x="{x + node_w/2}" y="{y + 26}" class="node-label">{name}</text>')
        attrs = dt_map.get(name, [])
        if attrs:
            sub = ", ".join(attrs[:6])
            if len(attrs) > 6:
                sub += " …"
            nodes_svg.append(f'<text x="{x + node_w/2}" y="{y + node_h + 16}" class="attr-label">{sub}</text>')
    svg = "\n".join(edges_svg + labels_svg + nodes_svg)
    html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8"/>
<title>SDFormat Model Ontology</title>
<style>
body {{ margin: 0; font-family: Segoe UI, Arial, sans-serif; }}
svg {{ background: #fff; }}
.node {{ fill: #f0f6ff; stroke: #4b7bec; stroke-width: 1.2; }}
.node-label {{ fill: #1f2d3d; font-size: 13px; text-anchor: middle; dominant-baseline: middle; }}
.attr-label {{ fill: #5a6b7b; font-size: 11px; text-anchor: middle; }}
.edge {{ stroke: #9aa6b2; stroke-width: 1; }}
.edge-label {{ fill: #2b3a42; font-size: 11px; text-anchor: middle; dominant-baseline: central; background: #fff; }}
.legend {{ position: fixed; top: 8px; right: 12px; background: rgba(255,255,255,0.9); border: 1px solid #ddd; padding: 8px 12px; border-radius: 6px; }}
</style>
</head>
<body>
<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">
{svg}
</svg>
<div class="legend">
<div><strong>节点</strong>: OWL Class</div>
<div><strong>连线</strong>: ObjectProperty</div>
<div><strong>下方文字</strong>: 属于该类的 DatatypeProperty 列表</div>
</div>
</body>
</html>"""
    with open(HTML_OUT, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    classes, obj_props, dt_props = parse_ttl(TTL_PATH)
    ordered_layers, layer_map = build_layers(classes, obj_props)
    positions, width, height, node_w, node_h = compute_positions(ordered_layers)
    make_html(classes, obj_props, dt_props, positions, width, height, node_w, node_h)
    print("Generated:", HTML_OUT)


if __name__ == "__main__":
    main()

