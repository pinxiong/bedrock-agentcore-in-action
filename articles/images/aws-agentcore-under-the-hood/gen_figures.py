#!/usr/bin/env python3
"""Generate all 8 figures for the AgentCore intro article (A0).

Design system (v2, 2026-10-15):
- white background (publishing platforms are white-bg), vivid accents
- every figure: kicker pill + bold title + subtitle header
- shadowed rounded cards, gradient fills, colored chips, number badges
- 8 figures with 8 DIFFERENT layout styles so the set never feels monotone:
  F0 command journey ribbon | F1 color-grouped grid | F2 stacked gradient layers
  F3 tree card + legend chips | F4 pipeline + timing bars | F5 vs-comparison
  F6 span tree + side annotations | F7 difficulty staircase
- PNGs are reused verbatim in the English article, the Chinese article and the PPT.
"""
import os
import resvg_py

OUT = os.path.dirname(os.path.abspath(__file__))

# ---- palette (white bg, vivid accents) ----
INK    = "#0F172A"
SLATE  = "#475569"
MUTED  = "#64748B"
LINE   = "#CBD5E1"

BLUE    = "#2563EB"; BLUE_D  = "#1D4ED8"; BLUE_B  = "#DBEAFE"
PURPLE  = "#7C3AED"; PURPLE_B = "#EDE9FE"
ORANGE  = "#EA580C"; ORANGE_O = "#FF9900"; ORANGE_B = "#FFEDD5"
GREEN   = "#059669"; GREEN_B  = "#D1FAE5"
RED     = "#E11D48"; RED_B    = "#FFE4E6"
TEAL    = "#0D9488"; TEAL_B   = "#CCFBF1"
YELLOW  = "#D97706"; YELLOW_B = "#FEF3C7"
PINK    = "#DB2777"; PINK_B   = "#FCE7F3"
INDIGO  = "#4F46E5"; INDIGO_B = "#E0E7FF"
SLATE_B = "#F1F5F9"

SANS = "'Helvetica Neue', 'PingFang SC', Arial, sans-serif"
MONO = "'SF Mono', Menlo, Consolas, monospace"

DEFS = f'''
<defs>
  <filter id="ds" x="-30%" y="-30%" width="160%" height="160%">
    <feDropShadow dx="0" dy="2.5" stdDeviation="4" flood-color="{INK}" flood-opacity="0.15"/>
  </filter>
  <linearGradient id="g-blue" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#3B82F6"/><stop offset="1" stop-color="{BLUE_D}"/>
  </linearGradient>
  <linearGradient id="g-purple" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#8B5CF6"/><stop offset="1" stop-color="#6D28D9"/>
  </linearGradient>
  <linearGradient id="g-orange" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#FF9900"/><stop offset="1" stop-color="{ORANGE}"/>
  </linearGradient>
  <linearGradient id="g-green" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#10B981"/><stop offset="1" stop-color="#047857"/>
  </linearGradient>
  <linearGradient id="g-red" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#F43F5E"/><stop offset="1" stop-color="#BE123C"/>
  </linearGradient>
  <linearGradient id="g-teal" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#14B8A6"/><stop offset="1" stop-color="#0F766E"/>
  </linearGradient>
  <linearGradient id="g-ink" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#0F172A"/><stop offset="1" stop-color="#1E3A8A"/>
  </linearGradient>
  <linearGradient id="g-ribbon" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{BLUE}"/><stop offset="0.35" stop-color="{TEAL}"/>
    <stop offset="0.65" stop-color="{ORANGE}"/><stop offset="1" stop-color="{RED}"/>
  </linearGradient>
</defs>
'''

def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def save_svg(svg: str, name: str) -> str:
    path = os.path.join(OUT, f"{name}.svg")
    with open(path, "w") as f:
        f.write(svg)
    return path

def to_png(svg_path: str, name: str, w: int = 1440):
    png_path = os.path.join(OUT, f"{name}.png")
    png_bytes = resvg_py.svg_to_bytes(svg_path=svg_path, width=w, background="#FFFFFF")
    with open(png_path, "wb") as f:
        f.write(png_bytes)
    return png_path

def header(kicker, title, sub, accent, W=680):
    """Standard header: kicker pill + bold title + subtitle. Returns (parts, content_y)."""
    pill_w = 20 + 7.8 * len(kicker)
    p = [
        f'<rect x="40" y="24" width="{pill_w:.0f}" height="21" rx="10.5" fill="{accent}"/>',
        f'<text x="{40 + pill_w/2:.0f}" y="38.5" text-anchor="middle" font-family="{SANS}" font-size="10" font-weight="700" letter-spacing="1.2" fill="white">{esc(kicker.upper())}</text>',
        f'<text x="40" y="80" font-family="{SANS}" font-size="23" font-weight="800" fill="{INK}">{esc(title)}</text>',
    ]
    if sub:
        p.append(f'<text x="40" y="102" font-family="{SANS}" font-size="12.5" fill="{SLATE}">{esc(sub)}</text>')
    return p, 126

