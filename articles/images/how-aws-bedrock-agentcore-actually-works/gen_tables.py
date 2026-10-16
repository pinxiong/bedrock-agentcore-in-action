#!/usr/bin/env python3
"""Render the article's two tables as PNG images.

Why: Medium has no table support, so `Import a story` drops Markdown tables.
These two images replace them in the Medium version, keeping the article's
design language (white bg, kicker pill, rounded card, colored accents).

Output: T1-layers-table.png, T2-requirements-table.png  (1440 px wide, same as
the figures produced by gen_figures.py).

Run: /Users/pinxiong/.workbuddy/binaries/python/envs/default/bin/python gen_tables.py
"""
import os
import resvg_py

OUT = os.path.dirname(os.path.abspath(__file__))

INK    = "#0F172A"
SLATE  = "#475569"
MUTED  = "#64748B"
LINE   = "#CBD5E1"
BLUE   = "#2563EB"; BLUE_B  = "#DBEAFE"
PURPLE = "#7C3AED"; PURPLE_B = "#EDE9FE"
TEAL   = "#0D9488"; TEAL_B  = "#CCFBF1"
SLATE_B = "#F1F5F9"
ROW_ALT = "#F8FAFC"

SANS = "'Helvetica Neue', 'PingFang SC', Arial, sans-serif"
MONO = "'SF Mono', Menlo, Consolas, monospace"

DEFS = f'''
<defs>
  <filter id="ds" x="-30%" y="-30%" width="160%" height="160%">
    <feDropShadow dx="0" dy="2.5" stdDeviation="4" flood-color="{INK}" flood-opacity="0.15"/>
  </filter>
</defs>
'''


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def header(kicker, title, sub, accent, W=680):
    pill_w = 20 + 7.8 * len(kicker)
    p = [
        f'<rect x="40" y="24" width="{pill_w:.0f}" height="21" rx="10.5" fill="{accent}"/>',
        f'<text x="{40 + pill_w/2:.0f}" y="38.5" text-anchor="middle" font-family="{SANS}" '
        f'font-size="10" font-weight="700" letter-spacing="1.2" fill="white">{esc(kicker.upper())}</text>',
        f'<text x="40" y="80" font-family="{SANS}" font-size="23" font-weight="800" fill="{INK}">{esc(title)}</text>',
    ]
    if sub:
        p.append(f'<text x="40" y="102" font-family="{SANS}" font-size="12.5" fill="{SLATE}">{esc(sub)}</text>')
    return p, 126


# ---- inline `code` support ------------------------------------------------
def tokens(cell):
    """Split a cell on backticks into [(text, is_mono)]."""
    out, mono = [], False
    for part in cell.split("`"):
        if part:
            out.append((part, mono))
        mono = not mono
    return out


def est_width(tok_text, size, mono):
    return len(tok_text) * size * (0.62 if mono else 0.58)


def wrap_tokens(toks, max_w, size):
    """Word-wrap a token list into lines (each line is a token list)."""
    lines, cur, cur_w = [], [], 0.0
    for text, mono in toks:
        for i, word in enumerate(text.split(" ")):
            if i:  # re-add the space that split() ate
                word = " " + word
            w = est_width(word, size, mono)
            if cur_w + w > max_w and cur:
                lines.append(cur)
                cur, cur_w = [], 0.0
                word = word.lstrip(" ")
                w = est_width(word, size, mono)
            cur.append((word, mono))
            cur_w += w
    if cur:
        lines.append(cur)
    return lines or [[("", False)]]


def cell_text(x, y, line, size, color, mono_color=None):
    out = []
    for text, mono in line:
        if not text:
            continue
        fam = MONO if mono else SANS
        fill = mono_color if (mono and mono_color) else color
        out.append(f'<tspan font-family="{fam}" fill="{fill}">{esc(text)}</tspan>')
    return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="500" fill="{color}">{"".join(out)}</text>'


