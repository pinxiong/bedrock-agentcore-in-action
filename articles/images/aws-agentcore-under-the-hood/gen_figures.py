#!/usr/bin/env python3
"""Generate all 7 figures for the AgentCore intro article as SVG, then convert to PNG."""
import os
import resvg_py

OUT = os.path.dirname(os.path.abspath(__file__))

# ---- shared palette (light theme, dark text) ----
C_BG       = "#FFFFFF"
C_TEXT     = "#1A1A2E"
C_TEXT_LT  = "#555555"
C_BLUE     = "#2E86DE"   # your code / you write
C_BLUE_BG  = "#D6EAF8"
C_GRAY     = "#95A5A6"   # CLI generates
C_GRAY_BG  = "#ECF0F1"
C_ORANGE   = "#FF8C00"   # AWS
C_ORANGE_BG= "#FFF3E0"
C_GREEN    = "#27AE60"   # success / live
C_GREEN_BG = "#D5F5E3"
C_RED      = "#E74C3C"   # failure / pitfall
C_RED_BG   = "#FADBD8"
C_PURPLE   = "#8E44AD"
C_PURPLE_BG= "#F4ECF7"
C_LINE     = "#BDC3C7"

def save_svg(svg: str, name: str) -> str:
    path = os.path.join(OUT, f"{name}.svg")
    with open(path, "w") as f:
        f.write(svg)
    return path

def to_png(svg_path: str, name: str, w: int = 1400):
    png_path = os.path.join(OUT, f"{name}.png")
    png_bytes = resvg_py.svg_to_bytes(
        svg_path=svg_path,
        width=w,
        background=C_BG,
    )
    with open(png_path, "wb") as f:
        f.write(png_bytes)
    return png_path

# ---- F1: Capability map (14 cells, only Runtime + Observability lit) ----
def fig1():
    caps = [
        ("Runtime", True), ("Memory", False), ("Gateway", False), ("Identity", False),
        ("Policy", False), ("Harness", False), ("Web Search", False),
        ("Browser", False), ("Code Interpreter", False), ("Observability", True),
        ("Evaluations", False), ("Optimization", False), ("Payments", False), ("Registry", False),
    ]
    cell_w, cell_h = 124, 100
    cols, rows = 5, 3
    grid_w = cols * cell_w + (cols - 1) * 10
    grid_h = rows * cell_h + (rows - 1) * 10
    ox = (680 - grid_w) // 2
    oy = 120
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 680 {oy + grid_h + 80}" width="680">']
    parts.append(f'<rect width="680" height="{oy + grid_h + 80}" fill="{C_BG}"/>')
    parts.append(f'<text x="340" y="55" text-anchor="middle" font-family="sans-serif" font-size="22" font-weight="700" fill="{C_TEXT}">AgentCore: 14 Capabilities</text>')
    parts.append(f'<text x="340" y="82" text-anchor="middle" font-family="sans-serif" font-size="13" fill="{C_TEXT_LT}">This article lights up 2 of 14 (shaded). The rest come in A1-A7.</text>')
    for i, (name, lit) in enumerate(caps):
        r, c = divmod(i, cols)
        x = ox + c * (cell_w + 10)
        y = oy + r * (cell_h + 10)
        if lit:
            fill, stroke, tcol = C_GREEN_BG, C_GREEN, C_GREEN
            badge = f'<rect x="{x+cell_w-42}" y="{y+8}" width="34" height="16" rx="3" fill="{C_GREEN}"/><text x="{x+cell_w-25}" y="{y+19}" text-anchor="middle" font-family="sans-serif" font-size="9" font-weight="700" fill="white">ON</text>'
        else:
            fill, stroke, tcol = C_GRAY_BG, C_LINE, C_TEXT_LT
            badge = ""
        parts.append(f'<rect x="{x}" y="{y}" width="{cell_w}" height="{cell_h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')
        parts.append(f'<text x="{x+cell_w//2}" y="{y+cell_h//2+5}" text-anchor="middle" font-family="sans-serif" font-size="12" font-weight="600" fill="{tcol}">{name}</text>')
        parts.append(badge)
    parts.append(f'<text x="340" y="{oy+grid_h+30}" text-anchor="middle" font-family="sans-serif" font-size="11" fill="{C_TEXT_LT}">Difficulty: D1 (Runtime) -> D5 (Registry). Each use case adds at least one new capability.</text>')
    parts.append('</svg>')
    svg = "\n".join(parts)
    return save_svg(svg, "F1-capability-map"), "F1-capability-map"