def card(x, y, w, h, fill="white", stroke=LINE, sw=1.5, rx=12, shadow=True):
    sh = ' filter="url(#ds)"' if shadow else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{sh}/>'

def chip(x, y, text, color, bg=None, size=9.5, pad=8, h=17, bold=True, text_color=None):
    w = pad * 2 + size * 0.62 * len(text)
    tc = text_color or color
    return (f'<rect x="{x}" y="{y}" width="{w:.0f}" height="{h}" rx="{h/2}" fill="{bg or color}" opacity="{1 if bg else 1}"/>'
            f'<text x="{x + w/2:.0f}" y="{y + h/2 + size*0.36:.1f}" text-anchor="middle" font-family="{SANS}" font-size="{size}" font-weight="{700 if bold else 500}" fill="{tc}">{esc(text)}</text>', w)

# =====================================================================
# F0: command journey (NEW - the whole lifecycle in six commands)
# =====================================================================
def fig0():
    W, H = 680, 372
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}">']
    parts.append(f'<rect width="{W}" height="{H}" fill="white"/>')
    parts.append(DEFS)
    hp, y = header("command map", "The Whole Lifecycle in Six Commands",
                   "Everything the AgentCore CLI does, end to end. No --region flag anywhere.", INDIGO)
    parts += hp

    stations = [
        ("1", "create",  "scaffold the project", "agentcore.json: every", "resource array empty", "g-blue",   BLUE),
        ("2", "dev",     "run it locally",       "Uvicorn on :8080,",     "hot reload",           "g-teal",   TEAL),
        ("3", "deploy",  "ship it to AWS",       "JSON in, 4 CFN",        "resources out",        "g-orange", ORANGE),
        ("4", "invoke",  "call the runtime",     "SSE stream, native",    "toolUse blocks",       "g-green",  GREEN),
        ("5", "traces",  "read what happened",   "spans land in X-Ray",   "(~10 min delay)",      "g-purple", PURPLE),
        ("6", "remove",  "tear it all down",     "stack converges",       "to empty",             "g-red",    RED),
    ]
    st_w, gap = 100, 8
    ox = (W - (6 * st_w + 5 * gap)) // 2
    ribbon_y = y + 56
    # gradient ribbon behind stations
    parts.append(f'<rect x="{ox+30}" y="{ribbon_y-4}" width="{6*st_w+5*gap-60}" height="8" rx="4" fill="url(#g-ribbon)" opacity="0.25"/>')
    parts.append(f'<rect x="{ox+30}" y="{ribbon_y-2}" width="{6*st_w+5*gap-60}" height="4" rx="2" fill="url(#g-ribbon)"/>')
    for i, (num, cmd, d0, l1, l2, grad, color) in enumerate(stations):
        cx = ox + i * (st_w + gap) + st_w // 2
        # number circle
        parts.append(f'<circle cx="{cx}" cy="{ribbon_y}" r="17" fill="url(#{grad})" filter="url(#ds)"/>')
        parts.append(f'<text x="{cx}" y="{ribbon_y+5}" text-anchor="middle" font-family="{SANS}" font-size="13" font-weight="800" fill="white">{num}</text>')
        # command chip: subcommand only, with a small "agentcore" caption
        chip_y = ribbon_y + 34
        parts.append(f'<text x="{cx}" y="{chip_y-5}" text-anchor="middle" font-family="{SANS}" font-size="8.5" font-weight="600" fill="{MUTED}">agentcore</text>')
        cw = 16 + 8.6 * len(cmd)
        parts.append(f'<rect x="{cx-cw/2:.0f}" y="{chip_y}" width="{cw:.0f}" height="21" rx="6" fill="white" stroke="{color}" stroke-width="1.5"/>')
        parts.append(f'<text x="{cx}" y="{chip_y+15}" text-anchor="middle" font-family="{MONO}" font-size="12" font-weight="700" fill="{color}">{cmd}</text>')
        # description
        parts.append(f'<text x="{cx}" y="{chip_y+42}" text-anchor="middle" font-family="{SANS}" font-size="10.5" font-weight="600" fill="{INK}">{esc(d0)}</text>')
        parts.append(f'<text x="{cx}" y="{chip_y+56}" text-anchor="middle" font-family="{SANS}" font-size="9.5" fill="{MUTED}">{esc(l1)}</text>')
        parts.append(f'<text x="{cx}" y="{chip_y+68}" text-anchor="middle" font-family="{SANS}" font-size="9.5" fill="{MUTED}">{esc(l2)}</text>')

    ny = chip_y + 96
    # bottom banner
    bw = 6 * st_w + 5 * gap
    parts.append(card(ox, ny, bw, 44, fill=SLATE_B, stroke=LINE, rx=10))
    parts.append(f'<text x="{ox+bw/2}" y="{ny+19}" text-anchor="middle" font-family="{SANS}" font-size="11" font-weight="700" fill="{INK}">Where does it deploy? aws-targets.json decides.</text>')
    parts.append(f'<text x="{ox+bw/2}" y="{ny+35}" text-anchor="middle" font-family="{SANS}" font-size="10" fill="{SLATE}">The first deploy calls STS, learns your account and writes the target back into the file.</text>')
    parts.append('</svg>')
    svg = "\n".join(parts)
    return save_svg(svg, "F0-command-map"), "F0-command-map"

