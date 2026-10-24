#!/usr/bin/env python3
"""Generate every image for the uc05 article from the run captured 2026-10-24/25.

Every line drawn here comes from `usecases/05-research-agent/evidence/`. The
terminal panels are that output with the account id redacted to 123456789012
and the spinner frames dropped; lines longer than the panel are wrapped and
nothing else is changed and nothing is invented. Each panel reads its evidence
file at build time, so the SVG, the PNG and this generator cannot disagree.

    python3 gen_figures.py            # writes every .svg next to this file
    ./render.sh                       # svg -> png
"""

from __future__ import annotations

import html
import pathlib
import re
import textwrap

HERE = pathlib.Path(__file__).resolve().parent
EVIDENCE = HERE.parents[2] / "usecases" / "05-research-agent" / "evidence"

BG0, BG1 = "#0a1024", "#0d1c3a"
BLUE, PURPLE, ORANGE, GREEN, RED, TEAL = (
    "#2563eb", "#7c3aed", "#ea580c", "#059669", "#e11d48", "#0d9488",
)
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
SANS = "Inter, Helvetica Neue, Arial, sans-serif"

W, G, O, T, D, S = "#f8fafc", "#34d399", "#fdba74", "#5eead4", "#7c93b5", "#cbd5e1"

PANEL_WIDTH = 112          # characters; everything longer is wrapped
WRAP_INDENT = "        "

SPINNERS = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


# --------------------------------------------------------------------------- #
# terminal panels                                                             #
# --------------------------------------------------------------------------- #

def wrap(lines: list[tuple[str, str]], width: int = PANEL_WIDTH) -> list[tuple[str, str]]:
    """Break lines that are wider than the panel. Nothing else is touched."""
    out: list[tuple[str, str]] = []
    for text, colour in lines:
        if len(text) <= width:
            out.append((text, colour))
            continue
        parts = textwrap.wrap(
            text, width=width, break_long_words=True, break_on_hyphens=False
        )
        out.append((parts[0], colour))
        out.extend((WRAP_INDENT + part, colour) for part in parts[1:])
    return out


def evidence_lines(stem: str) -> list[str]:
    """The captured output in an evidence file, headers and spinners removed."""
    raw = (EVIDENCE / stem).read_text(encoding="utf-8")
    # spinner frames ride on carriage returns: split on \r as well as \n
    raw = raw.replace("\r", "\n")
    lines = raw.splitlines()
    out = []
    for line in lines:
        s = line.strip()
        if not s or s and s[0] in SPINNERS:
            continue
        # strip ANSI escape sequences and any other control characters the capture
        # held; tabs become two spaces BEFORE the control-character strip
        line = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", line)
        line = line.replace("\t", "  ")
        line = "".join(ch for ch in line if ord(ch) >= 32)
        out.append(line.rstrip())
    # drop consecutive duplicates the CLI spinner re-prints
    dedup = []
    for line in out:
        if dedup and dedup[-1] == line:
            continue
        dedup.append(line)
    return dedup


def _redact_text(s: str) -> str:
    # generic: any 12-digit account id other than the placeholder is masked,
    # so the real id never needs to appear in this file
    return re.sub(r"\b\d{12}\b",
                  lambda m: "123456789012" if m.group(0) != "123456789012"
                  else m.group(0), s)


def redact(lines: list[str]) -> list[str]:
    """Account ids to 123456789012; also catch an id wrapped across two lines."""
    out = [_redact_text(line) for line in lines]
    fixed = []
    buf = ""
    for line in out:
        candidate = (buf + line) if buf else line
        if re.search(r"\b\d{4,6}$", line) and re.search(r"\b\d{6,8}$", buf or ""):
            buf = candidate
            continue
        fixed.append(_redact_text(candidate))
        buf = ""
    if buf:
        fixed.append(buf)
    return fixed


def short(line: str) -> str:
    """Shorten the absolute log path the CLI prints."""
    if line.startswith("Log: ") and ".cli/logs/" in line:
        return "Log: agentcore/.cli/logs/" + line.split(".cli/logs/", 1)[1]
    return line