# ---- F2: Three-layer mental model ----
def fig2():
    h = 380
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 680 {h}" width="680">']
    parts.append(f'<rect width="680" height="{h}" fill="{C_BG}"/>')
    parts.append(f'<text x="340" y="38" text-anchor="middle" font-family="sans-serif" font-size="20" font-weight="700" fill="{C_TEXT}">Three Layers: One Direction</text>')
    layers = [
        (80, "Layer 1: Your code", "src/ - agent entrypoint, tools, model loading", C_BLUE, C_BLUE_BG),
        (170, "Layer 2: The contract", "agentcore.json + aws-targets.json - you write by hand", C_PURPLE, C_PURPLE_BG),
        (260, "Layer 3: The plumbing", "agentcore/cdk/ - CLI generates on every deploy", C_GRAY, C_GRAY_BG),
    ]
    for y, title, desc, color, bg in layers:
        parts.append(f'<rect x="80" y="{y}" width="520" height="70" rx="10" fill="{bg}" stroke="{color}" stroke-width="2"/>')
        parts.append(f'<text x="100" y="{y+28}" font-family="sans-serif" font-size="15" font-weight="700" fill="{color}">{title}</text>')
        parts.append(f'<text x="100" y="{y+50}" font-family="sans-serif" font-size="12" fill="{C_TEXT_LT}">{desc}</text>')
    parts.append(f'<text x="340" y="{h-20}" text-anchor="middle" font-family="sans-serif" font-size="12" font-style="italic" fill="{C_TEXT_LT}">Rule: declare in JSON. Everything generated is regenerable.</text>')
    parts.append('</svg>')
    svg = "\n".join(parts)
    return save_svg(svg, "F2-three-layers"), "F2-three-layers"