# =====================================================================
# F1: capability map (color-grouped grid, 2 lit)
# =====================================================================
def fig1():
    W = 680
    caps = [
        ("Runtime", "lit"), ("Memory", PURPLE), ("Gateway", BLUE), ("Identity", BLUE), ("Policy", BLUE),
        ("Harness", TEAL), ("Web Search", TEAL), ("Browser", TEAL), ("Code Interpreter", TEAL), ("Observability", "lit"),
        ("Evaluations", YELLOW), ("Optimization", YELLOW), ("Payments", PINK), ("Registry", PINK),
    ]
    cell_w, cell_h, gap = 120, 88, 10
    cols = 5
    grid_w = cols * cell_w + (cols - 1) * gap
    ox = (W - grid_w) // 2
    hp, oy = header("what it is", "AgentCore: 14 Managed Capabilities",
                    "This article lights up 2 of 14. The rest arrive one use case at a time.", GREEN)
    H = oy + 3 * (cell_h + gap) + 118
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}">',
             f'<rect width="{W}" height="{H}" fill="white"/>', DEFS]
    parts += hp
    for i, (name, kind) in enumerate(caps):
        r, c = divmod(i, cols)
        x = ox + c * (cell_w + gap)
        y = oy + r * (cell_h + gap)
        if kind == "lit":
            parts.append(f'<rect x="{x-3}" y="{y-3}" width="{cell_w+6}" height="{cell_h+6}" rx="14" fill="{GREEN}" opacity="0.18"/>')
            parts.append(card(x, y, cell_w, cell_h, fill=GREEN_B, stroke=GREEN, sw=2.5, rx=10))
            parts.append(f'<text x="{x+cell_w/2}" y="{y+cell_h/2-2}" text-anchor="middle" font-family="{SANS}" font-size="13" font-weight="800" fill="#047857">{esc(name)}</text>')
            bw_badge = 12 + 5.6 * len("THIS ARTICLE")
            parts.append(f'<rect x="{x+cell_w/2-bw_badge/2:.0f}" y="{y+cell_h/2+8}" width="{bw_badge:.0f}" height="15" rx="7.5" fill="{GREEN}"/>')
            parts.append(f'<text x="{x+cell_w/2}" y="{y+cell_h/2+18.5}" text-anchor="middle" font-family="{SANS}" font-size="8" font-weight="800" letter-spacing="0.6" fill="white">THIS ARTICLE</text>')
        else:
            parts.append(card(x, y, cell_w, cell_h, fill="white", stroke=kind, sw=1.8, rx=10))
            parts.append(f'<rect x="{x}" y="{y}" width="{cell_w}" height="5" rx="2.5" fill="{kind}" opacity="0.9"/>')
            fs = 12 if len(name) <= 12 else 10.5
            parts.append(f'<text x="{x+cell_w/2}" y="{y+cell_h/2+4}" text-anchor="middle" font-family="{SANS}" font-size="{fs}" font-weight="700" fill="{kind}">{esc(name)}</text>')
    # legend (two rows of three)
    ly = oy + 3 * (cell_h + gap) + 24
    legend = [("Runtime + Observability", GREEN), ("Access: gateway, identity, policy", BLUE),
              ("Tools: search, browser, code, harness", TEAL), ("Memory", PURPLE),
              ("Quality: evaluations, optimization", YELLOW), ("Business: payments, registry", PINK)]
    for k, (label, color) in enumerate(legend):
        row, col = divmod(k, 3)
        lx = 70 + col * 200
        lyk = ly + row * 20
        parts.append(f'<circle cx="{lx+5}" cy="{lyk-4}" r="4.5" fill="{color}"/>')
        parts.append(f'<text x="{lx+15}" y="{lyk}" font-family="{SANS}" font-size="10" fill="{SLATE}">{esc(label)}</text>')
    parts.append(f'<text x="{W/2}" y="{ly+52}" text-anchor="middle" font-family="{SANS}" font-size="10.5" font-style="italic" fill="{MUTED}">Difficulty rises D1 (first agent) to D5 (multi-agent + registry). Each use case adds at least one new capability.</text>')
    parts.append('</svg>')
    svg = "\n".join(parts)
    return save_svg(svg, "F1-capability-map"), "F1-capability-map"