def table(kicker, title, sub, accent, tint, widths, rows, aligns, body_size=10.5):
    """rows[0] is the header row. Cells may use `code` spans."""
    W = 680
    x0, pad = 40, 10
    head_size = 10.5
    line_h = 14.5
    row_pad = 8.5

    body, y = [], 126
    # header band
    hh = 30
    body.append(f'<path d="M{x0} {y+12} a12 12 0 0 1 12 -12 h{W-2*x0-24} a12 12 0 0 1 12 12 v{hh-12} h-{W-2*x0} z" fill="{tint}"/>')
    cx = x0
    for cell, cw, al in zip(rows[0], widths, aligns):
        tx = cx + pad if al == "l" else cx + cw - pad
        anchor = "start" if al == "l" else "end"
        body.append(
            f'<text x="{tx}" y="{y + 20}" text-anchor="{anchor}" font-family="{SANS}" font-size="{head_size}" '
            f'font-weight="700" letter-spacing="0.4" fill="{accent}">{esc(cell.upper())}</text>'
        )
        cx += cw
    cy = y + hh

    # body rows
    for ri, row in enumerate(rows[1:]):
        lines_per_cell = []
        for cell, cw in zip(row, widths):
            max_w = cw - 2 * pad
            lines_per_cell.append(wrap_tokens(tokens(cell), max_w, body_size))
        rh = row_pad * 2 + line_h * max(len(l) for l in lines_per_cell)
        if ri % 2 == 1:
            body.append(f'<rect x="{x0}" y="{cy}" width="{W-2*x0}" height="{rh:.1f}" fill="{ROW_ALT}"/>')
        cx = x0
        for cell_lines, cw, al in zip(lines_per_cell, widths, aligns):
            for li, line in enumerate(cell_lines):
                ty = cy + row_pad + line_h * li + 10.5
                if al == "l":
                    body.append(cell_text(cx + pad, ty, line, body_size, SLATE, mono_color=accent))
                else:
                    # right-aligned: append anchored text, mono spans get accent
                    inner = "".join(
                        f'<tspan font-family="{MONO if m else SANS}" fill="{accent if m else SLATE}">{esc(t)}</tspan>'
                        for t, m in line if t
                    )
                    body.append(f'<text x="{cx + cw - pad}" y="{ty}" text-anchor="end" font-size="{body_size}" fill="{SLATE}">{inner}</text>')
            cx += cw
        body.append(f'<line x1="{x0}" y1="{cy+rh:.1f}" x2="{W-x0}" y2="{cy+rh:.1f}" stroke="{LINE}" stroke-width="1"/>')
        cy += rh

    table_h = cy - 126
    H = cy + 24
    card = (f'<rect x="{x0}" y="126" width="{W-2*x0}" height="{table_h:.1f}" rx="12" fill="white" '
            f'stroke="{LINE}" stroke-width="1.5" filter="url(#ds)"/>')
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H:.0f}" width="{W}">', DEFS]
    hp, _ = header(kicker, title, sub, accent)
    parts += hp + [card] + body + ['</svg>']
    return "".join(parts), W, H


def t1():
    rows = [
        ["Layer", "What lives there", "Who maintains it"],
        ["Business code", "`app/<AgentName>/` with the agent entrypoint", "you"],
        ["The contract", "`agentcore.json` and `aws-targets.json`", "you, by hand"],
        ["The plumbing", "a CDK project under `agentcore/cdk/`", "the CLI, on every deploy"],
    ]
    return table(
        "Three layers", "Who owns what in the project", "Two files you edit, one directory the CLI rewrites on every deploy",
        BLUE, BLUE_B, [130, 300, 170], rows, ["l", "l", "l"],
    )


def t2():
    rows = [
        ["Tool", "Version used", "Notes", "Check"],
        ["Node.js", "24.x", "20+ required by the CLI", "`node --version`"],
        ["AgentCore CLI", "0.31.1", "install below", "`agentcore --version`"],
        ["AWS CLI", "2.x", "any recent build", "`aws --version`"],
        ["uv", "0.11.9", "the CLI builds the Python environment for template agents with it", "`uv --version`"],
        ["Git", "2.39", "`create` runs `git init` in the new project", "`git --version`"],
        ["Python", "3.12 in the app venv", "3.10 to 3.14 supported by CodeZip; the runtime target is the CLI's default, not your interpreter", "`python3 -V`"],
        ["AWS account", "any", "with permissions below", "`aws sts get-caller-identity`"],
        ["Region", "us-east-1", "the whole series uses it", "`aws configure get region`"],
        ["Docker", "not needed", "this series uses CodeZip builds", "n/a"],
    ]
    return table(
        "Requirements", "What you need before the first command", "Versions used in this walkthrough, and the command that proves each one",
        TEAL, TEAL_B, [96, 136, 216, 152], rows, ["l", "l", "l", "r"], body_size=10,
    )


def main():
    for name, (svg, W, H) in {"T1-layers-table": t1(), "T2-requirements-table": t2()}.items():
        svg_path = os.path.join(OUT, f"{name}.svg")
        with open(svg_path, "w") as f:
            f.write(svg)
        png = resvg_py.svg_to_bytes(svg_path=svg_path, width=1440, background="#FFFFFF")
        with open(os.path.join(OUT, f"{name}.png"), "wb") as f:
            f.write(png)
        print(f"{name}.png  viewBox {W}x{H:.0f}  -> 1440 px wide  {len(png)} bytes")


if __name__ == "__main__":
    main()