# ---- F3: Directory anatomy (hand-written vs CLI-generated) ----
def fig3():
    h = 480
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 680 {h}" width="680">']
    parts.append(f'<rect width="680" height="{h}" fill="{C_BG}"/>')
    parts.append(f'<text x="340" y="32" text-anchor="middle" font-family="sans-serif" font-size="19" font-weight="700" fill="{C_TEXT}">Project Directory: Two Colours</text>')
    parts.append(f'<rect x="470" y="14" width="12" height="12" rx="2" fill="{C_BLUE}"/><text x="488" y="25" font-family="sans-serif" font-size="10" fill="{C_TEXT_LT}">you write</text>')
    parts.append(f'<rect x="560" y="14" width="12" height="12" rx="2" fill="{C_GRAY}"/><text x="578" y="25" font-family="sans-serif" font-size="10" fill="{C_TEXT_LT}">CLI generates</text>')

    # tree entries: (indent, name, kind, is_last)
    entries = [
        (0, "01-first-agent/", "root", False),
        (1, "src/", "blue", False),
        (2, "main.py", "blue", False),
        (2, "model/load.py", "blue", False),
        (2, "model/sanitize.py", "blue", False),
        (2, "pyproject.toml", "blue", True),
        (1, "tests/", "blue", False),
        (2, "smoke.py", "blue", False),
        (2, "test_sanitize.py", "blue", True),
        (1, "README.md", "blue", False),
        (1, "article.md", "blue", True),
        (1, "agentcore/", "root", True),
        (2, "agentcore.json", "star", False),
        (2, "aws-targets.json", "star", False),
        (2, ".gitignore", "gear", False),
        (2, "cdk/", "gear", False),
        (2, ".cli/", "gear", False),
        (2, ".llm-context/", "gear", False),
        (2, ".cache/", "gear", True),
    ]
    y0 = 60
    lh = 20
    for i, (indent, name, kind, is_last) in enumerate(entries):
        y = y0 + i * lh
        prefix = "  " * indent + ("`- " if is_last else "|- ")
        if kind == "root":
            color, marker = C_TEXT, ""
        elif kind == "blue":
            color, marker = C_BLUE, " [you write]"
        elif kind == "star":
            color, marker = C_BLUE, " [you write]"
        elif kind == "gear":
            color, marker = C_GRAY, " [CLI generates]"
        else:
            color, marker = C_TEXT_LT, ""
        # color box
        if kind == "blue" or kind == "star":
            parts.append(f'<rect x="45" y="{y-2}" width="6" height="6" rx="1" fill="{C_BLUE}"/>')
        elif kind == "gear":
            parts.append(f'<rect x="45" y="{y-2}" width="6" height="6" rx="1" fill="{C_GRAY}"/>')
        parts.append(f'<text x="58" y="{y+8}" font-family="monospace" font-size="11" fill="{color}">{prefix}{name}</text>')
        if marker:
            parts.append(f'<text x="350" y="{y+8}" font-family="sans-serif" font-size="9" fill="{C_TEXT_LT}">{marker}</text>')

    parts.append(f'<text x="340" y="{h-18}" text-anchor="middle" font-family="sans-serif" font-size="11" font-style="italic" fill="{C_TEXT_LT}">You never edit gear files. The next command overwrites them.</text>')
    parts.append('</svg>')
    svg = "\n".join(parts)
    return save_svg(svg, "F3-directory-anatomy"), "F3-directory-anatomy"

# ---- F4: Six-step deploy pipeline ----
def fig4():
    h = 260
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 680 {h}" width="680">']
    parts.append(f'<rect width="680" height="{h}" fill="{C_BG}"/>')
    parts.append(f'<text x="340" y="32" text-anchor="middle" font-family="sans-serif" font-size="19" font-weight="700" fill="{C_TEXT}">Deploy: Six Steps to READY</text>')

    steps = [
        ("1", "Package", "zip src/ + deps\n41 MB asset", C_BLUE, C_BLUE_BG, "seconds"),
        ("2", "Synthesize", "CDK app reads JSON\nemits CFN template", C_PURPLE, C_PURPLE_BG, "~3s"),
        ("3", "Upload", "zip -> S3\n(bootstrapped bucket)", C_ORANGE, C_ORANGE_BG, "seconds"),
        ("4", "Create stack", "CloudFormation\n4 resources", C_ORANGE, C_ORANGE_BG, "~5min (cold)"),
        ("5", "Record state", "deployed-state.json\nARN + endpoint", C_GRAY, C_GRAY_BG, "instant"),
        ("6", "Print endpoint", "Runtime: READY", C_GREEN, C_GREEN_BG, "instant"),
    ]
    bw, bh = 88, 120
    gap = 12
    total_w = 6 * bw + 5 * gap
    ox = (680 - total_w) // 2
    oy = 70
    for i, (num, title, desc, color, bg, timing) in enumerate(steps):
        x = ox + i * (bw + gap)
        parts.append(f'<rect x="{x}" y="{oy}" width="{bw}" height="{bh}" rx="8" fill="{bg}" stroke="{color}" stroke-width="2"/>')
        parts.append(f'<circle cx="{x+bw//2}" cy="{oy+22}" r="14" fill="{color}"/><text x="{x+bw//2}" y="{oy+26}" text-anchor="middle" font-family="sans-serif" font-size="12" font-weight="700" fill="white">{num}</text>')
        parts.append(f'<text x="{x+bw//2}" y="{oy+52}" text-anchor="middle" font-family="sans-serif" font-size="11" font-weight="700" fill="{color}">{title}</text>')
        lines = desc.split("\n")
        for j, line in enumerate(lines):
            parts.append(f'<text x="{x+bw//2}" y="{oy+72+j*14}" text-anchor="middle" font-family="sans-serif" font-size="9" fill="{C_TEXT_LT}">{line}</text>')
        parts.append(f'<text x="{x+bw//2}" y="{oy+bh-8}" text-anchor="middle" font-family="sans-serif" font-size="9" font-style="italic" fill="{C_TEXT_LT}">{timing}</text>')
        if i < 5:
            ax = x + bw
            parts.append(f'<line x1="{ax+2}" y1="{oy+bh//2}" x2="{ax+gap-2}" y2="{oy+bh//2}" stroke="{C_LINE}" stroke-width="2" marker-end=""/>')

    parts.append(f'<text x="340" y="{oy+bh+30}" text-anchor="middle" font-family="sans-serif" font-size="12" fill="{C_TEXT_LT}">Cold deploy: 9 min 49 s  |  Code-only redeploy: 26 s</text>')
    parts.append(f'<text x="340" y="{oy+bh+52}" text-anchor="middle" font-family="sans-serif" font-size="11" font-style="italic" fill="{C_TEXT_LT}">Stack name = AgentCore-&lt;projectName&gt;-&lt;targetName&gt; (from JSON, never hardcoded)</text>')
    parts.append('</svg>')
    svg = "\n".join(parts)
    return save_svg(svg, "F4-deploy-pipeline"), "F4-deploy-pipeline"