# =====================================================================
# F2: three layers (stacked gradient cards + rule banner)
# =====================================================================
def fig2():
    W, H = 680, 496
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}">',
             f'<rect width="{W}" height="{H}" fill="white"/>', DEFS]
    hp, y = header("mental model", "Three Layers, One Direction",
                   "You write code and JSON. The CLI generates everything else. AWS runs the stack.", PURPLE)
    parts += hp
    layers = [
        ("1", "YOUR CODE", "src/ - agent entrypoint, tools, model loading", "YOU MAINTAIN", BLUE, BLUE_B, "g-blue"),
        ("2", "THE CONTRACT", "agentcore.json + aws-targets.json - written by hand", "YOU MAINTAIN", PURPLE, PURPLE_B, "g-purple"),
        ("3", "THE PLUMBING", "agentcore/cdk/ - a CDK project regenerated on every deploy", "CLI REGENERATES", ORANGE, ORANGE_B, "g-orange"),
    ]
    bx, bw, bh, bg_ = 60, 470, 74, 20
    for i, (num, title, desc, own, color, light, grad) in enumerate(layers):
        ly = y + i * (bh + bg_)
        parts.append(card(bx, ly, bw, bh, fill=light, stroke=color, sw=2, rx=12))
        parts.append(f'<circle cx="{bx+34}" cy="{ly+bh/2}" r="18" fill="url(#{grad})"/>')
        parts.append(f'<text x="{bx+34}" y="{ly+bh/2+5}" text-anchor="middle" font-family="{SANS}" font-size="14" font-weight="800" fill="white">{num}</text>')
        parts.append(f'<text x="{bx+66}" y="{ly+30}" font-family="{SANS}" font-size="14.5" font-weight="800" fill="{color}">{esc(title)}</text>')
        parts.append(f'<text x="{bx+66}" y="{ly+52}" font-family="{SANS}" font-size="11" fill="{SLATE}">{esc(desc)}</text>')
        # owner chip on the right
        cw = 8 * 0.62 * len(own) + 16
        parts.append(f'<rect x="{bx+bw-cw-12:.0f}" y="{ly+12}" width="{cw:.0f}" height="16" rx="8" fill="white" stroke="{color}" stroke-width="1.2"/>')
        parts.append(f'<text x="{bx+bw-cw/2-12:.0f}" y="{ly+23.5}" text-anchor="middle" font-family="{SANS}" font-size="8" font-weight="700" letter-spacing="0.5" fill="{color}">{own}</text>')
    # downward deploy arrow on the right
    ax = bx + bw + 40
    arrow_top = y + 8
    arrow_bot = y + 3 * (bh + bg_) - bg_ - 14
    parts.append(f'<line x1="{ax}" y1="{arrow_top}" x2="{ax}" y2="{arrow_bot}" stroke="{ORANGE}" stroke-width="3"/>')
    parts.append(f'<path d="M {ax-7} {arrow_bot-12} L {ax} {arrow_bot} L {ax+7} {arrow_bot-12} Z" fill="{ORANGE}"/>')
    y_mid = (arrow_top + arrow_bot) / 2
    parts.append(f'<text x="{ax+12}" y="{y_mid - 3:.0f}" font-family="{MONO}" font-size="10.5" font-weight="700" fill="{ORANGE}">agentcore</text>')
    parts.append(f'<text x="{ax+12}" y="{y_mid + 11:.0f}" font-family="{MONO}" font-size="10.5" font-weight="700" fill="{ORANGE}">deploy</text>')
    # rule banner
    ry = y + 3 * (bh + bg_) + 6
    parts.append(f'<rect x="60" y="{ry}" width="560" height="52" rx="12" fill="url(#g-ink)" filter="url(#ds)"/>')
    parts.append(f'<text x="340" y="{ry+22}" text-anchor="middle" font-family="{SANS}" font-size="14" font-weight="800" fill="white">Declare in JSON. Everything generated is regenerable.</text>')
    parts.append(f'<text x="340" y="{ry+41}" text-anchor="middle" font-family="{SANS}" font-size="10.5" fill="#93C5FD">The rest of this article is that one rule, traced end to end.</text>')
    parts.append('</svg>')
    svg = "\n".join(parts)
    return save_svg(svg, "F2-three-layers"), "F2-three-layers"