def classify(line: str) -> str:
    if line.startswith("Session:") or line.startswith("To resume:"):
        return T
    if line.startswith("Log:") or line.startswith("Note:") or line.startswith("Next:"):
        return D
    if line.startswith("#"):
        return D
    if line.startswith("$ "):
        return S
    if "success" in line:
        return G
    if "error" in line:
        return O
    return W


def panel_lines(command: list[str], body: list[str]) -> list[tuple[str, str]]:
    """A `$ command` line, then the captured output."""
    lines = [(line, S) for line in command]
    for line in redact(body):
        text = short(line)
        if not text:
            continue
        lines.append((text, classify(text)))
    return lines


def shell_box(name: str, title: str, lines: list[tuple[str, str]], subtitle: str = "") -> None:
    """Render captured terminal output as an SVG panel.

    The frame is sized to its content. A fixed 1440 wide frame left two thirds
    of the box empty on the short captures and shrank the 17.5px text to about
    9px once the article fitted the image to its column.
    """
    top = 96
    pad = 34
    size = 17.5
    lh = 27
    adv = size * 0.62                                   # monospace advance
    chars = min(PANEL_WIDTH, max([len(t) for t, _ in lines] + [40]))
    lines = wrap(lines, chars)
    room = max(chars * adv, len(subtitle) * 15 * 0.6)
    width = int(min(1500, max(880, 58 + room + 76)))
    height = top + lh * (len(lines) + 1) + pad + (34 if subtitle else 0)

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img">',
        f"<title>{html.escape(title)}</title>",
        "<defs>",
        '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{BG0}"/><stop offset="1" stop-color="{BG1}"/></linearGradient>',
        '<radialGradient id="g1" cx="0.08" cy="0.02" r="0.8">'
        f'<stop offset="0" stop-color="{BLUE}" stop-opacity="0.22"/>'
        f'<stop offset="1" stop-color="{BLUE}" stop-opacity="0"/></radialGradient>',
        '<radialGradient id="g2" cx="0.92" cy="1.0" r="0.8">'
        f'<stop offset="0" stop-color="{PURPLE}" stop-opacity="0.20"/>'
        f'<stop offset="1" stop-color="{PURPLE}" stop-opacity="0"/></radialGradient>',
        "</defs>",
        f'<rect width="{width}" height="{height}" fill="url(#bg)"/>',
        f'<rect width="{width}" height="{height}" fill="url(#g1)"/>',
        f'<rect width="{width}" height="{height}" fill="url(#g2)"/>',
    ]

    out.append(f'<rect x="28" y="26" width="{width-56}" height="{height-52}" rx="16" '
               f'fill="#0b1428" stroke="#1e2a44" stroke-width="1.5"/>')
    out.append(f'<rect x="28" y="26" width="{width-56}" height="46" rx="16" fill="#101b33"/>')
    out.append(f'<rect x="28" y="58" width="{width-56}" height="14" fill="#101b33"/>')
    for i, colour in enumerate((RED, ORANGE, GREEN)):
        out.append(f'<circle cx="{56 + i*26}" cy="49" r="6.5" fill="{colour}" opacity="0.85"/>')
    out.append(f'<text x="{width//2}" y="55" font-family="{MONO}" font-size="16" fill="{D}" '
               f'text-anchor="middle">{html.escape(title)}</text>')

    y = top + 6
    for text, colour in lines:
        out.append(
            f'<text x="58" y="{y}" font-family="{MONO}" font-size="{size}" '
            f'fill="{colour}" xml:space="preserve">{html.escape(text)}</text>'
        )
        y += lh
    if subtitle:
        y += 8
        out.append(f'<text x="58" y="{y}" font-family="{MONO}" font-size="15" '
                   f'fill="{D}">{html.escape(subtitle)}</text>')
    out.append("</svg>")
    (HERE / f"{name}.svg").write_text("\n".join(out) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# figure 1: one config, three managed tools, two files                         #
# --------------------------------------------------------------------------- #

def figure_architecture() -> None:
    """Diagram. Every arrow endpoint is computed from the box rectangles below."""
    w, h = 1440, 760
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}" role="img">',
        "<title>One prompt reaches the managed harness, which drives web search "
        "through the gateway, pages through the browser and computes in the "
        "code interpreter; the files stay in the session VM until exec fetches them.</title>",
        "<defs>",
        '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{BG0}"/><stop offset="1" stop-color="{BG1}"/></linearGradient>',
        '<radialGradient id="g1" cx="0.08" cy="0.02" r="0.8">'
        f'<stop offset="0" stop-color="{BLUE}" stop-opacity="0.22"/>'
        f'<stop offset="1" stop-color="{BLUE}" stop-opacity="0"/></radialGradient>',
        '<radialGradient id="g2" cx="0.92" cy="1.0" r="0.8">'
        f'<stop offset="0" stop-color="{PURPLE}" stop-opacity="0.20"/>'
        f'<stop offset="1" stop-color="{PURPLE}" stop-opacity="0"/></radialGradient>',
        "</defs>",
        f'<rect width="{w}" height="{h}" fill="url(#bg)"/>',
        f'<rect width="{w}" height="{h}" fill="url(#g1)"/>',
        f'<rect width="{w}" height="{h}" fill="url(#g2)"/>',
    ]

    # explicit triangular heads, never <marker>s (resvg places them unreliably)
    AH_L, AH_HW = 15.0, 7.0

    def head(x, y, ux, uy, colour):
        bx, by = x - ux * AH_L, y - uy * AH_L
        px, py = -uy * AH_HW, ux * AH_HW
        out.append(
            f'<polygon points="{bx+px:.2f},{by+py:.2f} {x:.2f},{y:.2f} '
            f'{bx-px:.2f},{by-py:.2f}" fill="{colour}"/>'
        )

    def shaft(x1, y1, x2, y2, colour, width=2.2):
        ux, uy = x2 - x1, y2 - y1
        n = (ux * ux + uy * uy) ** 0.5
        ux, uy = ux / n, uy / n
        ex, ey = x2 - ux * AH_L * 0.55, y2 - uy * AH_L * 0.55
        out.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{ex:.2f}" y2="{ey:.2f}" '
                   f'stroke="{colour}" stroke-width="{width}"/>')
        head(x2, y2, ux, uy, colour)

    def label(x, y, text, size=16, colour="#8ea0bd", anchor="start", weight="400", mono=False):
        out.append(
            f'<text x="{x}" y="{y}" font-family="{MONO if mono else SANS}" font-size="{size}" '
            f'fill="{colour}" text-anchor="{anchor}" font-weight="{weight}">{html.escape(text)}</text>'
        )

    def box(name, x, y, bw, bh, fill, stroke, lines):
        out.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="14" fill="{fill}" '
                   f'stroke="{stroke}" stroke-width="2"/>')
        rows = lines
        start = y + bh / 2 - (len(rows) - 1) * 13 + 6
        for i, (text, size, colour, weight) in enumerate(rows):
            out.append(
                f'<text x="{x + bw/2:.0f}" y="{start + i*26:.0f}" font-family="{SANS}" '
                f'font-size="{size}" fill="{colour}" font-weight="{weight}" '
                f'text-anchor="middle">{html.escape(text)}</text>'
            )
        return {"x": x, "y": y, "w": bw, "h": bh}

    def edge_mid(b, side):
        cx, cy = b["x"] + b["w"] / 2, b["y"] + b["h"] / 2
        return {
            "left": (b["x"], cy), "right": (b["x"] + b["w"], cy),
            "top": (cx, b["y"]), "bottom": (cx, b["y"] + b["h"]),
        }[side]

    def arrow(b1, s1, b2, s2, colour, text="", tcolour="#64748b"):
        (x1, y1), (x2, y2) = edge_mid(b1, s1), edge_mid(b2, s2)
        shaft(x1, y1, x2, y2, colour)
        if text:
            label((x1 + x2) / 2, (y1 + y2) / 2 - 13, text, 14, tcolour, "middle")

    label(60, 62, "the deployed use case, uc05", 22, "#f8fafc", weight="600")
    label(60, 90, "one prompt reaches the harness, the harness calls three managed tools, the files stay in the session VM", 15)

    # Three columns with a 90 unit channel between the harness and the tools so
    # that every connector and its label has room of its own. Nothing is routed
    # under another node, so no line crosses another line.
    TRUNK = 810
    x_c, x_h, x_t, tw = 60, 380, 900, 340

    b_caller = box("caller", x_c, 270, 240, 110, "#0e1a33", "#2b3c5e",
                   [("one prompt", 19, "#f8fafc", "600"),
                    ("agentcore invoke", 15, "#7c93b5", "400")])
    b_harness = box("harness", x_h, 225, 340, 200, "#122146", "#3b82f6",
                    [("managed harness", 20, "#f8fafc", "600"),
                     ("harness.json: model, prompt,", 14, "#7c93b5", "400"),
                     ("max-iterations, tool list", 14, "#7c93b5", "400"),
                     ("session VM per session id", 14, "#c4b5fd", "400")])
    b_browser = box("browser", x_t, 160, tw, 100, "#0d1729", "#0d9488",
                    [("browser tool", 17, "#5eead4", "600"),
                     ("StartBrowserSession, pages", 13, "#7c93b5", "400")])
    b_gw = box("gw", x_t, 300, tw, 110, "#122146", "#7c3aed",
               [("gateway · web-search", 18, "#e9d5ff", "600"),
                ("connector target", 14, "#7c93b5", "400"),
                ("managed web index", 14, "#c4b5fd", "400")])
    b_ci = box("ci", x_t, 450, tw, 110, "#0d1729", "#ea580c",
               [("code interpreter", 17, "#fdba74", "600"),
                ("sandbox: stdlib + PIL, numpy", 13, "#7c93b5", "400"),
                ("wind.xlsx + wind.png", 13, "#fdba74", "400")])
    b_vm = box("vm", x_t, 610, tw, 100, "#0e1a33", "#2b3c5e",
               [("session VM", 18, "#f8fafc", "600"),
                ("agentcore exec pins the id", 13, "#7c93b5", "400"),
                ("ls · base64 out", 13, "#34d399", "400")])

    arrow(b_caller, "right", b_harness, "left", "#60a5fa", "invoke")

    # fan-out: one trunk out of the harness, one stub per tool, each stub long
    # enough to carry its own label above it
    hx, hy = edge_mid(b_harness, "right")
    out.append(f'<line x1="{hx:.2f}" y1="{hy:.2f}" x2="{TRUNK}" y2="{hy:.2f}" '
               f'stroke="#60a5fa" stroke-width="2.2"/>')
    out.append(f'<line x1="{TRUNK}" y1="210" x2="{TRUNK}" y2="505" '
               f'stroke="#60a5fa" stroke-width="2.2"/>')
    for b, text in ((b_browser, "browse"), (b_gw, "search"), (b_ci, "code")):
        tx, ty = edge_mid(b, "left")
        shaft(TRUNK, ty, tx, ty, "#60a5fa")
        label((TRUNK + tx) / 2, ty - 11, text, 14, "#8ea0bd", "middle")

    # the two files are written inside the sandbox, exec reads them back out
    cx2, cy2 = edge_mid(b_ci, "bottom")
    vx2, vy2 = edge_mid(b_vm, "top")
    shaft(cx2, cy2, vx2, vy2, "#fdba74")
    label(vx2 + 14, (cy2 + vy2) / 2 + 5, "files land in /home", 14, "#8ea0bd", "start")

    out.append("</svg>")
    (HERE / "F1-harness-architecture.svg").write_text("\n".join(out) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# covers                                                                      #
# --------------------------------------------------------------------------- #

def cover(w: int, h: int, name: str, safe: float = 0.0) -> None:
    """Normalised layout, so the same composition works at every ratio.

    `safe` is the fraction of width that must survive a 1.91:1 centre crop. The
    Dev.to cover ships at 2.38:1 for the 1000x420 article slot, but Dev.to also
    feeds the same URL to its 1200x627 social card, which crops 9.8% off each
    side. Padding the art to >= 10.5% keeps both crops intact.
    """
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" '
        f'height="{h}" role="img">',
        "<title>A research agent in AgentCore: one prompt, three managed tools, two real files</title>",
        "<defs>",
        '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{BG0}"/><stop offset="1" stop-color="{BG1}"/></linearGradient>',
        '<radialGradient id="g1" cx="0.08" cy="0.02" r="0.8">'
        f'<stop offset="0" stop-color="{BLUE}" stop-opacity="0.22"/>'
        f'<stop offset="1" stop-color="{BLUE}" stop-opacity="0"/></radialGradient>',
        '<radialGradient id="g2" cx="0.92" cy="1.0" r="0.8">'
        f'<stop offset="0" stop-color="{PURPLE}" stop-opacity="0.20"/>'
        f'<stop offset="1" stop-color="{PURPLE}" stop-opacity="0"/></radialGradient>',
        "</defs>",
        f'<rect width="{w}" height="{h}" fill="url(#bg)"/>',
        f'<rect width="{w}" height="{h}" fill="url(#g1)"/>',
        f'<rect width="{w}" height="{h}" fill="url(#g2)"/>',
    ]

    pad = round(max(0.055, safe) * w)
    bw = w - 2 * pad
    u = bw / 0.89

    hl = max(10.0, 13.0 * u / 1200)
    hw = hl * 0.5

    def head(x, y, colour):
        out.append(f'<polygon points="{x-hl:.2f},{y-hw:.2f} {x:.2f},{y:.2f} '
                   f'{x-hl:.2f},{y+hw:.2f}" fill="{colour}"/>')

    def shaft(x1, y1, x2, y2, colour, width=2.2):
        ex = x2 - hl * 0.55
        out.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{ex:.2f}" y2="{y2:.2f}" '
                   f'stroke="{colour}" stroke-width="{width}"/>')
        head(x2, y2, colour)

    out.append(
        f'<text x="{pad:.0f}" y="{0.15*h:.0f}" font-family="{SANS}" font-size="{0.024*u:.0f}" '
        f'fill="#60a5fa" font-weight="600">AgentCore in Action</text>'
    )
    out.append(
        f'<text x="{pad:.0f}" y="{0.28*h:.0f}" font-family="{SANS}" font-size="{0.052*u:.0f}" '
        f'fill="#f8fafc" font-weight="700">The Managed Harness</text>'
    )
    out.append(
        f'<text x="{pad:.0f}" y="{0.365*h:.0f}" font-family="{SANS}" '
        f'font-size="{0.022*u:.0f}" fill="#c4b5fd">'
        f'one prompt, three tools, two files, no agent loop written</text>'
    )

    # three equal boxes with equal gutters: the band spans pad .. w-pad exactly,
    # so the left and right margins match and no box is wider than its text
    gap = round(bw * 0.085)
    boxw = round((bw - 2 * gap) / 3)
    top = round(0.47 * h)
    bh = round(0.28 * h)
    xs = [pad, pad + boxw + gap, pad + 2 * (boxw + gap)]
    boxes = [
        dict(x=xs[0], stroke="#3b82f6", head="one prompt",
             body=["search, browse,", "compute"]),
        dict(x=xs[1], stroke="#7c3aed", head="managed harness",
             body=["harness.json + tools", "session state per id"]),
        dict(x=xs[2], stroke="#059669", head="session VM",
             body=["wind.xlsx 1,806 B", "wind.png 16,705 B"]),
    ]
    fs = round(0.0165 * w)
    cy = top + bh // 2
    pitch = 0.05 * h
    for b in boxes:
        b["h"] = bh
        out.append(
            f'<rect x="{b["x"]}" y="{top}" width="{boxw}" height="{bh}" '
            f'rx="14" fill="#0b1428" stroke="{b["stroke"]}" stroke-width="2"/>'
        )
        rows = [(b["head"], b["stroke"], "600")]
        rows += [(line, "#cbd5e1", "400") for line in b["body"]]
        for i, (text, colour, weight) in enumerate(rows):
            y = cy + 0.25*fs + (i - 1) * pitch
            out.append(
                f'<text x="{b["x"] + boxw/2:.0f}" y="{y:.0f}" font-family="{SANS}" '
                f'font-size="{fs}" fill="{colour}" font-weight="{weight}" '
                f'text-anchor="middle">{html.escape(text)}</text>'
            )

    a, g, c = boxes
    lfs = round(0.015 * w)
    for left, right, colour, text in (
        (a, g, "#60a5fa", "invoke"),
        (g, c, "#34d399", "tools"),
    ):
        shaft(left["x"] + boxw, cy, right["x"], cy, colour)
        out.append(
            f'<text x="{(left["x"] + boxw + right["x"]) / 2:.0f}" y="{cy - 14}" '
            f'font-family="{SANS}" font-size="{lfs}" fill="{colour}" '
            f'text-anchor="middle">{text}</text>'
        )

    out.append(
        f'<text x="{pad:.0f}" y="{0.90*h:.0f}" font-family="{SANS}" '
        f'font-size="{0.016*u:.0f}" fill="#8ea0bd">'
        f'one invoke, 22 tool spans, two real files; the model switches mid-session and the session survives</text>'
    )
    out.append("</svg>")
    (HERE / f"{name}.svg").write_text("\n".join(out) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# every panel                                                                 #
# --------------------------------------------------------------------------- #

def panels() -> None:
    shell_box(
        "D1-adds", "terminal - the gateway, the web-search connector, the harness",
        panel_lines(
            ["$ agentcore add gateway --name research-gateway --protocol-type MCP --authorizer-type NONE"],
            evidence_lines("10-add-gateway.txt"),
        )
        + panel_lines(
            ["$ agentcore add gateway-target --name websearch --gateway research-gateway \\",
             "    --type connector --connector web-search"],
            evidence_lines("11-add-target.txt"),
        )
        + panel_lines(
            ["$ agentcore add harness --name research --model-provider bedrock \\",
             "    --model-id deepseek.v3.2 --api-format converse_stream \\",
             "    --tools agentcore_browser,agentcore_code_interpreter \\",
             '    --system-prompt "You are a market research analyst..." \\',
             "    --max-iterations 30 --timeout 900"],
            evidence_lines("12-add-harness.txt"),
        ),
        "evidence/10, 11, 12 · web search is a gateway connector; the harness carries browser and code interpreter",
    )
    shell_box(
        "S1-deploy", "terminal - agentcore deploy, first deploy (2 m 22 s)",
        panel_lines(["$ agentcore deploy -y --target default"],
                    evidence_lines("15-deploy-2.log")),
        "evidence/15-deploy-2.log · one stack: gateway with its web-search target, the harness, its runtime",
    )
    ev17 = evidence_lines("17-add-gwtool.txt")
    shell_box(
        "S2-gwtool", "terminal - wire the gateway to the harness as a tool, deploy again",
        panel_lines(
            ["$ agentcore add tool --harness research --type agentcore_gateway --name websearch \\",
             "    --gateway research-gateway --outbound-auth none"],
            [l for l in ev17 if "Added" in l or "deploy" in l],
        ),
        "evidence/17-add-gwtool.txt · the gateway resolves to its ARN from deployed state",
    )
    ev20 = evidence_lines("20-invoke-final.txt")
    shell_box(
        "S3-invoke", "terminal - one prompt: search, browse, compute, two files (4 m 02 s)",
        panel_lines(
            ['$ agentcore invoke --session-id research-session-0004-artifacts-run --prompt "Produce a short',
             '    market note on wind power. Step 1: use the websearch tool..."'],
            [l for l in ev20 if l.startswith("Step") or l.startswith("-") or
             l.startswith("**Step") or l.startswith("1.") or l.startswith("2.") or
             l.startswith("- China") or l.startswith("- United States") or l.startswith("- Germany") or
             l.startswith("- Brazil") or l.startswith("- India") or
             ("wind.xlsx" in l) or ("wind.png" in l) or l.startswith("Session:")],
        ),
        "evidence/20-invoke-final.txt · the full answer names both files with their byte sizes",
    )
    ev22 = evidence_lines("22-spans-final.txt")
    shell_box(
        "S4-spans", "terminal - the span listing for that one session",
        panel_lines(
            ["$ aws logs filter-log-events --region us-east-1 \\",
             "    --log-group-name aws/spans --start-time <ms> \\",
             '''    --query "events[].message" --output json | jq -r ".[]" | jq -r ''',
             '''    'select(."attributes"."session.id"? == "research-session-0004-artifacts-run")''',
             '''    | [.name, ."attributes"."gen_ai.tool.status"] | @tsv"' '''],
            ev22,
        ),
        "evidence/22-spans-final.txt · websearch and browser success, code_interpreter errors, shell successes",
    )
    ev21 = evidence_lines("21-exec-inspect.txt")
    keep = [l for l in ev21 if ("zip OK" in l or "PNG magic" in l or "dimensions" in l
                                or l.strip().endswith(".xml") or l.strip().endswith(".rels"))]
    shell_box(
        "S5-exec", "terminal - agentcore exec, pinned to the same session, inspects the files",
        panel_lines(
            ["$ agentcore exec --harness research \\",
             "    --session-id research-session-0004-artifacts-run -- sh -c \\",
             '    "python3 -c \\"import zipfile; z=zipfile.ZipFile(\'/home/wind.xlsx\');',
             '    print(z.testzip() is None, z.namelist())\\" ..."'],
            keep,
        ),
        "evidence/21-exec-inspect.txt · zip CRC True, five OOXML members, PNG magic 89504e47, 800x600",
    )
    ev30 = evidence_lines("30-model-before.txt")
    ev32 = evidence_lines("32-model-after.txt")
    shell_box(
        "S6-model-switch", "terminal - the same session, before and after the mid-session model switch",
        panel_lines(
            ["$ agentcore invoke --session-id research-session-0004-artifacts-run \\",
             '    --prompt "Before we switch anything: which country had the smallest wind share..."'],
            [l for l in ev30 if l and not l.startswith("$")][:1],
        )
        + panel_lines(
            ["# edit app/research/harness.json: modelId deepseek.v3.2 -> amazon.nova-lite-v1:0",
             "$ agentcore deploy -y --target default        # 1 m 40 s, harness version 5",
             "$ agentcore invoke --session-id research-session-0004-artifacts-run \\",
             '    --prompt "Same session, new model. From the table you built earlier..."'],
            [l for l in ev32 if l and not l.startswith("$")][:1],
        ),
        "evidence/30, 31, 32 · both answers name India at 5.1%, one harness version apart",
    )
    ev33 = evidence_lines("33-spans-after-switch.txt")
    shell_box(
        "S7-spans-after", "terminal - spans after the switch: two chat models, no new tool calls",
        panel_lines(
            ["$ aws logs filter-log-events ... --query 'events[].message' --output json \\",
             "  | jq -r '.[] | fromjson? | select(.\"attributes\".\"session.id\"? == \"research-session-0004-artifacts-run\")",
             "  | [.name, .\"attributes\".\"gen_ai.tool.status\"] | @tsv'"],
            sorted(set(ev33)),
        ),
        "evidence/33-spans-after-switch.txt · chat deepseek.v3.2 and chat amazon.nova-lite-v1:0 share the session",
    )
    ev40 = evidence_lines("40-export.txt")
    ev42 = evidence_lines("42-invoke-export.txt")
    ev43 = evidence_lines("43-invoke-export-same.txt")
    shell_box(
        "S8-export", "terminal - export the harness to a Strands runtime agent, deploy, compare",
        panel_lines(
            ["$ agentcore export harness --name research --target-agent-name researchAgent"],
            [l for l in ev40 if l.startswith("Exported") or l.startswith("  app/") or l.startswith("  agentcore")],
        )
        + panel_lines(
            ["$ agentcore deploy -y --target default        # 2 m 11 s",
             "$ agentcore invoke --runtime researchAgent --session-id research-session-0007-export-same --prompt \"...\""],
            [l for l in ev43 if l.startswith("- ") or "percent" in l][:5],
        ),
        "evidence/40, 41, 43 · the export answers with the same five shares the harness computed",
    )
    ev60 = evidence_lines("60-remove-all.txt")
    ev61 = evidence_lines("61-reconcile.log")
    ev62 = evidence_lines("62-status-empty.txt")
    shell_box(
        "S9-teardown", "terminal - teardown: remove all, reconcile, empty status",
        panel_lines(
            ["$ agentcore remove all -y"],
            [l for l in ev60 if l.startswith("All") or l.startswith("Your")],
        )
        + panel_lines(
            ["$ agentcore deploy -y --target default        # 3 m 12 s"],
            [l for l in ev61 if "Tear down" in l or l.startswith("✓ Deployed")],
        )
        + panel_lines(
            ["$ agentcore status"],
            [l for l in ev62 if "No resources" in l],
        ),
        "evidence/60, 61, 62 · remove all rewrites agentcore.json and aws-targets.json; restore both from git",
    )


def main() -> None:
    panels()
    figure_architecture()
    cover(1200, 675, "cover")
    cover(1000, 420, "cover-devto", safe=0.105)
    cover(1400, 788, "cover-medium")   # Medium feature image, same 16:9 composition


if __name__ == "__main__":
    main()