# ---- F5: One surface, two hosts (Uvicorn vs microVM) ----
def fig5():
    h = 360
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 680 {h}" width="680">']
    parts.append(f'<rect width="680" height="{h}" fill="{C_BG}"/>')
    parts.append(f'<text x="340" y="32" text-anchor="middle" font-family="sans-serif" font-size="19" font-weight="700" fill="{C_TEXT}">One HTTP Surface, Two Hosts</text>')

    # shared contract box at top center
    parts.append(f'<rect x="180" y="55" width="320" height="50" rx="8" fill="{C_BLUE_BG}" stroke="{C_BLUE}" stroke-width="2"/>')
    parts.append(f'<text x="340" y="78" text-anchor="middle" font-family="sans-serif" font-size="13" font-weight="700" fill="{C_BLUE}">GET /ping  +  POST /invocations</text>')
    parts.append(f'<text x="340" y="96" text-anchor="middle" font-family="sans-serif" font-size="10" fill="{C_TEXT_LT}">Your code implements these two routes. Nothing else.</text>')

    # left: local
    parts.append(f'<rect x="40" y="140" width="280" height="140" rx="10" fill="{C_GRAY_BG}" stroke="{C_GRAY}" stroke-width="2"/>')
    parts.append(f'<text x="180" y="165" text-anchor="middle" font-family="sans-serif" font-size="13" font-weight="700" fill="{C_GRAY}">agentcore dev (local)</text>')
    parts.append(f'<text x="180" y="188" text-anchor="middle" font-family="sans-serif" font-size="11" fill="{C_TEXT_LT}">Uvicorn on localhost:8080</text>')
    parts.append(f'<text x="180" y="208" text-anchor="middle" font-family="sans-serif" font-size="11" fill="{C_TEXT_LT}">Hot reload on file save</text>')
    parts.append(f'<text x="180" y="228" text-anchor="middle" font-family="sans-serif" font-size="11" fill="{C_TEXT_LT}">Model calls -> Bedrock (cloud)</text>')
    parts.append(f'<text x="180" y="255" text-anchor="middle" font-family="sans-serif" font-size="10" font-style="italic" fill="{C_GREEN}">No deployment needed</text>')

    # right: cloud
    parts.append(f'<rect x="360" y="140" width="280" height="140" rx="10" fill="{C_ORANGE_BG}" stroke="{C_ORANGE}" stroke-width="2"/>')
    parts.append(f'<text x="500" y="165" text-anchor="middle" font-family="sans-serif" font-size="13" font-weight="700" fill="{C_ORANGE}">agentcore deploy (cloud)</text>')
    parts.append(f'<text x="500" y="188" text-anchor="middle" font-family="sans-serif" font-size="11" fill="{C_TEXT_LT}">Serverless microVM per session</text>')
    parts.append(f'<text x="500" y="208" text-anchor="middle" font-family="sans-serif" font-size="11" fill="{C_TEXT_LT}">IAM role + endpoint + traces</text>')
    parts.append(f'<text x="500" y="228" text-anchor="middle" font-family="sans-serif" font-size="11" fill="{C_TEXT_LT}">Scaling handled by platform</text>')
    parts.append(f'<text x="500" y="255" text-anchor="middle" font-family="sans-serif" font-size="10" font-style="italic" fill="{C_GREEN}">Same code, same routes</text>')

    # connecting lines
    parts.append(f'<line x1="340" y1="105" x2="180" y2="140" stroke="{C_LINE}" stroke-width="1.5" stroke-dasharray="4,3"/>')
    parts.append(f'<line x1="340" y1="105" x2="500" y2="140" stroke="{C_LINE}" stroke-width="1.5" stroke-dasharray="4,3"/>')

    parts.append(f'<text x="340" y="{h-15}" text-anchor="middle" font-family="sans-serif" font-size="12" font-style="italic" fill="{C_TEXT_LT}">No shim, no adapter, no second interface to drift.</text>')
    parts.append('</svg>')
    svg = "\n".join(parts)
    return save_svg(svg, "F5-one-surface"), "F5-one-surface"