# =====================================================================
# F3: project anatomy (one tree card + ownership legend chips)
# =====================================================================
def fig3():
    W, H = 680, 588
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}">',
             f'<rect width="{W}" height="{H}" fill="white"/>', DEFS]
    hp, y = header("project anatomy", "One Project, Two Kinds of Files",
                   "Blue squares = you write it once. Gray squares = the CLI generates and overwrites it.", BLUE)
    parts += hp
    cx, cw, ch = 40, 600, 380
    parts.append(card(cx, y, cw, ch, fill="white", stroke=LINE, sw=1.5))
    # header strip
    parts.append(f'<path d="M {cx} {y+36} L {cx} {y+14} Q {cx} {y} {cx+14} {y} L {cx+cw-14} {y} Q {cx+cw} {y} {cx+cw} {y+14} L {cx+cw} {y+36} Z" fill="{SLATE_B}"/>')
    # legend chips inside header
    c1, w1 = chip(cx + 16, y + 9, "you write", BLUE, bg=BLUE_B, size=9.5, pad=9)
    parts.append(c1)
    c2, w2 = chip(cx + 16 + w1 + 10, y + 9, "CLI generates", SLATE, bg="#E2E8F0", size=9.5, pad=9, text_color=SLATE)
    parts.append(c2)
    entries = [
        (0, "01-first-agent/", "", INK, False),
        (1, "src/", "", INK, False),
        (2, "main.py", "the entrypoint", BLUE, True),
        (2, "model/load.py", "model selection", BLUE, True),
        (2, "model/sanitize.py", "stream filter", BLUE, True),
        (1, "tests/smoke.py", "capability assertions", BLUE, True),
        (1, "README.md", "operational doc", BLUE, True),
        (1, "agentcore/", "", INK, False),
        (2, "agentcore.json", "THE CONTRACT", BLUE, True),
        (2, "aws-targets.json", "WHERE TO DEPLOY", BLUE, True),
        (2, ".gitignore", "", SLATE, True),
        (2, "cdk/", "vendored CDK app", SLATE, False),
        (2, ".cli/", "logs, traces, state", SLATE, False),
        (2, ".llm-context/ + .cache/", "schema ref, build staging", SLATE, False),
    ]
    ty = y + 58
    lh = 22.5
    for i, (indent, name, note, color, is_file) in enumerate(entries):
        yy = ty + i * lh
        bx = cx + 24 + indent * 22
        if is_file:
            bcol = BLUE if color == BLUE else "#94A3B8"
            parts.append(f'<rect x="{bx}" y="{yy-8}" width="10" height="10" rx="2.5" fill="{bcol}"/>')
        elif name.endswith("/"):
            parts.append(f'<path d="M {bx} {yy+3} h 11 l 4 4 v 7 h -15 Z" fill="none" stroke="{INK}" stroke-width="1.5"/>')
        parts.append(f'<text x="{bx+18}" y="{yy+2}" font-family="{MONO}" font-size="11.5" font-weight="{700 if color==INK else 500}" fill="{color}">{esc(name)}</text>')
        if note:
            nx = cx + 330
            ncol = BLUE if color == BLUE else MUTED
            parts.append(f'<text x="{nx}" y="{yy+2}" font-family="{SANS}" font-size="9.5" font-style="italic" fill="{ncol}">{esc(note)}</text>')
    # bottom warning banner
    wy = y + ch + 16
    parts.append(card(40, wy, 600, 46, fill=RED_B, stroke=RED, sw=1.5, rx=10))
    parts.append(f'<text x="{340}" y="{wy+19}" text-anchor="middle" font-family="{SANS}" font-size="11.5" font-weight="800" fill="{RED}">Never hand-edit a gear file. The next command overwrites it.</text>')
    parts.append(f'<text x="{340}" y="{wy+36}" text-anchor="middle" font-family="{SANS}" font-size="10" fill="{SLATE}">Project root = the closest folder up from cwd containing both agentcore/ and agentcore/agentcore.json.</text>')
    parts.append('</svg>')
    svg = "\n".join(parts)
    return save_svg(svg, "F3-directory-anatomy"), "F3-directory-anatomy"

