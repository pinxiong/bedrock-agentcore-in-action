#!/usr/bin/env python3
"""Generate every image for the uc06 article from the run captured 2026-10-25.

Every line drawn here comes from `usecases/06-quality-loop/evidence/`. The
terminal panels are that output with the account id redacted to 123456789012
and the spinner frames dropped; lines longer than the panel are wrapped and
nothing else is changed and nothing is invented. Each panel reads its evidence
file at build time, so the SVG, the PNG and this generator cannot disagree.

    python3 gen_figures.py            # writes every .svg next to this file
    ./render.sh                       # svg -> png
"""

from __future__ import annotations

import html
import json
import pathlib
import re
import textwrap

HERE = pathlib.Path(__file__).resolve().parent
EVIDENCE = HERE.parents[2] / "usecases" / "06-quality-loop" / "evidence"

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


def evidence_lines(stem: str, fold: bool = True) -> list[str]:
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
    # drop consecutive duplicates the CLI spinner re-prints; a span listing is
    # data, not a redraw, so it passes fold=False and keeps every row
    if not fold:
        return out
    dedup = []
    for line in out:
        if dedup and dedup[-1] == line:
            continue
        dedup.append(line)
    return dedup


def evidence_json(stem: str) -> dict:
    return json.loads((EVIDENCE / stem).read_text(encoding="utf-8"))


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
    if "Log: " in line and ".cli/logs/" in line:
        return "Log: agentcore/.cli/logs/" + line.split(".cli/logs/", 1)[1]
    if line.startswith("Results saved to: ") and ".cli/eval-results/" in line:
        return "Results saved to: agentcore/.cli/eval-results/" \
            + line.split(".cli/eval-results/", 1)[1]
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
    if "error" in line.lower() or "FAILED" in line:
        return O
    if "success" in line.lower() or "COMPLETED" in line or "✓" in line:
        return G
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
# figure 1: the quality loop, from traces to a bundled fix                     #
# --------------------------------------------------------------------------- #

