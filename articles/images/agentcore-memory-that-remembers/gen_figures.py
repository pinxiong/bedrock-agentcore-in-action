#!/usr/bin/env python3
"""Generate every image for the uc02 article from the run captured on 2026-10-18.

Every line drawn here comes from `usecases/02-memory/evidence/`, files 20 to 44.
The terminal panels are that output with the account id redacted to 123456789012
and the repeated spinner dropped; lines longer than the panel are wrapped and
nothing else is changed and nothing is invented. Each panel reads its evidence
file at build time, so the SVG, the PNG and this generator cannot disagree.

    python3 gen_figures.py            # writes every .svg next to this file
    ./render.sh                       # svg -> png
"""

from __future__ import annotations

import html
import pathlib
import textwrap

HERE = pathlib.Path(__file__).resolve().parent
EVIDENCE = HERE.parents[2] / "usecases" / "02-memory" / "evidence"

BG0, BG1 = "#0a1024", "#0d1c3a"
BLUE, PURPLE, ORANGE, GREEN, RED, TEAL = (
    "#2563eb", "#7c3aed", "#ea580c", "#059669", "#e11d48", "#0d9488",
)
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
SANS = "Inter, Helvetica Neue, Arial, sans-serif"

W, G, O, T, D, S = "#f8fafc", "#34d399", "#fdba74", "#5eead4", "#7c93b5", "#cbd5e1"

PANEL_WIDTH = 112          # characters; everything longer is wrapped
WRAP_INDENT = "        "


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


def evidence_body(stem: str) -> list[str]:
    """The captured output in an evidence file, header lines removed."""
    lines = (EVIDENCE / stem).read_text(encoding="utf-8").splitlines()
    try:
        start = lines.index("") + 1
    except ValueError:  # no blank line after the header
        start = 0
    return [line.rstrip() for line in lines[start:] if line.strip()]


def short(line: str) -> str:
    """Drop the local absolute path the CLI prints for its own log file."""
    import re
    if re.match(r"^\S+ .* \d+\.\d+s user .* total$", line):
        return ""          # the time(1) wrapper, not the command's output
    if line.startswith("Log: ") and ".cli/logs/" in line:
        return "Log: agentcore/.cli/logs/" + line.split(".cli/logs/", 1)[1]
    return line


def panel_lines(command: list[str], body: list[str]) -> list[tuple[str, str]]:
    """A `$ command` line, then the captured output."""
    lines = [(line, S) for line in command]
    for line in body:
        text = short(line)
        if not text:
            continue
        if text.startswith("Session:") or text.startswith("To resume:"):
            lines.append((text, T))
        elif text.startswith("Log:") or text.startswith("Note:") or text.startswith("Next:"):
            lines.append((text, D))
        elif text.startswith("Invoking agent"):
            lines.append((text, D))
        elif text.startswith("$ "):
            lines.append((text, S))
        else:
            lines.append((text, W))
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
# figure 1: one memory resource, two halves, three namespaces                 #
# --------------------------------------------------------------------------- #