# =====================================================================
# F4: deploy pipeline (gradient cards + timing bars)
# =====================================================================
def fig4():
    W, H = 680, 404
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}">',
             f'<rect width="{W}" height="{H}" fill="white"/>', DEFS]
    hp, y = header("under the hood", "Deploy: Six Steps to READY",
                   "One command. Zero Dockerfiles. Four CloudFormation resources.", ORANGE)
    parts += hp
    steps = [
        ("1", "Package", "zip src/ + deps", "41 MB asset", "g-blue", BLUE),
        ("2", "Synthesize", "CDK reads JSON,", "emits CFN template", "g-purple", PURPLE),
        ("3", "Upload", "asset goes to the", "bootstrap S3 bucket", "g-teal", TEAL),
        ("4", "Create stack", "CloudFormation", "provisions 4 resources", "g-orange", ORANGE),
        ("5", "Record state", "ARN + endpoint into", "deployed-state.json", "g-purple", PURPLE),
        ("6", "Print endpoint", "runtime flips to", "READY", "g-green", GREEN),
    ]
    bw, bh, gap = 98, 116, 8
    total = 6 * bw + 5 * gap
    ox = (W - total) // 2
    for i, (num, title, l1, l2, grad, color) in enumerate(steps):
        x = ox + i * (bw + gap)
        parts.append(card(x, y, bw, bh, fill="white", stroke=color, sw=2, rx=12))
        parts.append(f'<circle cx="{x+bw/2}" cy="{y+26}" r="15" fill="url(#{grad})"/>')
        parts.append(f'<text x="{x+bw/2}" y="{y+31}" text-anchor="middle" font-family="{SANS}" font-size="12" font-weight="800" fill="white">{num}</text>')
        parts.append(f'<text x="{x+bw/2}" y="{y+58}" text-anchor="middle" font-family="{SANS}" font-size="11.5" font-weight="800" fill="{color}">{esc(title)}</text>')
        parts.append(f'<text x="{x+bw/2}" y="{y+77}" text-anchor="middle" font-family="{SANS}" font-size="9" fill="{SLATE}">{esc(l1)}</text>')
        parts.append(f'<text x="{x+bw/2}" y="{y+90}" text-anchor="middle" font-family="{SANS}" font-size="9" fill="{SLATE}">{esc(l2)}</text>')
        if i < 5:
            ax = x + bw + 1
            parts.append(f'<path d="M {ax} {y+bh/2-5} L {ax+gap-2} {y+bh/2} L {ax} {y+bh/2+5} Z" fill="{MUTED}"/>')
    # timing bars
    by = y + bh + 36
    parts.append(f'<text x="40" y="{by-8}" font-family="{SANS}" font-size="11.5" font-weight="700" fill="{INK}">Measured wall-clock, cold account vs warm redeploy</text>')
    bar_x, bar_w = 40, 480
    # cold bar (589 s)
    parts.append(card(bar_x, by, bar_w, 26, fill="white", stroke=ORANGE, sw=1.5, rx=8))
    parts.append(f'<rect x="{bar_x+2}" y="{by+2}" width="{bar_w-4}" height="22" rx="6" fill="url(#g-orange)"/>')
    parts.append(f'<text x="{bar_x+bar_w/2}" y="{by+17}" text-anchor="middle" font-family="{SANS}" font-size="10.5" font-weight="700" fill="white">first deploy, cold: 9 min 49 s (mostly npm install, 221 packages)</text>')
    # warm bar (26 s)
    wy = by + 36
    w_w = max(26 / 589 * bar_w, 30)
    parts.append(card(bar_x, wy, bar_w, 26, fill="white", stroke=GREEN, sw=1.5, rx=8))
    parts.append(f'<rect x="{bar_x+2}" y="{wy+2}" width="{w_w:.0f}" height="22" rx="6" fill="url(#g-green)"/>')
    parts.append(f'<text x="{bar_x+w_w+10:.0f}" y="{wy+17}" font-family="{SANS}" font-size="10.5" font-weight="700" fill="#047857">redeploy, code only: 26 s</text>')
    # stack name note
    ny = wy + 52
    parts.append(f'<text x="40" y="{ny}" font-family="{SANS}" font-size="10.5" fill="{SLATE}">Stack name = <tspan font-family="{MONO}" font-weight="700" fill="{INK}">AgentCore-&lt;projectName&gt;-&lt;targetName&gt;</tspan> - both values come from the JSON, never hardcoded.</text>')
    parts.append('</svg>')
    svg = "\n".join(parts)
    return save_svg(svg, "F4-deploy-pipeline"), "F4-deploy-pipeline"