# ---- F6: X-Ray span tree ----
def fig6():
    h = 330
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 680 {h}" width="680">']
    parts.append(f'<rect width="680" height="{h}" fill="{C_BG}"/>')
    parts.append(f'<text x="340" y="32" text-anchor="middle" font-family="sans-serif" font-size="19" font-weight="700" fill="{C_TEXT}">X-Ray Trace: One Tool-Using Invoke</text>')

    # tree structure
    nodes = [
        (340, 65, "invoke_agent  Strands Agents", C_BLUE, C_BLUE_BG, 'tools=["add_numbers"], 934 tokens'),
        (210, 130, "execute_event_loop_cycle", C_PURPLE, C_PURPLE_BG, "cycle 1"),
        (520, 130, "execute_event_loop_cycle", C_PURPLE, C_PURPLE_BG, "cycle 2"),
        (130, 195, "execute_tool  add_numbers", C_GREEN, C_GREEN_BG, "TOOL, status=success"),
        (360, 195, "chat  deepseek.v3.2", C_ORANGE, C_ORANGE_BG, "finish=tool_use"),
        (570, 195, "chat  deepseek.v3.2", C_ORANGE, C_ORANGE_BG, "finish=end_turn"),
    ]
    # edges
    edges = [(0,1), (0,2), (1,3), (1,4), (2,5)]
    for a, b in edges:
        x1, y1 = nodes[a][0], nodes[a][1]+22
        x2, y2 = nodes[b][0], nodes[b][1]-22
        parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{C_LINE}" stroke-width="1.5"/>')

    for x, y, label, color, bg, meta in nodes:
        w = 200
        parts.append(f'<rect x="{x-w//2}" y="{y}" width="{w}" height="44" rx="6" fill="{bg}" stroke="{color}" stroke-width="1.5"/>')
        parts.append(f'<text x="{x}" y="{y+17}" text-anchor="middle" font-family="sans-serif" font-size="10.5" font-weight="700" fill="{color}">{label}</text>')
        parts.append(f'<text x="{x}" y="{y+34}" text-anchor="middle" font-family="sans-serif" font-size="9" fill="{C_TEXT_LT}">{meta}</text>')

    parts.append(f'<text x="340" y="{h-42}" text-anchor="middle" font-family="sans-serif" font-size="11" fill="{C_TEXT_LT}">One cycle per model round trip. The tool call is its own span inside the cycle.</text>')
    parts.append(f'<text x="340" y="{h-20}" text-anchor="middle" font-family="sans-serif" font-size="10" font-style="italic" fill="{C_RED}">Caveat: spans need ~10 min to become queryable. Local dev has no tool span.</text>')
    parts.append('</svg>')
    svg = "\n".join(parts)
    return save_svg(svg, "F6-span-tree"), "F6-span-tree"

