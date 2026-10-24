#!/usr/bin/env python3
"""Generate every image for the uc04 article from the run captured 2026-10-23/24.

Every line drawn here comes from `usecases/04-policy/evidence/`. The terminal
panels are that output with the account id redacted to 123456789012 and the
spinner frames dropped; lines longer than the panel are wrapped and nothing else
is changed and nothing is invented. Each panel reads its evidence file at build
time, so the SVG, the PNG and this generator cannot disagree.

    python3 gen_figures.py            # writes every .svg next to this file
    ./render.sh                       # svg -> png
"""

from __future__ import annotations

import html
import pathlib
import re
import textwrap

HERE = pathlib.Path(__file__).resolve().parent
EVIDENCE = HERE.parents[2] / "usecases" / "04-policy" / "evidence"

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

def wrap(lines: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Break lines that are wider than the panel. Nothing else is touched."""
    out: list[tuple[str, str]] = []
    for text, colour in lines:
        if len(text) <= PANEL_WIDTH:
            out.append((text, colour))
            continue
        parts = textwrap.wrap(
            text, width=PANEL_WIDTH, break_long_words=True, break_on_hyphens=False
        )
        out.append((parts[0], colour))
        out.extend((WRAP_INDENT + part, colour) for part in parts[1:])
    return out


def evidence_lines(stem: str) -> list[str]:
    """The captured output in an evidence file, headers and spinners removed."""
    lines = (EVIDENCE / stem).read_text(encoding="utf-8").splitlines()
    out = []
    for line in lines:
        s = line.strip()
        if not s or s and s[0] in SPINNERS:
            continue
        # strip ANSI escape sequences and any other control characters the capture
        # held; tabs become two spaces BEFORE the control-character strip, or the
        # strip would swallow them (CloudWatch text output separates values with
        # tabs) and "1.0<TAB>2.0" would render as "1.02.0"
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
    if "DENY" in line or "Denied" in line or "denied" in line:
        return O
    if "ALLOW" in line or "refundCeiling" in line or "approvalAlways" in line:
        return G
    if line.startswith("LOG_ONLY") or line.startswith("ENFORCE"):
        return O if "Deny" in line else G
    return W


def panel_lines(command: list[str], body: list[str]) -> list[tuple[str, str]]:
    """A `$ command` line, then the captured output."""
    lines = [(line, S) for line in command]
    for line in body:
        text = short(line)
        if not text:
            continue
        lines.append((text, classify(text)))
    return lines


def shell_box(name: str, title: str, lines: list[tuple[str, str]], subtitle: str = "") -> None:
    """Render captured terminal output as an SVG panel."""
    lines = wrap(lines)
    top = 96
    pad = 34
    size = 17.5
    lh = 27
    width = 1440
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
# figure 1: the agent proposes, the engine disposes                            #
# --------------------------------------------------------------------------- #

def figure_architecture() -> None:
    """Diagram. Every arrow endpoint is computed from the box rectangles below."""
    w, h = 1440, 700
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}" role="img">',
        "<title>The model proposes a refund, the policy engine attached to the gateway "
        "decides before the backend ever runs.</title>",
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

    # Arrowheads are explicit triangles, not <marker>s: resvg places and tints
    # markers unreliably (curved paths shift the head off the tangent, vertical
    # lines inherit the wrong fill), so the tip is computed here and lands on
    # the target border by construction.
    AH_L, AH_HW = 15.0, 7.0        # head length / half width, figure units

    def head(x, y, ux, uy, colour):
        """Triangle whose TIP is exactly (x, y), pointing along (ux, uy)."""
        bx, by = x - ux * AH_L, y - uy * AH_L
        px, py = -uy * AH_HW, ux * AH_HW
        out.append(
            f'<polygon points="{bx+px:.2f},{by+py:.2f} {x:.2f},{y:.2f} '
            f'{bx-px:.2f},{by-py:.2f}" fill="{colour}"/>'
        )

    def shaft(x1, y1, x2, y2, colour, width=2.2):
        """Line stopping inside the head, so the tip is triangle-only."""
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
        """The midpoint of one box edge: left, right, top, bottom."""
        cx, cy = b["x"] + b["w"] / 2, b["y"] + b["h"] / 2
        return {
            "left": (b["x"], cy), "right": (b["x"] + b["w"], cy),
            "top": (cx, b["y"]), "bottom": (cx, b["y"] + b["h"]),
        }[side]

    def arrow(b1, s1, b2, s2, colour, text="", tcolour="#64748b"):
        (x1, y1), (x2, y2) = edge_mid(b1, s1), edge_mid(b2, s2)
        shaft(x1, y1, x2, y2, colour)
        if text:
            # centred on the line: baseline just above it, at the midpoint
            label((x1 + x2) / 2, (y1 + y2) / 2 - 8, text, 14, tcolour, "middle")

    def side_label(x, y_top, y_bot, text, side="left"):
        """A vertical line's label: beside the line, vertically centred on it."""
        mid = (y_top + y_bot) / 2
        if side == "left":
            label(x - 12, mid + 5, text, 14, "#64748b", "end")
        else:
            label(x + 12, mid + 5, text, 14, "#64748b", "start")

    label(60, 62, "the deployed use case, uc04", 22, "#f8fafc", weight="600")
    label(60, 90, "the ceiling lives in Cedar on the engine, not in the prompt the model reads", 15)

    # ---- page grid --------------------------------------------------------
    # 60px page margins; the leftover width is split evenly over the three
    # gaps of the request chain, so the right side is as tight as the left.
    margin, cy = 60, 300                     # cy: the chain's shared centreline
    cw, aw, gww, lw = 240, 300, 300, 220     # box widths: caller, agent, gateway, backend
    gap = (w - 2 * margin - (cw + aw + gww + lw)) / 3
    x_lambda = w - margin - lw               # anchored right: the 60px margin holds
    x_gw = round(x_lambda - gww - gap)
    x_agent = round(x_gw - aw - gap)
    x_caller = margin
    x_col = x_gw                             # engine and log align on the gateway

    b_caller = box("caller", x_caller, cy - 60, cw, 120, "#0e1a33", "#2b3c5e",
                   [("customer / rep", 19, "#f8fafc", "600"), ("agentcore invoke", 15, "#7c93b5", "400")])
    b_agent = box("agent", x_agent, cy - 75, aw, 150, "#122146", "#3b82f6",
                  [("AgentCore Runtime", 20, "#f8fafc", "600"),
                   ("aia_uc04 · Strands · deepseek.v3.2", 14, "#7c93b5", "400"),
                   ("no rule in the prompt", 14, "#fda4af", "400")])
    b_eng = box("eng", x_col, 40, 300, 104, "#0d1729", "#7c3aed",
                [("policy engine · 2 Cedar policies", 17, "#e9d5ff", "600"),
                 ("amount <= 500, otherwise default deny", 14, "#7c93b5", "400")])
    b_gw = box("gw", x_gw, cy - 100, gww, 200, "#122146", "#7c3aed",
               [("AgentCore Gateway", 20, "#e9d5ff", "600"),
                ("MCP endpoint", 14, "#7c93b5", "400"),
                ("mode: LOG_ONLY | ENFORCE", 14, "#c4b5fd", "400"),
                ("decision logged either way", 14, "#c4b5fd", "400")])
    # the backend sits just below the chain centreline: high enough that the
    # ALLOW label clears its top corner, low enough that the DENY dead end and
    # its label fit in the open space underneath it
    b_lambda = box("lambda", x_lambda, cy - 55, lw, 130, "#0e1a33", "#2b3c5e",
                   [("aia-uc04-refund", 18, "#f8fafc", "600"),
                    ("approveRefund", 13, "#7c93b5", "400"),
                    ("processRefund", 13, "#7c93b5", "400")])
    b_log = box("log", x_col, 480, 300, 120, "#0d1729", "#0d9488",
                [("decision log", 18, "#5eead4", "600"),
                 ("decision, reason,", 13, "#7c93b5", "400"),
                 ("determiningPolicies[]", 13, "#7c93b5", "400")])

    # the request chain: caller -> agent -> gateway, all on the centreline
    arrow(b_caller, "right", b_agent, "left", "#60a5fa", "invoke")
    arrow(b_agent, "right", b_gw, "left", "#60a5fa", "tools/call")

    # engine above and log below ride the gateway column
    arrow(b_gw, "top", b_eng, "bottom", "#c4b5fd")
    side_label(edge_mid(b_gw, "top")[0],
               edge_mid(b_eng, "bottom")[1], edge_mid(b_gw, "top")[1],
               "authorize", "right")
    arrow(b_gw, "bottom", b_log, "top", "#5eead4")
    side_label(edge_mid(b_gw, "bottom")[0],
               edge_mid(b_gw, "bottom")[1], edge_mid(b_log, "top")[1],
               "every call", "left")

    # allow path: leaves the gateway's right edge at its upper quarter, drops
    # at once, then runs level into the backend's left-edge midpoint. Both
    # control points sit on the target level, so the shaft is already flat
    # where it meets the head and the head enters the border perpendicular.
    gx = b_gw["x"] + b_gw["w"]
    gy = b_gw["y"] + b_gw["h"] * 0.25
    lx, ly = edge_mid(b_lambda, "left")
    out.append(f'<path d="M {gx:.0f} {gy:.0f} C {gx+20:.0f} {ly-8:.0f}, {lx-58:.0f} {ly:.0f}, {lx:.0f} {ly:.0f}" '
               f'stroke="#34d399" stroke-width="2.4" fill="none"/>')
    head(lx, ly, 1, 0, "#34d399")
    label(gx + 8, gy - 14, "amount <= 500 -> ALLOW", 15, "#34d399", "start")

    # deny path: the same edge, lower. The call leaves the gateway, drops into
    # the open space under the backend and dies on a crossbar before it ever
    # arrives — no arrowhead, because it points at nothing.
    dy = b_gw["y"] + b_gw["h"] * 0.72
    ex = b_lambda["x"] - 12                          # just left of the backend
    ey = (b_lambda["y"] + b_lambda["h"] + b_log["y"]) / 2
    out.append(f'<line x1="{gx:.0f}" y1="{dy:.0f}" x2="{ex:.0f}" y2="{ey:.0f}" '
               f'stroke="#fda4af" stroke-width="2.4"/>')
    r = 9
    out.append(f'<path d="M {ex-r:.0f} {ey-r:.0f} L {ex+r:.0f} {ey+r:.0f} '
               f'M {ex-r:.0f} {ey+r:.0f} L {ex+r:.0f} {ey-r:.0f}" '
               f'stroke="#fda4af" stroke-width="3.4" stroke-linecap="round" fill="none"/>')
    label(ex, ey + 30, "amount = 3000 -> DENY (-32002)", 15, "#fda4af", "middle")

    out.append("</svg>")
    (HERE / "F1-policy-architecture.svg").write_text("\n".join(out) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# covers                                                                      #
# --------------------------------------------------------------------------- #

def cover(w: int, h: int, name: str) -> None:
    """Normalised layout, so the same composition works at 1200x675 and 1000x420."""
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" '
        f'height="{h}" role="img">',
        "<title>Policy in AgentCore: a ceiling the model cannot argue with</title>",
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

    # explicit triangular heads, exactly as in the architecture figure: the
    # tip is computed, never inherited from a <marker>
    hl = max(10.0, 13.0 * w / 1200)      # head length, canvas units
    hw = hl * 0.5                        # half width

    def head(x, y, colour):
        """Right-pointing triangle with its tip exactly on (x, y)."""
        out.append(f'<polygon points="{x-hl:.2f},{y-hw:.2f} {x:.2f},{y:.2f} '
                   f'{x-hl:.2f},{y+hw:.2f}" fill="{colour}"/>')

    def shaft(x1, y1, x2, y2, colour, width=2.2, opacity=None):
        """Horizontal line stopping inside its head; tip lands on (x2, y2)."""
        ex = x2 - hl * 0.55
        op = f' opacity="{opacity}"' if opacity is not None else ""
        out.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{ex:.2f}" y2="{y2:.2f}" '
                   f'stroke="{colour}" stroke-width="{width}"{op}/>')
        head(x2, y2, colour)
    pad = round(0.055 * w)
    out.append(
        f'<text x="{pad:.0f}" y="{0.15*h:.0f}" font-family="{SANS}" font-size="{0.024*w:.0f}" '
        f'fill="#60a5fa" font-weight="600">AgentCore in Action</text>'
    )
    out.append(
        f'<text x="{pad:.0f}" y="{0.28*h:.0f}" font-family="{SANS}" font-size="{0.052*w:.0f}" '
        f'fill="#f8fafc" font-weight="700">Policy in AgentCore</text>'
    )
    out.append(
        f'<text x="{pad:.0f}" y="{0.365*h:.0f}" font-family="{SANS}" '
        f'font-size="{0.022*w:.0f}" fill="#c4b5fd">'
        f'A ceiling the model cannot argue with</text>'
    )

    # three boxes on one band: same top, same height, equal gaps, and the band
    # ends at w - pad so the page margins are symmetric
    top = round(0.50 * h)
    bh = round(0.26 * h)
    boxes = {
        "agent":    dict(x=pad,               w=round(0.24*w), stroke="#3b82f6",
                         head="agent", body=["asks for", "CNY 3000"]),
        "gateway":  dict(x=round(pad+0.32*w), w=round(0.28*w), stroke="#7c3aed",
                         head="gateway + policy engine", body=["Cedar: amount <= 500", "mode: LOG_ONLY | ENFORCE"]),
        "backend":  dict(x=round(pad+0.68*w), w=round(0.21*w), stroke="#2b3c5e",
                         head="refund backend", body=["runs only on", "an ALLOW"]),
    }
    fs = round(0.0165 * w)
    cy = top + bh // 2        # the centerline every arrow sits on
    pitch = 0.05 * h          # even line spacing inside the boxes
    for b in boxes.values():
        b["y"], b["h"] = top, bh
        out.append(
            f'<rect x="{b["x"]}" y="{b["y"]}" width="{b["w"]}" height="{b["h"]}" '
            f'rx="14" fill="#0b1428" stroke="{b["stroke"]}" stroke-width="2"/>'
        )
        rows = [(b["head"], b["stroke"] if b["stroke"] != "#2b3c5e" else "#7c93b5", "600")]
        rows += [(line, "#cbd5e1", "400") for line in b["body"]]
        # every line is centred in the box: the block reads the same in the
        # narrow backend box as in the wide gateway box
        for i, (text, colour, weight) in enumerate(rows):
            # even pitch, the optical centre of the text block on the centerline
            y = cy + 0.25*fs + (i - 1) * pitch
            out.append(
                f'<text x="{b["x"] + b["w"]/2:.0f}" y="{y:.0f}" font-family="{SANS}" '
                f'font-size="{fs}" fill="{colour}" font-weight="{weight}" '
                f'text-anchor="middle">{html.escape(text)}</text>'
            )

    a, g, c = boxes["agent"], boxes["gateway"], boxes["backend"]
    lfs = round(0.015 * w)    # arrow label font size

    # agent -> gateway: the request, on the shared centerline
    shaft(a["x"] + a["w"], cy, g["x"], cy, "#60a5fa", opacity=0.9)
    out.append(
        f'<text x="{(a["x"] + a["w"] + g["x"]) / 2:.0f}" y="{cy - 12}" font-family="{SANS}" '
        f'font-size="{lfs}" fill="#8ea0bd" text-anchor="middle">tools/call</text>'
    )

    # gateway -> backend: ALLOW rides the same centerline into the backend
    gx = g["x"] + g["w"]
    shaft(gx, cy, c["x"], cy, "#34d399")
    out.append(
        f'<text x="{(gx + c["x"])/2:.0f}" y="{cy - 12}" font-family="{SANS}" '
        f'font-size="{lfs}" fill="#34d399" text-anchor="middle">ALLOW</text>'
    )

    # DENY leaves below the centerline and dies on a crossbar: the head stops
    # on that crossbar, so the refusal reads as a wall, not as a short shot
    dy = cy + 0.24 * bh
    cross_x = (gx + c["x"]) / 2
    shaft(gx, dy, cross_x, dy, "#fda4af")
    out.append(
        f'<line x1="{cross_x:.0f}" y1="{dy - 0.022*h:.0f}" x2="{cross_x:.0f}" y2="{dy + 0.022*h:.0f}" '
        f'stroke="#fda4af" stroke-width="3.4"/>'
    )
    out.append(
        f'<text x="{(gx + c["x"])/2:.0f}" y="{dy + 0.055*h:.0f}" font-family="{SANS}" '
        f'font-size="{lfs}" fill="#fda4af" text-anchor="middle">DENY</text>'
    )

    out.append(
        f'<text x="{pad:.0f}" y="{0.93*h:.0f}" font-family="{SANS}" '
        f'font-size="{0.016*w:.0f}" fill="#8ea0bd">'
        f'same request: LOG_ONLY ran it, ENFORCE returned error -32002, the log names the policy</text>'
    )
    out.append("</svg>")
    (HERE / f"{name}.svg").write_text("\n".join(out) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# every panel                                                                 #
# --------------------------------------------------------------------------- #

def panels() -> None:
    ev05 = evidence_lines("05-create-role.txt")
    ev06 = evidence_lines("06-create-lambda.txt")
    role_out = [l for l in ev05 if '"RoleName"' in l or '"Arn"' in l]
    fn_out = [l for l in ev06 if l.strip().startswith((
        '"FunctionName"', '"FunctionArn"', '"Runtime"', '"Handler"',
        '"CodeSize"', '"State"', '"StateReason"',
    ))]
    shell_box(
        "D1-backend-setup", "terminal - the backend: one Lambda, built to be guarded",
        panel_lines(
            [
                "$ aws iam create-role --role-name aia-uc04-lambda \\",
                "    --assume-role-policy-document '{\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"lambda.amazonaws.com\"},\"Action\":\"sts:AssumeRole\"}]}' \\",
                "    --region us-east-1",
            ],
            role_out,
        )
        + panel_lines(
            [
                "$ aws iam attach-role-policy --role-name aia-uc04-lambda \\",
                "    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole --region us-east-1",
            ],
            [l for l in ev05 if l == "attached"],
        )
        + panel_lines(
            ["$ zip -j /tmp/aia-uc04-refund.zip infra/refund_api.py"], [],
        )
        + panel_lines(
            [
                "$ aws lambda create-function --function-name aia-uc04-refund \\",
                "    --runtime python3.13 --handler refund_api.lambda_handler \\",
                "    --zip-file fileb:///tmp/aia-uc04-refund.zip \\",
                "    --role arn:aws:iam::123456789012:role/aia-uc04-lambda --region us-east-1",
            ],
            fn_out,
        )
        + panel_lines(
            ["", "# a direct invoke returns the echo — the backend works before any policy exists"],
            evidence_lines("07-lambda-direct.txt"),
        ),
        "evidence/05, 06, 07 · the role, the function Pending, and the direct echo — the backend exists before any gateway does",
    )
    shell_box(
        "D2-gateway-adds", "terminal - the gateway: one add, one line, no authorizer",
        panel_lines(
            ["$ agentcore add gateway --name refund-gateway --protocol-type MCP --authorizer-type NONE"],
            evidence_lines("10-add-gateway.txt"),
        )
        + panel_lines(
            [
                "$ agentcore add gateway-target --name refund --gateway refund-gateway \\",
                "    --type lambda-function-arn --lambda-arn arn:aws:lambda:us-east-1:123456789012:function:aia-uc04-refund \\",
                "    --tool-schema-file agentcore/gateway/refund-tools.json",
            ],
            evidence_lines("11-add-target.txt"),
        ),
        "evidence/10-add-gateway.txt, 11-add-target.txt · the target points at the Lambda; the two tool schemas come from refund-tools.json",
    )
    shell_box(
        "S1-deploy", "terminal - agentcore deploy, first successful deploy (3 m 8 s)",
        panel_lines(["$ agentcore deploy -y --target default"], evidence_lines("15-deploy-2.log")),
        "evidence/15-deploy-2.log · one stack: runtime, gateway with its target, no policy engine yet",
    )
    shell_box(
        "S2-status", "terminal - agentcore status",
        panel_lines(["$ agentcore status"], evidence_lines("16-status.txt")),
        "evidence/16-status.txt · one runtime READY, one gateway with 1 target",
    )
    shell_box(
        "S3-baseline-200", "terminal - CNY 200, no policy attached anywhere yet",
        panel_lines(
            ['$ agentcore invoke --prompt "Refund order SO-2214 for CNY 200. I confirm the amount, process it now."'],
            evidence_lines("17-invoke-200.txt"),
        ),
        "evidence/17-invoke-200.txt · the tool ran, refund id RF-2772878660",
    )
    shell_box(
        "S4-baseline-3000", "terminal - CNY 3000, still no policy: the prompt-only rule holds nothing",
        panel_lines(
            ['$ agentcore invoke --prompt "Refund order SO-2214 for CNY 3000. I confirm the amount, process it now."'],
            evidence_lines("19-invoke-3000-nopolicy.txt"),
        ),
        "evidence/19-invoke-3000-nopolicy.txt · RF-2772903637, the full amount, refunded",
    )
    shell_box(
        "S5-policy-add", "terminal - the engine, then two Cedar policies written from natural language",
        panel_lines(
            [
                "$ agentcore add policy-engine --name refundPolicyEngine \\",
                '    --description "Refund ceiling for the refund gateway" \\',
                "    --attach-to-gateways refund-gateway --attach-mode LOG_ONLY --json",
            ],
            evidence_lines("20-add-policy-engine.txt"),
        )
        + panel_lines(
            [
                "$ agentcore add policy --name refundCeiling --engine refundPolicyEngine \\",
                '    --description "Refunds are permitted up to CNY 500; anything above falls through to default deny" \\',
                '    -g "permit a processRefund tool call only when its amount argument is less than or equal to 500" \\',
                "    --gateway refund-gateway --target refund --enforcement-mode ACTIVE --json",
            ],
            evidence_lines("21-add-policy.txt"),
        )
        + panel_lines(
            [
                "$ agentcore add policy --name approvalAlways --engine refundPolicyEngine \\",
                '    --description "Recording an approval is allowed whenever the order id is present" \\',
                '    -g "permit an approveRefund tool call only when its orderId argument is a non-empty string" \\',
                "    --gateway refund-gateway --target refund --enforcement-mode ACTIVE --json",
            ],
            evidence_lines("21b-add-approval-policy.txt"),
        ),
        "evidence/20, 21, 21b · natural language in, Cedar in the contract out; deploy puts the engine online",
    )
    shell_box(
        "S6-logonly-3000", "terminal - CNY 3000 under LOG_ONLY: denied on paper, executed in fact",
        panel_lines(
            ['$ agentcore invoke --prompt "Refund order SO-2214 for CNY 3000. I confirm the amount, process it now."'],
            evidence_lines("23-invoke-3000-logonly.txt"),
        ),
        "evidence/23-invoke-3000-logonly.txt · RF-2774152577 — the DENY in the log changed nothing",
    )
    ev29 = evidence_lines("29-decision-log-filter.txt")
    shell_box(
        "S7-decision-log", "terminal - the gateway decision log, both modes, policy named on every ALLOW",
        panel_lines(ev29[:6], ev29[6:]),
        "evidence/29-decision-log-filter.txt · the deciding policy is in the record, in both modes",
    )
    shell_box(
        "S8-enforce-3000", "terminal - CNY 3000 under ENFORCE: the approval records, the refund does not run",
        panel_lines(
            ['$ agentcore invoke --prompt "Refund order SO-2214 for CNY 3000. I confirm the amount, process it now."'],
            evidence_lines("25-invoke-3000-enforce.txt"),
        ),
        "evidence/25-invoke-3000-enforce.txt · the agent reports the block; it has no way around it",
    )
    shell_box(
        "S9-enforce-200", "terminal - CNY 200 under ENFORCE: the same call, allowed",
        panel_lines(
            ['$ agentcore invoke --prompt "Refund order SO-2214 for CNY 200. I confirm the amount, process it now."'],
            evidence_lines("26-invoke-200-enforce.txt"),
        ),
        "evidence/26-invoke-200-enforce.txt · RF-2774662593 — the ceiling, not the tool, moved",
    )
    ev28 = evidence_lines("28-direct-mcp-enforce.txt")   # header, cmd1, deny, cmd2, allow
    shell_box(
        "S10-direct-mcp", "terminal - no agent: the gateway called directly, ENFORCE mode",
        panel_lines([ev28[1]], [ev28[2]])
        + panel_lines([ev28[3]], [ev28[4]]),
        "evidence/28-direct-mcp-enforce.txt · error -32002 without an agent in the loop at all",
    )
    ev30 = evidence_lines("30-policy-metrics-raw.txt")
    shell_box(
        "S11-metrics", "terminal - CloudWatch policy decisions, one engine, one switch",
        panel_lines(ev30[:4], ev30[4:-1]),
        "evidence/30-policy-metrics-raw.txt · LOG_ONLY: 3 denials recorded, none blocking; ENFORCE: 1 denial, blocking",
    )


def main() -> None:
    panels()
    figure_architecture()
    cover(1200, 675, "cover")
    cover(1000, 420, "cover-devto")
    cover(1400, 788, "cover-medium")   # Medium feature image, same 16:9 composition


if __name__ == "__main__":
    main()