# =====================================================================
# F5: one surface, two hosts (vs comparison)
# =====================================================================
def fig5():
    W, H = 680, 496
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}">',
             f'<rect width="{W}" height="{H}" fill="white"/>', DEFS]
    hp, y = header("run it", "One HTTP Surface, Two Hosts",
                   "Your code implements two routes. Everything else about hosting is AgentCore's job.", TEAL)
    parts += hp
    # contract card top center
    cw, ch = 400, 64
    cx = (W - cw) // 2
    parts.append(f'<rect x="{cx}" y="{y}" width="{cw}" height="{ch}" rx="12" fill="url(#g-ink)" filter="url(#ds)"/>')
    parts.append(f'<text x="{W/2}" y="{y+28}" text-anchor="middle" font-family="{MONO}" font-size="14" font-weight="800" fill="white">GET /ping   |   POST /invocations</text>')
    parts.append(f'<text x="{W/2}" y="{y+48}" text-anchor="middle" font-family="{SANS}" font-size="10.5" fill="#93C5FD">the only two routes your code implements</text>')
    # two host cards
    hy = y + ch + 44
    hh = 190
    hw = 285
    lx, rx_ = 40, W - 40 - hw
    hosts = [
        (lx, "agentcore dev", "LOCAL", "g-teal", TEAL, TEAL_B,
         ["Uvicorn on localhost:8080", "hot reload on file save", "model calls still go to Bedrock", "no deployment, no stack"]),
        (rx_, "agentcore deploy", "CLOUD", "g-orange", ORANGE, ORANGE_B,
         ["serverless microVM per session", "https://.../runtimes/<arn>/invocations", "IAM role + trace pipeline included", "scaling handled by the platform"]),
    ]
    for x, title, tag, grad, color, light, items in hosts:
        parts.append(card(x, hy, hw, hh, fill="white", stroke=color, sw=2, rx=14))
        parts.append(f'<rect x="{x}" y="{hy}" width="{hw}" height="44" rx="14" fill="url(#{grad})"/>')
        parts.append(f'<rect x="{x}" y="{hy+30}" width="{hw}" height="14" fill="url(#{grad})"/>')
        parts.append(f'<text x="{x+16}" y="{hy+27}" font-family="{SANS}" font-size="14" font-weight="800" fill="white">{esc(title)}</text>')
        tw = 6 * 0.62 * len(tag) + 14
        parts.append(f'<rect x="{x+hw-tw-14:.0f}" y="{hy+13}" width="{tw:.0f}" height="18" rx="9" fill="white" opacity="0.25"/>')
        parts.append(f'<text x="{x+hw-14-tw/2:.0f}" y="{hy+25.5}" text-anchor="middle" font-family="{SANS}" font-size="9" font-weight="800" letter-spacing="1" fill="white">{tag}</text>')
        for j, item in enumerate(items):
            iy = hy + 66 + j * 30
            parts.append(f'<circle cx="{x+24}" cy="{iy-4}" r="7" fill="{light}"/>')
            parts.append(f'<path d="M {x+20.5} {iy-4} l 2.5 2.8 l 4.5 -5.5" stroke="#047857" stroke-width="1.8" fill="none" stroke-linecap="round"/>')
            parts.append(f'<text x="{x+40}" y="{iy}" font-family="{SANS}" font-size="10.5" fill="{SLATE}">{esc(item)}</text>')
    # equals badge between
    mbx, mby = W / 2, hy + hh / 2
    parts.append(f'<circle cx="{mbx}" cy="{mby}" r="19" fill="url(#g-green)" filter="url(#ds)"/>')
    parts.append(f'<text x="{mbx}" y="{mby+6}" text-anchor="middle" font-family="{SANS}" font-size="17" font-weight="800" fill="white">=</text>')
    parts.append(f'<text x="{mbx}" y="{hy-8}" text-anchor="middle" font-family="{SANS}" font-size="10" font-weight="700" fill="#047857">same code, same routes</text>')
    parts.append(f'<path d="M {lx+hw+8} {mby} L {rx_-8} {mby}" stroke="#10B981" stroke-width="2" stroke-dasharray="5,4"/>')
    # bottom note
    ny = hy + hh + 24
    parts.append(f'<text x="{W/2}" y="{ny}" text-anchor="middle" font-family="{SANS}" font-size="11" font-style="italic" fill="{MUTED}">No shim, no adapter, no second interface to drift. What passed locally deploys unchanged.</text>')
    parts.append(f'<text x="{W/2}" y="{ny+19}" text-anchor="middle" font-family="{SANS}" font-size="11" font-style="italic" fill="{MUTED}">agentcore invoke and boto3 are clients of the hosted surface, not a third interface.</text>')
    parts.append('</svg>')
    svg = "\n".join(parts)
    return save_svg(svg, "F5-one-surface"), "F5-one-surface"