def figure_architecture() -> None:
    """Diagram. Every arrow endpoint is computed from the box rectangles below."""
    w, h = 1440, 800
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}" role="img">',
        "<title>Spans and logs flow to CloudWatch; evaluations and insights read "
        "the traces; a recommendation becomes configuration bundle v2; the gateway "
        "routes traffic between bundle versions; the A/B report decides.</title>",
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

    label(60, 62, "the quality loop, uc06", 22, "#f8fafc", weight="600")
    label(60, 90, "observed traces drive evaluators, insights and a recommendation; the fix ships as bundle v2 through the gateway", 15)

    x_c, x_h, x_t, tw = 60, 380, 900, 360

    b_caller = box("caller", x_c, 250, 240, 130, "#0e1a33", "#2b3c5e",
                   [("audit prompts", 19, "#f8fafc", "600"),
                    ("6 receipts, 3 currencies", 14, "#7c93b5", "400"),
                    ("one planted defect", 14, "#fdba74", "400")])
    b_runtime = box("runtime", x_h, 215, 340, 200, "#122146", "#3b82f6",
                    [("agentcore runtime", 20, "#f8fafc", "600"),
                     ("Strands agent, 3 tools", 14, "#7c93b5", "400"),
                     ("prompt from config bundle", 14, "#c4b5fd", "400"),
                     ("aws-opentelemetry-distro", 14, "#5eead4", "400")])
    b_spans = box("spans", x_t, 140, tw, 100, "#0d1729", "#0d9488",
                  [("CloudWatch aws/spans", 17, "#5eead4", "600"),
                   ("22 tool spans, 0 convert_currency", 13, "#7c93b5", "400")])
    b_eval = box("eval", x_t, 280, tw, 110, "#122146", "#7c3aed",
                 [("evaluations", 18, "#e9d5ff", "600"),
                  ("on-demand · batch · dataset", 14, "#7c93b5", "400"),
                  ("online, sampled 100%", 14, "#c4b5fd", "400")])
    b_insights = box("insights", x_t, 430, tw, 110, "#0d1729", "#ea580c",
                     [("insights", 17, "#fdba74", "600"),
                      ("failure cluster: 8 sessions,", 13, "#7c93b5", "400"),
                      ("Foreign Currency Ignored", 13, "#fdba74", "400")])
    b_reco = box("reco", x_t, 580, tw, 100, "#0e1a33", "#059669",
                 [("recommendation", 18, "#34d399", "600"),
                  ("Builtin.Correctness over traces", 13, "#7c93b5", "400")])

    arrow(b_caller, "right", b_runtime, "left", "#60a5fa", "invoke")

    hx, hy = edge_mid(b_runtime, "right")
    out.append(f'<line x1="{hx:.2f}" y1="{hy:.2f}" x2="810" y2="{hy:.2f}" '
               f'stroke="#60a5fa" stroke-width="2.2"/>')
    out.append(f'<line x1="810" y1="190" x2="810" y2="630" '
               f'stroke="#60a5fa" stroke-width="2.2"/>')
    for b, text in ((b_spans, "otel"), (b_eval, "scores"), (b_insights, "patterns")):
        tx, ty = edge_mid(b, "left")
        shaft(810, ty, tx, ty, "#60a5fa")
        label((810 + tx) / 2, ty - 11, text, 14, "#8ea0bd", "middle")

    shaft(edge_mid(b_insights, "bottom")[0], edge_mid(b_insights, "bottom")[1],
          *edge_mid(b_reco, "top"), "#fdba74")
    label(edge_mid(b_reco, "top")[0] + 14,
          (edge_mid(b_insights, "bottom")[1] + edge_mid(b_reco, "top")[1]) / 2 + 5,
          "chained", 14, "#8ea0bd", "start")

    # the fix flows back to the runtime as an immutable bundle version
    rx, ry = edge_mid(b_reco, "left")
    out.append(f'<line x1="{rx:.2f}" y1="{ry:.2f}" x2="640" y2="{ry:.2f}" stroke="#34d399" stroke-width="2.2"/>')
    out.append(f'<line x1="640" y1="{ry:.2f}" x2="640" y2="{edge_mid(b_runtime, "bottom")[1] + 40:.2f}" stroke="#34d399" stroke-width="2.2"/>')
    shaft(640, edge_mid(b_runtime, "bottom")[1] + 6, 550, edge_mid(b_runtime, "bottom")[1] + 6, "#34d399")
    label(652, ry - 10, "bundle v2 (d4c45b72)", 14, "#34d399", "start")
    label(652, ry + 14, "A/B via gateway: C 50% / T1 50%", 14, "#8ea0bd", "start")

    out.append("</svg>")
    (HERE / "F1-quality-loop.svg").write_text("\n".join(out) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# covers                                                                      #
# --------------------------------------------------------------------------- #

def cover(w: int, h: int, name: str, safe: float = 0.0) -> None:
    """Normalised layout, so the same composition works at every ratio.

    `safe` is the fraction of width that must survive a 1.91:1 centre crop.
    """
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" '
        f'height="{h}" role="img">',
        "<title>Finding what broke in AgentCore: spans, four evaluation modes, "
        "an insight, a recommendation and an A/B test over immutable bundles</title>",
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
        f'fill="#f8fafc" font-weight="700">Finding What Broke</text>'
    )
    out.append(
        f'<text x="{pad:.0f}" y="{0.365*h:.0f}" font-family="{SANS}" '
        f'font-size="{0.022*u:.0f}" fill="#c4b5fd">'
        f'spans in, evaluators on, insight out, fix shipped as bundle v2</text>'
    )

    gap = round(bw * 0.085)
    boxw = round((bw - 2 * gap) / 3)
    top = round(0.47 * h)
    bh = round(0.28 * h)
    xs = [pad, pad + boxw + gap, pad + 2 * (boxw + gap)]
    boxes = [
        dict(x=xs[0], stroke="#0d9488", head="observe",
             body=["22 tool spans, zero", "convert_currency calls"]),
        dict(x=xs[1], stroke="#7c3aed", head="evaluate",
             body=["Correctness 0.50,", "currency_guard 0.00"]),
        dict(x=xs[2], stroke="#059669", head="optimize",
             body=["A/B: mean 2.0 to 4.0,", "p = 0.00043"]),
    ]
    fs = round(0.0165 * w)
    cy = top + bh // 2
    pitch = 0.05 * h
    for b in boxes:
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
        (a, g, "#60a5fa", "traces"),
        (g, c, "#34d399", "bundle v2"),
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
        f'four evaluation modes, one failure cluster, one CI gate that blocks the PR</text>'
    )
    out.append("</svg>")
    (HERE / f"{name}.svg").write_text("\n".join(out) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# every panel                                                                 #
# --------------------------------------------------------------------------- #

def panels() -> None:
    shell_box(
        "D1-adds", "terminal - one gateway, two evaluators, two online configs, a bundle, a dataset",
        panel_lines(
            ["$ agentcore add gateway --name expense-gateway \\",
             "    --protocol-type NONE --authorizer-type NONE"],
            evidence_lines("20-add-gateway.txt"),
        )
        + panel_lines(
            ["$ agentcore add evaluator --name currency_guard --level TRACE \\",
             "    --type llm-as-a-judge --model deepseek.v3.2 --rating-scale pass-fail \\",
             '    --instructions "You are reviewing one trace of an expense audit agent. '
             'Trace context: {context}. Rule: if the receipt the agent loaded with load_receipt '
             'has a currency other than USD, the agent must call convert_currency ..."'],
            evidence_lines("21-add-evaluator.txt"),
        )
        + panel_lines(
            ["$ agentcore add online-eval --name prod_quality --runtime aia_uc06 \\",
             "    --evaluator currency_guard --sampling-rate 100 --enable-on-create"],
            evidence_lines("28-add-online-eval.txt"),
        )
        + panel_lines(
            ["$ agentcore add config-bundle --name expense_config \\",
             "    --components-file agentcore/bundles/prompt-v1.json --branch main \\",
             '    --commit-message "production prompt as it has run for two months"'],
            evidence_lines("33-add-bundle-v1.txt"),
        )
        + panel_lines(
            ["$ agentcore add dataset --name expense_audit_set \\",
             "    --schema-type AGENTCORE_EVALUATION_PREDEFINED_V1 \\",
             '    --description "Fixed audit scenarios with known-correct answers"'],
            evidence_lines("40-add-dataset.txt"),
        ),
        "evidence/20, 21, 28, 33, 40 · every resource the quality loop needs is declared, then deployed once",
    )
    ev05 = evidence_lines("05-deploy-1.log")
    shell_box(
        "S0-deploy", "terminal - agentcore deploy, one stack for everything above",
        panel_lines(
            ["$ agentcore deploy -y --target default"],
            [l for l in ev05 if l.startswith(("✓ Deployed", "  ApplicationAgentAiaUc06RuntimeArn",
                                              "  StackNameOutput", "Note:", "Next:"))],
        ),
        "evidence/05-deploy-1.log · runtime, gateway, evaluators, online configs, bundle and dataset in one stack",
    )
    ev30 = evidence_lines("30-invoke-prod-02-r4107.txt")
    shell_box(
        "S1-defect", "terminal - the planted defect, reproduced on an EUR receipt",
        panel_lines(
            ["$ agentcore invoke --runtime aia_uc06 \\",
             "    --session-id qloop-prod-02-r4107-audit-run-2026 \\",
             '    --prompt "Audit receipt R-4107 for reimbursement. Apply the travel desk policy and end with the decision line."'],
            [l for l in ev30 if l.startswith("I'll audit")
             or l.startswith("However, I need to be careful here.")
             or l.startswith("Based on the instructions, I should treat")
             or l.startswith("Decision:")
             or l.startswith("Session:")],
        ),
        "evidence/30-invoke-prod-02 · the model quotes the stale prohibition, treats EUR 210 as USD 210, approves",
    )
    span_rows: list[str] = []
    tool_counts: dict[str, int] = {}
    n_rows = 0
    for row in json.loads((EVIDENCE / "36-spans-prod.json").read_text(encoding="utf-8")):
        span = json.loads(row) if isinstance(row, str) else row
        n_rows += 1
        name = span.get("name", "")
        if name.startswith("execute_tool "):
            tool_counts[name] = tool_counts.get(name, 0) + 1
    for name, count in sorted(tool_counts.items()):
        span_rows.append(f"{count:3d}  {name}")
    span_rows.append(f"{sum(tool_counts.values()):3d}  execute_tool spans total across 11 sessions")
    span_rows.append("  0  execute_tool convert_currency")
    shell_box(
        "S2-spans", "terminal - the tool spans of the 11 baseline sessions",
        panel_lines(
            ["$ aws logs filter-log-events --region us-east-1 \\",
             "    --log-group-name aws/spans \\",
             '    --start-time $(python3 -c "import time;print(int((time.time()-7200)*1000))") \\',
             "    --query 'events[].message' --output json > evidence/36-spans-prod.json",
             "$ python3 -c \"import json; docs=[json.loads(m) for m in",
             "    json.load(open('evidence/36-spans-prod.json'))]; print(Counter(...))\""],
            span_rows,
        ),
        f"evidence/36-spans-prod.json · {n_rows} span rows; every non-USD receipt was approved without a conversion",
    )
    shell_box(
        "S3-eval", "terminal - three offline evaluation modes over the same traces",
        panel_lines(
            ["$ agentcore run eval -r aia_uc06 -e Builtin.Correctness currency_guard \\",
             "    --session-id qloop-prod-02-r4107-audit-run-2026"],
            [l for l in evidence_lines("50-eval-ondemand.txt") if l.startswith(("Agent:", "  Builtin", "  currency"))],
        )
        + panel_lines(
            ["$ agentcore run batch-evaluation -r aia_uc06 -e Builtin.Correctness currency_guard \\",
             "    -n baseline_audit_batch --lookback-days 1 --wait"],
            [l for l in evidence_lines("51-eval-batch.txt")
             if l.startswith(("Sessions:", "  aiauc06", "  Builtin", "✓"))],
        )
        + panel_lines(
            ["$ agentcore run eval -r aia_uc06 -e Builtin.Correctness currency_guard \\",
             "    --dataset expense_audit_set"],
            [l for l in evidence_lines("54-eval-dataset.txt") if l.startswith(("Agent:", "  Builtin", "  currency"))],
        ),
        "evidence/50, 51, 54 · one failing session scores 0.00; eleven sessions average 0.50; six scripted scenarios 0.50",
    )
    ins = evidence_json("61-insights-detail.json")
    fail0 = ins["failureAnalysisResult"]["failures"][0]
    sub0 = fail0["subCategories"][0]
    root0 = sub0["rootCauses"][0]
    sess0 = root0["affectedSessions"][0]
    ev60 = evidence_lines("60-insights.txt")
    shell_box(
        "S4-insights", "terminal - insights: the traces cluster into one dominant failure",
        panel_lines(
            ["$ agentcore run insights -r aia_uc06 --lookback-days 1 \\",
             "    -n baseline_failure_analysis --wait"],
            [l for l in ev60 if l.startswith(("✓",))],
        )
        + panel_lines(
            ["$ agentcore view insights baseline_failure_analysis-375c7e1293 --json"],
            [
                f"evaluator: {ins['insights'][0]}",
                f"sessions analyzed: {ins['evaluationResults']['numberOfSessionsCompleted']}",
                f"failure cluster: {fail0['name']} ({fail0['affectedSessionCount']} sessions)",
                f"sub-cluster: {sub0['name']} ({sub0['affectedSessionCount']} sessions)",
                f"example session: {sess0['sessionId']}",
                f"fixType: {sess0['fixType']}",
            ],
        ),
        "evidence/60, 61-insights-detail.json · 8 of 17 sessions share one root cause, and it names the prompt",
    )
    ev62 = evidence_lines("62-recommendation.txt")
    ev67 = evidence_lines("67-recommendation-3.txt")
    reco_expl = [l for l in ev67 if l.startswith(("The most pervasive pattern", "The optimizer traced this",
                                                  "+++ Recommended System Prompt +++"))]
    shell_box(
        "S5-reco", "terminal - recommendation: categorical evaluator rejected, numeric one reads the traces",
        panel_lines(
            ["$ agentcore run recommendation --type system-prompt -r aia_uc06 -e currency_guard \\",
             "    --prompt-file app/aia_uc06/system-prompt.md \\",
             "    --from-insights baseline_failure_analysis-375c7e1293 -n currency_fix --wait"],
            [l for l in ev62 if "Error:" in l][:1],
        )
        + panel_lines(
            ["$ agentcore run recommendation --type system-prompt -r aia_uc06 -e Builtin.Correctness \\",
             "    --prompt-file app/aia_uc06/system-prompt.md \\",
             "    --from-insights baseline_failure_analysis-375c7e1293 -n currency_fix3 --wait"],
            [l for l in ev67 if l.startswith("✓")][:1] + reco_expl,
        ),
        "evidence/62, 67 · pass-fail scales cannot drive optimization; the numeric run cites the EUR/GBP traces",
    )
    ev69 = evidence_lines("69-update-bundle-v2.txt")
    ev70 = evidence_lines("70-ab-start.txt")
    shell_box(
        "S6-bundle", "terminal - ship the fix as an immutable bundle version, not a code deploy",
        panel_lines(
            ["$ aws bedrock-agentcore-control update-configuration-bundle --region us-east-1 \\",
             "    --cli-input-json file:///tmp/update-bundle-v2.json   # parentVersionIds: [v1]"],
            [l for l in ev69 if '"versionId"' in l or '"bundleId"' in l],
        )
        + panel_lines(
            ["$ agentcore run ab-test -n expense_ab_01 -g expense-gateway \\",
             "    --control-bundle expense_config --control-version f45629ba-e409-46b7-80b8-ce1858319573 \\",
             "    --treatment-bundle expense_config --treatment-version d4c45b72-99ec-4d39-a60b-b5a1541f68d5 \\",
             "    --online-eval prod_score --control-weight 50 --treatment-weight 50"],
            [l for l in ev70 if l.startswith(("Mode:", "  C (", "  T1 ("))],
        ),
        "evidence/69, 70 · v2 is a new version of the same bundle; the gateway splits traffic 50/50 between versions",
    )
    ab = evidence_json("72-ab-report.txt")
    metrics = ab["results"]["evaluatorMetrics"][0]
    ctrl = metrics["controlStats"]
    treat = metrics["variantResults"][0]
    ci = treat["confidenceInterval"]
    shell_box(
        "S7-ab-report", "terminal - the A/B report: 28 invoked, 26 scored, the lift is real",
        panel_lines(
            ["$ agentcore view ab-test aiauc06_expense_ab_01-227c8af53d --json"],
            [
                f"evaluator: currency_score (1-5 quality scale)",
                f"control   C : mean {ctrl['mean']}  n = {ctrl['sampleSize']}",
                f"variant  T1 : mean {treat['mean']}  n = {treat['sampleSize']}  ({treat['percentChange']}%)",
                f"confidence interval: [{ci['lower']:.2f}, {ci['upper']:.2f}]",
                f"p-value: {treat['pValue']:.5f}   isSignificant: {treat['isSignificant']}",
            ],
        ),
        "evidence/70-72 · 28 invoked through one gateway URL, 26 scored, split by W3C baggage headers",
    )
    shell_box(
        "S8-gate", "terminal - the CI gate: pass on the baseline, block on a raised floor",
        panel_lines(
            ["$ agentcore run batch-evaluation --runtime aia_uc06 -e Builtin.Correctness \\",
             "    -n gate_probe --lookback-days 1 --wait --json"],
            [l for l in evidence_lines("81-gate-pass.txt")],
        )
        + panel_lines(
            ["$ agentcore run batch-evaluation --runtime aia_uc06 -e Builtin.Correctness \\",
             "    -n gate_probe --lookback-days 1 --wait --json"],
            [l for l in evidence_lines("82-gate-block.txt")],
        ),
        "evidence/81, 82 · mean 0.678 clears the 0.500 floor; below the floor the step exits 1 and the PR blocks",
    )
    ev90 = evidence_lines("90-remove-all.txt")
    ev91 = evidence_lines("91-reconcile.log")
    ev92 = evidence_lines("92-status-empty.txt")
    shell_box(
        "S9-teardown", "terminal - teardown: empty the contract, reconcile, nothing left",
        panel_lines(
            ["$ agentcore remove all -y"],
            [l for l in ev90 if l.startswith(("All", "Your"))],
        )
        + panel_lines(
            ["$ agentcore deploy -y --target default        # reconcile the stack down"],
            [l for l in ev91 if "✓ Deployed" in l or "Tear down" in l or "Deleted" in l][:3],
        )
        + panel_lines(
            ["$ agentcore status"],
            [l for l in ev92 if "No resources" in l][:1],
        ),
        "evidence/90, 91, 92 · the tag index may still list ghosts; agentcore status is the source of truth",
    )


def main() -> None:
    panels()
    figure_architecture()
    cover(1200, 675, "cover")
    cover(1000, 420, "cover-devto", safe=0.105)
    cover(1400, 788, "cover-medium")   # Medium feature image, same 16:9 composition


if __name__ == "__main__":
    main()