def figure_architecture() -> None:
    w, h = 1440, 760
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}" role="img">',
        "<title>One AgentCore Memory resource split into a short-term event log and three "
        "long-term namespaces, every namespace keyed by actor id.</title>",
        "<defs>",
        '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{BG0}"/><stop offset="1" stop-color="{BG1}"/></linearGradient>',
        '<radialGradient id="g1" cx="0.08" cy="0.02" r="0.8">'
        f'<stop offset="0" stop-color="{BLUE}" stop-opacity="0.22"/>'
        f'<stop offset="1" stop-color="{BLUE}" stop-opacity="0"/></radialGradient>',
        '<radialGradient id="g2" cx="0.92" cy="1.0" r="0.8">'
        f'<stop offset="0" stop-color="{PURPLE}" stop-opacity="0.20"/>'
        f'<stop offset="1" stop-color="{PURPLE}" stop-opacity="0"/></radialGradient>',
        '<marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        'markerHeight="7" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#60a5fa"/></marker>',
        '<marker id="ahp" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        'markerHeight="7" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#c4b5fd"/></marker>',
        "</defs>",
        f'<rect width="{w}" height="{h}" fill="url(#bg)"/>',
        f'<rect width="{w}" height="{h}" fill="url(#g1)"/>',
        f'<rect width="{w}" height="{h}" fill="url(#g2)"/>',
    ]

    def label(x: int, y: int, text: str, size: int = 16,
              colour: str = "#8ea0bd", anchor: str = "start", weight: str = "400") -> None:
        out.append(
            f'<text x="{x}" y="{y}" font-family="{SANS}" font-size="{size}" fill="{colour}" '
            f'text-anchor="{anchor}" font-weight="{weight}">{html.escape(text)}</text>'
        )

    def box(x: int, y: int, bw: int, bh: int, fill: str, stroke: str, line1: str,
            line2: str = "", lsize: int = 20, ssize: int = 15,
            lcolour: str = "#f8fafc", scolour: str = "#7c93b5", line3: str = "") -> None:
        out.append(
            f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="14" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="1.6"/>'
        )
        rows = [line1] + ([line2] if line2 else []) + ([line3] if line3 else [])
        total = len(rows)
        start = y + bh / 2 - (total - 1) * 13 + 6
        for i, text in enumerate(rows):
            out.append(
                f'<text x="{x + bw/2:.0f}" y="{start + i*26:.0f}" font-family="{SANS}" '
                f'font-size="{lsize if i == 0 else ssize:.0f}" '
                f'fill="{lcolour if i == 0 else scolour}" '
                f'text-anchor="middle">{html.escape(text)}</text>'
            )

    def arrow(x1: int, y1: int, x2: int, y2: int, colour: str = "#60a5fa",
              marker: str = "ah", dash: str = "") -> None:
        style = f' stroke-dasharray="{dash}"' if dash else ""
        out.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{colour}" '
            f'stroke-width="2.2"{style} marker-end="url(#{marker})"/>'
        )

    label(60, 62, "the deployed use case, uc02", 22, "#f8fafc", weight="600")
    label(60, 90, "every resource below is tagged Project=agentcore-in-action, UseCase=02", 15)

    box(46, 140, 250, 120, "#0e1a33", "#2b3c5e", "caller", "agentcore invoke", 20, 15)
    label(70, 240, "--user-id <actor>", 15, "#cbd5e1")
    label(70, 262, "--session-id <uuid>", 15, "#cbd5e1")

    box(380, 125, 300, 230, "#122146", "#3b82f6", "AgentCore Runtime", "aia_uc02",
        21, 15, "#f8fafc", "#7c93b5", "app/aia_uc02, CodeZip, PYTHON_3_13")

    arrow(296, 200, 374, 200)
    label(335, 188, "invoke", 13, "#64748b", anchor="middle")

    box(380, 420, 300, 90, "#0e1a33", "#2b3c5e", "Bedrock", "deepseek.v3.2", 18, 14)
    arrow(530, 355, 530, 414, "#60a5fa", "ah", "5 5")
    label(544, 390, "converse", 14, "#64748b")

    out.append('<rect x="780" y="112" width="614" height="560" rx="18" fill="#101c37" '
               'stroke="#7c3aed" stroke-width="2"/>')
    label(804, 152, "AgentCore Memory  aia_uc02_mem", 20, "#c4b5fd", weight="600")
    label(804, 178, "eventExpiryDuration 30 d, three extraction strategies", 14, "#7c93b5")

    arrow(684, 234, 778, 234, "#5eead4")
    label(690, 222, "write", 14, "#5eead4")
    box(804, 190, 566, 78, "#0d1729", "#0d9488", "short term", "CreateEvent, one event per turn",
        18, 13, "#5eead4", "#7c93b5", "append-only, keyed by (actor, session)")

    out.append('<path d="M 1050 268 L 1050 308" stroke="#ea580c" stroke-width="2.4" '
               'marker-end="url(#ah)" fill="none"/>')
    label(1062, 296, "async extraction", 14, "#fdba74")

    arrow(778, 339, 686, 339, "#c4b5fd", "ahp", "6 5")
    label(690, 327, "read", 14, "#c4b5fd")

    ns_rows = [
        ("USER_PREFERENCE", "/users/{actorId}/preferences", GREEN, "visible 2 to 4 min after the event"),
        ("SEMANTIC", "/users/{actorId}/facts", BLUE, "facts the extractor distils"),
        ("EPISODIC", "/episodes/{actorId}/{sessionId}", ORANGE, "slowest: ~17 min after the event"),
    ]
    y = 316
    for name, ns, colour, note in ns_rows:
        out.append(f'<rect x="804" y="{y}" width="566" height="86" rx="12" fill="#0b1428" '
                   f'stroke="{colour}" stroke-width="1.6"/>')
        label(826, y + 34, name, 17, "#f8fafc", weight="600")
        label(826, y + 58, ns, 16, "#cbd5e1")
        label(826, y + 76, note, 14, "#7c93b5")
        y += 98

    label(804, y + 22, "long term: RetrieveMemoryRecords reads one namespace at a time",
          15, "#8ea0bd")
    label(804, y + 46, "the trailing slash on /episodes/{actorId}/ is a prefix read",
          15, "#8ea0bd")

    label(60, 600, "the actor id sits inside the key, not in a filter, so two", 15, "#8ea0bd")
    label(60, 624, "managers never share a namespace to begin with.", 15, "#8ea0bd")
    label(60, 672, "teardown: agentcore remove all -y, then a reconciling deploy", 15, "#64748b")
    label(60, 696, "survives: the CDK bootstrap stack and its asset bucket", 15, "#64748b")
    out.append("</svg>")
    (HERE / "F1-memory-architecture.svg").write_text("\n".join(out) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# figure 2: one actor's loop, with this run's measured times                  #
# --------------------------------------------------------------------------- #

def figure_two_sessions() -> None:
    w, h = 1440, 726
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}" role="img">',
        "<title>A preference stated in session one is extracted into a record and read back "
        "by session two, which never saw the first conversation.</title>",
        "<defs>",
        '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{BG0}"/><stop offset="1" stop-color="{BG1}"/></linearGradient>',
        '<radialGradient id="g1" cx="0.08" cy="0.02" r="0.8">'
        f'<stop offset="0" stop-color="{TEAL}" stop-opacity="0.22"/>'
        f'<stop offset="1" stop-color="{TEAL}" stop-opacity="0"/></radialGradient>',
        '<radialGradient id="g2" cx="0.92" cy="1.0" r="0.8">'
        f'<stop offset="0" stop-color="{ORANGE}" stop-opacity="0.20"/>'
        f'<stop offset="1" stop-color="{ORANGE}" stop-opacity="0"/></radialGradient>',
        '<marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        'markerHeight="7" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#60a5fa"/></marker>',
        "</defs>",
        f'<rect width="{w}" height="{h}" fill="url(#bg)"/>',
        f'<rect width="{w}" height="{h}" fill="url(#g1)"/>',
        f'<rect width="{w}" height="{h}" fill="url(#g2)"/>',
    ]

    def label(x: int, y: int, text: str, size: int = 16,
              colour: str = "#8ea0bd", anchor: str = "start", weight: str = "400") -> None:
        out.append(
            f'<text x="{x}" y="{y}" font-family="{SANS}" font-size="{size}" fill="{colour}" '
            f'text-anchor="{anchor}" font-weight="{weight}">{html.escape(text)}</text>'
        )

    def arrow(x1: int, y1: int, x2: int, y2: int, colour: str = "#60a5fa", dash: str = "") -> None:
        style = f' stroke-dasharray="{dash}"' if dash else ""
        out.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{colour}" '
            f'stroke-width="2.2"{style} marker-end="url(#ah)"/>'
        )

    label(60, 62, "the cross-session loop, measured", 22, "#f8fafc", weight="600")
    label(60, 90, "actor store_manager_south, two invocations of the same runtime, two session ids",
          15)

    out.append('<rect x="60" y="130" width="560" height="300" rx="18" fill="#0b1428" '
               'stroke="#2563eb" stroke-width="2"/>')
    label(88, 172, "session one  06:25:46Z", 20, "#93c5fd", weight="600")
    label(88, 206, 'prompt  "From now on, only reorder for the', 16, "#cbd5e1")
    label(88, 230, '        South China region. Ignore every other', 16, "#cbd5e1")
    label(88, 254, '        region."', 16, "#cbd5e1")
    label(88, 296, "the agent stores nothing itself.", 15, "#64748b")
    label(88, 322, "it appends both turns as one event;", 15, "#64748b")
    label(88, 348, "extraction decides what becomes a record.", 15, "#64748b")
    label(88, 404, "returned 06:26:03Z   17 s of CLI wall clock", 15, "#5eead4")

    arrow(624, 280, 700, 280, "#5eead4")

    out.append('<rect x="700" y="180" width="300" height="200" rx="18" fill="#101c37" '
               'stroke="#ea580c" stroke-width="2"/>')
    label(850, 226, "extraction", 21, "#fdba74", weight="600", anchor="middle")
    label(850, 262, "runs after the event,", 15, "#8ea0bd", anchor="middle")
    label(850, 292, "not inside the invoke", 15, "#8ea0bd", anchor="middle")
    label(850, 336, "255 s to become readable", 18, "#f8fafc", anchor="middle", weight="600")
    label(850, 362, "measured, not estimated", 14, "#64748b", anchor="middle")

    arrow(1004, 280, 1080, 280, "#fdba74")

    out.append('<rect x="1080" y="130" width="300" height="300" rx="18" fill="#0b1428" '
               'stroke="#059669" stroke-width="2"/>')
    label(1230, 172, "session two  06:30:18Z", 20, "#6ee7b7", weight="600", anchor="middle")
    label(1230, 204, "a session id it has never seen", 15, "#7c93b5", anchor="middle")
    label(1230, 246, 'prompt', 15, "#8ea0bd", anchor="middle")
    label(1230, 272, '"Draft this week\'s', 16, "#cbd5e1", anchor="middle")
    label(1230, 296, 'reorder list."', 16, "#cbd5e1", anchor="middle")
    label(1230, 340, "reordered for", 15, "#8ea0bd", anchor="middle")
    label(1230, 368, "South China only", 18, "#f8fafc", anchor="middle", weight="600")
    label(1230, 404, "Guangzhou, Shenzhen, Dongguan", 15, "#5eead4", anchor="middle")

    out.append('<rect x="60" y="462" width="1320" height="116" rx="16" fill="#0b1428" '
               'stroke="#1e2a44" stroke-width="1.5"/>')
    label(88, 502, "why this is not the default answering", 18, "#f8fafc", weight="600")
    label(88, 534, "namespace  /users/store_manager_south/preferences", 16, "#34d399")
    label(88, 562, "the system prompt picks North China when no preference is remembered, and the", 16, "#cbd5e1")
    label(88, 586, "agent has to say it is guessing; this session did neither.", 16, "#cbd5e1")

    out.append('<rect x="60" y="588" width="1320" height="104" rx="16" fill="#0b1428" '
               'stroke="#1e2a44" stroke-width="1.5"/>')
    label(88, 636, "east    /users/store_manager_east/preferences    East China   Shanghai, Hangzhou, Nanjing",
          16, "#34d399")
    label(88, 668, "south   /users/store_manager_south/preferences   South China  Guangzhou, Shenzhen, Dongguan",
          16, "#fdba74")

    label(60, 710, "the two lines above are two invocations fourteen seconds apart, same prompt, "
                   "two actor ids.", 14, "#64748b")

    out.append("</svg>")
    (HERE / "F2-two-sessions.svg").write_text("\n".join(out) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# covers                                                                      #
# --------------------------------------------------------------------------- #

def cover(w: int, h: int, name: str) -> None:
    """Normalised layout, so the same composition works at 1200x675 and 1000x420."""
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" '
        f'height="{h}" role="img">',
        "<title>An Agent That Remembers: short-term and long-term memory on AgentCore</title>",
        "<defs>",
        '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{BG0}"/><stop offset="1" stop-color="{BG1}"/></linearGradient>',
        '<radialGradient id="g1" cx="0.08" cy="0.02" r="0.8">'
        f'<stop offset="0" stop-color="{BLUE}" stop-opacity="0.22"/>'
        f'<stop offset="1" stop-color="{BLUE}" stop-opacity="0"/></radialGradient>',
        '<radialGradient id="g2" cx="0.92" cy="1.0" r="0.8">'
        f'<stop offset="0" stop-color="{PURPLE}" stop-opacity="0.20"/>'
        f'<stop offset="1" stop-color="{PURPLE}" stop-opacity="0"/></radialGradient>',
        '<marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        'markerHeight="7" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#60a5fa"/></marker>',
        "</defs>",
        f'<rect width="{w}" height="{h}" fill="url(#bg)"/>',
        f'<rect width="{w}" height="{h}" fill="url(#g1)"/>',
        f'<rect width="{w}" height="{h}" fill="url(#g2)"/>',
    ]
    pad = 0.055 * w
    title = 0.052 * w
    out.append(
        f'<text x="{pad:.0f}" y="{0.16*h:.0f}" font-family="{SANS}" font-size="{0.024*w:.0f}" '
        f'fill="#60a5fa" font-weight="600">AgentCore in Action</text>'
    )
    out.append(
        f'<text x="{pad:.0f}" y="{0.30*h:.0f}" font-family="{SANS}" font-size="{title:.0f}" '
        f'fill="#f8fafc" font-weight="700">An Agent That Remembers</text>'
    )
    out.append(
        f'<text x="{pad:.0f}" y="{0.385*h:.0f}" font-family="{SANS}" '
        f'font-size="{0.022*w:.0f}" fill="#c4b5fd">'
        f'Short-term and long-term memory, in one resource</text>'
    )

    top = 0.50 * h
    card_h = 0.28 * h
    card_w = 0.245 * w
    x1, x2 = pad, pad + card_w + 0.125 * w
    fs = 0.0165 * w
    for x, colour, head_txt, body in (
        (x1, BLUE, "session 1", ["only my own region", "matters to me"]),
        (x2, GREEN, "session 2", ["already knew that,", "and says why"]),
    ):
        out.append(
            f'<rect x="{x:.0f}" y="{top:.0f}" width="{card_w:.0f}" height="{card_h:.0f}" '
            f'rx="14" fill="#0b1428" stroke="{colour}" stroke-width="2"/>'
        )
        out.append(
            f'<text x="{x + 0.022*w:.0f}" y="{top + 0.075*h:.0f}" font-family="{SANS}" '
            f'font-size="{fs:.0f}" fill="{colour}" font-weight="600">{head_txt}</text>'
        )
        for i, line in enumerate(body):
            out.append(
                f'<text x="{x + 0.022*w:.0f}" y="{top + (0.125 + i*0.055)*h:.0f}" '
                f'font-family="{SANS}" font-size="{fs:.0f}" fill="#cbd5e1">{line}</text>'
            )

    ay = top + 0.14 * h
    out.append(
        f'<line x1="{x1 + card_w + 0.012*w:.0f}" y1="{ay:.0f}" x2="{x2 - 0.012*w:.0f}" '
        f'y2="{ay:.0f}" stroke="#60a5fa" stroke-width="2.2" marker-end="url(#ah)"/>'
    )
    out.append(
        f'<text x="{(x1 + card_w + x2) / 2:.0f}" y="{ay - 0.03*h:.0f}" font-family="{SANS}" '
        f'font-size="{0.015*w:.0f}" fill="#8ea0bd" text-anchor="middle">memory</text>'
    )
    out.append(
        f'<text x="{pad:.0f}" y="{0.93*h:.0f}" font-family="{SANS}" '
        f'font-size="{0.016*w:.0f}" fill="#8ea0bd">'
        f'one memory resource, three namespaces, actor id inside the key</text>'
    )
    out.append("</svg>")
    (HERE / f"{name}.svg").write_text("\n".join(out) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# every panel                                                                 #
# --------------------------------------------------------------------------- #

SPANS_CMD = [
    """$ jq -r '[.[] ."@message" | select(type == "object" and .name != null)] as $spans""",
    """      | $spans | sort_by(.startTimeUnixNano) | .[] | (.attributes // {}) as $a""",
    """      | [.name, (((.durationNano // 0) / 1000000 | floor | tostring) + " ms"),""",
    """         (if $a["gen_ai.usage.input_tokens"] then ($a["gen_ai.usage.input_tokens"] | tostring)""",
    """            + " in / " + ($a["gen_ai.usage.output_tokens"] | tostring) + " out" else "-" end)]""",
    """      | @tsv' \\""",
    "  agentcore/.cli/traces/aia_uc02-6ad46781381df402758baa6d42b96dd3.json | column -t -s $'\\t'",
]

INDEPENDENCE_CMD = [
    "$ aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=agentcore-in-action \\",
    "    --region us-east-1 --query 'ResourceTagMappingList[].{arn:ResourceARN,tags:Tags[?Key==`UseCase`].Value|[0]}' \\",
    "    --output text",
]

# Filled in by hand from the run: the episode recall invoke is the last one made.
EPISODE_SESSION = "801a6b1087b14af48fecfc870aa82dee-31527d8a"
EPISODE_RECALL_START = "07:08:05Z"
EPISODE_WAIT = "1022 s (17 m 2 s)"

SOUTH_PREF_CMD = [
    "$ agentcore invoke --user-id store_manager_south --session-id c40ea8a3deea4b6c9efe0755fc784ef3-229cdb2d \\",
    '    --prompt "From now on, only reorder for the South China region. Ignore every other region."',
]
SOUTH_RECALL_CMD = [
    "$ agentcore invoke --user-id store_manager_south --session-id bf60f433a15444288a1356e9902ba70f-33438667 \\",
    '    --prompt "Draft this week\'s reorder list."',
]
EAST_PREF_CMD = [
    "$ agentcore invoke --user-id store_manager_east --session-id 597e436a5ae1435cb7d6c422c4a936be-584aa045 \\",
    '    --prompt "From now on, only reorder for the East China region. Ignore every other region."',
]
EAST_RECALL_CMD = [
    "$ agentcore invoke --user-id store_manager_east --session-id 6cb14cbdd21d418795777aada1ba40d0-37ad719d \\",
    '    --prompt "Draft this week\'s reorder list."',
]
SOUTH_AGAIN_CMD = [
    "$ agentcore invoke --user-id store_manager_south --session-id 184c229604484042ade86f840e90d8ce-4a0d1bea \\",
    '    --prompt "Draft this week\'s reorder list."',
]
EPISODE_CMD = [
    "$ agentcore invoke --user-id store_manager_east --session-id d1ed2f2053a543f493953ec4e7967083-0fa33c38 \\",
    '    --prompt "I tried restocking my stores from the Guangzhou warehouse last month. It failed: \\',
    'the lead time was 9 days and three stores stocked out. Make a note of it."',
]
EAST_EPISODE_RECALL_CMD = [
    "$ agentcore invoke --user-id store_manager_east --session-id %s \\" % EPISODE_SESSION,
    '    --prompt "Is it a good idea to ship this week\'s East China restock from the Guangzhou warehouse?"',
]
TEARDOWN_CMD = [
    "$ agentcore remove all -y",
    "$ agentcore deploy -y --target default",
    "$ agentcore status",
    "$ aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=agentcore-in-action \\",
    "    --region us-east-1 --query 'ResourceTagMappingList[].{arn:ResourceARN,tags:Tags[?Key==`UseCase`].Value|[0]}' \\",
    "    --output text",
    "$ git checkout agentcore/agentcore.json agentcore/aws-targets.json",
    "$ agentcore status",
]

TEARDOWN_BODY = (
    [("", S)]
    + panel_lines(["$ agentcore remove all -y"], evidence_body("47-remove-all.txt"))
    + [("", S)]
    + panel_lines(["$ agentcore deploy -y --target default"],
                  evidence_body("48-reconcile-deploy.txt"))
    + [("", S)]
    + panel_lines(["$ agentcore status"], evidence_body("49-status-after-down.txt"))
    + [("", S)]
    + panel_lines(INDEPENDENCE_CMD, evidence_body("50-independence-after-down.txt"))
    + [("    (no rows: ResourceTagMappingList is empty)", D), ("", S)]
    + panel_lines(["$ git checkout agentcore/agentcore.json agentcore/aws-targets.json"], [])
    + panel_lines(["$ agentcore status"], evidence_body("51-status-restored.txt"))
)


def panels() -> None:
    shell_box(
        "S1-deploy", "terminal - agentcore deploy",
        panel_lines(["$ agentcore deploy -y --target default"], evidence_body("20-deploy.txt")),
        "evidence/20-deploy.txt · wall clock 4 m 20 s · per-step durations in evidence/21-deploy-log.txt",
    )
    shell_box(
        "S2-status", "terminal - agentcore status",
        panel_lines(["$ agentcore status"], evidence_body("22-status.txt")),
        "evidence/22-status.txt · the CLI hard-wraps long lines, so the runtime ARN is on two lines",
    )
    shell_box(
        "S3-preference-south", "terminal - session one states a preference",
        panel_lines(SOUTH_PREF_CMD, evidence_body("30-invoke-south-preference.txt")),
        "evidence/30-invoke-south-preference.txt · started 06:25:46Z, returned 06:26:03Z",
    )
    shell_box(
        "S4-recall-south", "terminal - session two, four minutes later",
        panel_lines(SOUTH_RECALL_CMD, evidence_body("31-invoke-south-recall.txt")),
        "evidence/31-invoke-south-recall.txt · started 06:30:18Z, 255 s after the event was written",
    )
    shell_box(
        "S5-preference-east", "terminal - a second manager states a different preference",
        panel_lines(EAST_PREF_CMD, evidence_body("34-invoke-east-preference.txt")),
        "evidence/34-invoke-east-preference.txt · nothing extracted yet, so it falls back to the default",
    )
    shell_box(
        "S6-recall-east", "terminal - that manager's next session",
        panel_lines(EAST_RECALL_CMD, evidence_body("39-invoke-east-recall.txt")),
        "evidence/39-invoke-east-recall.txt · started 06:37:14Z, 236 s after its own preference event",
    )
    shell_box(
        "S7-isolation", "terminal - the same question, the other manager, fourteen seconds later",
        panel_lines(SOUTH_AGAIN_CMD, evidence_body("40-invoke-south-again.txt")),
        "evidence/40-invoke-south-again.txt · started 06:37:46Z, fourteen seconds after S6",
    )
    shell_box(
        "S8-episode", "terminal - a failed restock, told once",
        panel_lines(EPISODE_CMD, evidence_body("43-invoke-east-episode.txt")),
        "evidence/43-invoke-east-episode.txt · started 06:50:47Z, returned 06:51:03Z",
    )
    shell_box(
        "S9-episode-recall", "terminal - a later session asks about the warehouse that failed",
        panel_lines(EAST_EPISODE_RECALL_CMD, evidence_body("45-invoke-east-episode-ask.txt")),
        "evidence/45-invoke-east-episode-ask.txt · started %s, %s after the episode event" % (
            EPISODE_RECALL_START, EPISODE_WAIT),
    )
    shell_box(
        "S10-traces-list", "terminal - agentcore traces list",
        panel_lines(["$ agentcore traces list"], evidence_body("35-traces-list.txt")),
        "evidence/35-traces-list.txt · one row per invoke of this runtime",
    )
    shell_box(
        "S11-trace-get", "terminal - agentcore traces get",
        panel_lines(["$ agentcore traces get 6ad46781381df402758baa6d42b96dd3"],
                    evidence_body("36-trace-get.txt")),
        "evidence/36-trace-get.txt · the trace JSON itself carries base64 fields that decode to "
        "binary records holding the account id, so only the extracted part is kept, in evidence/37",
    )
    shell_box(
        "S12-trace-spans", "terminal - the span table out of that trace",
        panel_lines(SPANS_CMD, evidence_body("37-trace-spans.txt")),
        "evidence/37-trace-spans.txt · one traced invoke: three RetrieveMemoryRecords reads before "
        "the model, one CreateEvent after it",
    )
    shell_box(
        "S13-independence", "terminal - aws resourcegroupstaggingapi, while uc02 is deployed",
        panel_lines(INDEPENDENCE_CMD, evidence_body("38-independence.txt")),
        "evidence/38-independence.txt · four resources, every one of them tagged UseCase=02",
    )
    shell_box(
        "S14-teardown", "terminal - remove all, the reconciling deploy, and the empty account",
        TEARDOWN_BODY,
        "evidence/47 to evidence/51 · remove all empties both JSON files, the deploy deletes the "
        "stack in 4 m 13 s, the tag query prints nothing, and git restores the contract",
    )


def main() -> None:
    panels()
    figure_architecture()
    figure_two_sessions()
    cover(1200, 675, "cover")
    cover(1000, 420, "cover-devto")
    cover(1400, 788, "cover-medium")   # Medium feature image, same 16:9 composition


if __name__ == "__main__":
    main()