# =====================================================================
# F6: span tree + side annotations
# =====================================================================
def fig6():
    W, H = 680, 470
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}">',
             f'<rect width="{W}" height="{H}" fill="white"/>', DEFS]
    hp, y = header("observability", "One Invoke, Dissected",
                   "The X-Ray span tree teaches the agent loop without reading framework source.", GREEN)
    parts += hp
    nodes = [
        (255, y + 14, "invoke_agent", "Strands Agents  ·  934 tokens", "g-blue", BLUE),
        (160, y + 94, "execute_event_loop_cycle", "cycle 1", "g-purple", PURPLE),
        (350, y + 94, "execute_event_loop_cycle", "cycle 2", "g-purple", PURPLE),
        (88,  y + 174, "execute_tool add_numbers", "TOOL span, status=success", "g-green", GREEN),
        (255, y + 174, "chat deepseek.v3.2", "finish_reason=tool_use", "g-orange", ORANGE),
        (422, y + 174, "chat deepseek.v3.2", "finish_reason=end_turn", "g-orange", ORANGE),
    ]
    nw, nh = 158, 50
    edges = [(0, 1), (0, 2), (1, 3), (1, 4), (2, 5)]
    for a, b in edges:
        x1, y1 = nodes[a][0], nodes[a][1] + nh
        x2, y2 = nodes[b][0], nodes[b][1]
        my = (y1 + y2) / 2
        parts.append(f'<path d="M {x1} {y1} V {my} H {x2} V {y2}" fill="none" stroke="{LINE}" stroke-width="1.8"/>')
        parts.append(f'<path d="M {x2-4} {y2-6} L {x2} {y2} L {x2+4} {y2-6} Z" fill="{MUTED}"/>')
    for x, yy, title, meta, grad, color in nodes:
        parts.append(card(x - nw / 2, yy, nw, nh, fill="white", stroke=color, sw=1.8, rx=10))
        parts.append(f'<rect x="{x - nw/2}" y="{yy}" width="5" height="{nh}" rx="2.5" fill="url(#{grad})"/>')
        tfs = 9.3 if len(title) > 20 else 10.5
        parts.append(f'<text x="{x - nw/2 + 13}" y="{yy+21}" font-family="{MONO}" font-size="{tfs}" font-weight="700" fill="{INK}">{esc(title)}</text>')
        parts.append(f'<text x="{x - nw/2 + 13}" y="{yy+38}" font-family="{SANS}" font-size="8.8" fill="{MUTED}">{esc(meta)}</text>')
    # side annotations
    ax_, aw = 540, 118
    anns = [
        (y + 60, YELLOW_B, "#B45309", "1 cycle = 1 model round trip"),
        (y + 130, GREEN_B, "#047857", "the tool call is a first-class span, not hidden text"),
        (y + 215, RED_B, RED, "spans need ~10 min to become queryable"),
        (y + 280, RED_B, RED, "local dev records no tool span"),
    ]
    for ay, bg, tc, txt in anns:
        lines = txt.split(" ")
        rows, cur = [], ""
        for wd in lines:
            if len(cur) + len(wd) + 1 <= 20:
                cur = (cur + " " + wd).strip()
            else:
                rows.append(cur); cur = wd
        rows.append(cur)
        rh = 14 + len(rows) * 12
        parts.append(f'<rect x="{ax_-8}" y="{ay}" width="{aw}" height="{rh}" rx="8" fill="{bg}"/>')
        for j, r_ in enumerate(rows):
            parts.append(f'<text x="{ax_}" y="{ay+17+j*12}" font-family="{SANS}" font-size="8.8" font-weight="600" fill="{tc}">{esc(r_)}</text>')
    parts.append('</svg>')
    svg = "\n".join(parts)
    return save_svg(svg, "F6-span-tree"), "F6-span-tree"

# ---- generate all ----
if __name__ == "__main__":
    figs = [fig0(), fig1(), fig2(), fig3(), fig4(), fig5(), fig6()]
    for svg_path, name in figs:
        png_path = to_png(svg_path, name, w=1440)
        print(f"  {name}: {os.path.basename(svg_path)} + {os.path.basename(png_path)}")
    print(f"\nDone. {len(figs)} figures generated in {OUT}")