# ---- F7: Series roadmap (7 articles, difficulty ladder) ----
def fig7():
    h = 420
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 680 {h}" width="680">']
    parts.append(f'<rect width="680" height="{h}" fill="{C_BG}"/>')
    parts.append(f'<text x="340" y="32" text-anchor="middle" font-family="sans-serif" font-size="19" font-weight="700" fill="{C_TEXT}">Series Roadmap: 7 Use Cases, Rising Difficulty</text>')

    articles = [
        ("A1", "First Agent", "D1", "runtime, observability", C_GREEN),
        ("A2", "Memory", "D2", "memory", C_GREEN),
        ("A3", "Gateway + Identity", "D3", "gateway, identity", "#2ECC71"),
        ("A4", "Policy", "D3", "policy", "#2ECC71"),
        ("A5", "Research Agent", "D4", "web search, browser,\ncode interpreter, harness", C_ORANGE),
        ("A6", "Quality Loop", "D4", "evaluations,\noptimization", C_ORANGE),
        ("A7", "Multi-Agent + Registry", "D5", "multi-agent, registry", C_RED),
    ]

    bw = 80
    gap = 12
    total_w = 7 * bw + 6 * gap
    ox = (680 - total_w) // 2
    oy = 80

    # staircase baseline
    for i, (aid, title, diff, caps, color) in enumerate(articles):
        x = ox + i * (bw + gap)
        h_bar = 60 + i * 28
        parts.append(f'<rect x="{x}" y="{oy + 200 - h_bar}" width="{bw}" height="{h_bar}" rx="6" fill="{color}" opacity="0.15" stroke="{color}" stroke-width="1.5"/>')
        parts.append(f'<text x="{x+bw//2}" y="{oy+200-h_bar-8}" text-anchor="middle" font-family="sans-serif" font-size="13" font-weight="700" fill="{color}">{aid}</text>')
        parts.append(f'<text x="{x+bw//2}" y="{oy+200-h_bar+18}" text-anchor="middle" font-family="sans-serif" font-size="9" font-weight="600" fill="{color}">{diff}</text>')
        # title below bar
        parts.append(f'<text x="{x+bw//2}" y="{oy+218}" text-anchor="middle" font-family="sans-serif" font-size="9" font-weight="600" fill="{C_TEXT}">{title}</text>')
        # caps
        cap_lines = caps.split("\n")
        for j, cl in enumerate(cap_lines):
            parts.append(f'<text x="{x+bw//2}" y="{oy+232+j*11}" text-anchor="middle" font-family="sans-serif" font-size="7" fill="{C_TEXT_LT}">{cl}</text>')

    parts.append(f'<text x="340" y="{h-20}" text-anchor="middle" font-family="sans-serif" font-size="11" font-style="italic" fill="{C_TEXT_LT}">Each use case deploys standalone. Each article follows the same pattern: real deployment, measured outputs.</text>')
    parts.append('</svg>')
    svg = "\n".join(parts)
    return save_svg(svg, "F7-series-roadmap"), "F7-series-roadmap"

# ---- generate all ----
figs = [fig1(), fig2(), fig3(), fig4(), fig5(), fig6(), fig7()]

for svg_path, name in figs:
    png_path = to_png(svg_path, name, w=1400)
    print(f"  {name}: {os.path.basename(svg_path)} + {os.path.basename(png_path)}")

print(f"\nDone. {len(figs)} figures generated in {OUT}")
