#!/usr/bin/env python3
"""Generate every image for the uc02 article from the run captured on 2026-10-18.

Every number drawn here comes from `usecases/02-memory/evidence/`. The terminal
panels are the captured output with the account id redacted to 123456789012, the
bold markers the model emitted stripped, and a `...` wherever a line is cut.

    python3 gen_figures.py            # writes every .svg next to this file
    render.sh                         # svg -> png, see the comment at the bottom
"""

from __future__ import annotations

import html
import pathlib

HERE = pathlib.Path(__file__).resolve().parent

BG0, BG1 = "#0a1024", "#0d1c3a"
BLUE, PURPLE, ORANGE, GREEN, RED, TEAL = (
    "#2563eb", "#7c3aed", "#ea580c", "#059669", "#e11d48", "#0d9488",
)
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
SANS = "Inter, Helvetica Neue, Arial, sans-serif"

# text colours used inside terminal panels
W, G, O, T, D, S = "#f8fafc", "#34d399", "#fdba74", "#5eead4", "#7c93b5", "#cbd5e1"


def head(w: int, h: int, title: str, glow_a: str = BLUE, glow_b: str = PURPLE) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}" role="img">',
        f"<title>{html.escape(title)}</title>",
        "<defs>",
        '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{BG0}"/><stop offset="1" stop-color="{BG1}"/></linearGradient>',
        '<radialGradient id="gA" cx="0.08" cy="0.02" r="0.8">'
        f'<stop offset="0" stop-color="{glow_a}" stop-opacity="0.24"/>'
        f'<stop offset="1" stop-color="{glow_a}" stop-opacity="0"/></radialGradient>',
        '<radialGradient id="gB" cx="0.92" cy="1.0" r="0.8">'
        f'<stop offset="0" stop-color="{glow_b}" stop-opacity="0.20"/>'
        f'<stop offset="1" stop-color="{glow_b}" stop-opacity="0"/></radialGradient>',
        '<marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        'markerHeight="7" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#60a5fa"/></marker>',
        '<marker id="ahp" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        'markerHeight="7" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#c4b5fd"/></marker>',
        "</defs>",
        f'<rect width="{w}" height="{h}" fill="url(#bg)"/>',
        f'<rect width="{w}" height="{h}" fill="url(#gA)"/>',
        f'<rect width="{w}" height="{h}" fill="url(#gB)"/>',
    ]


def panel(name: str, title: str, lines: list[tuple[str, str]], subtitle: str = "") -> None:
    """Render captured terminal output as an SVG panel."""
    top = 96
    pad = 34
    size = 17.5
    lh = 27
    width = 1440
    height = top + lh * (len(lines) + 1) + pad + (34 if subtitle else 0)

    out = head(width, height, title)
    out.append(
        f'<rect x="28" y="26" width="{width-56}" height="{height-52}" rx="16" '
        f'fill="#0b1428" stroke="#1e2a44" stroke-width="1.5"/>'
    )
    out.append(f'<rect x="28" y="26" width="{width-56}" height="46" rx="16" fill="#101b33"/>')
    out.append(f'<rect x="28" y="58" width="{width-56}" height="14" fill="#101b33"/>')
    for i, colour in enumerate((RED, ORANGE, GREEN)):
        out.append(f'<circle cx="{56 + i*26}" cy="49" r="6.5" fill="{colour}" opacity="0.85"/>')
    out.append(
        f'<text x="{width//2}" y="55" font-family="{MONO}" font-size="16" fill="{D}" '
        f'text-anchor="middle">{html.escape(title)}</text>'
    )

    y = top + 6
    for text, colour in lines:
        out.append(
            f'<text x="58" y="{y}" font-family="{MONO}" font-size="{size}" '
            f'fill="{colour}" xml:space="preserve">{html.escape(text)}</text>'
        )
        y += lh
    if subtitle:
        y += 8
        out.append(
            f'<text x="58" y="{y}" font-family="{MONO}" font-size="15" '
            f'fill="{D}">{html.escape(subtitle)}</text>'
        )
    out.append("</svg>")
    (HERE / f"{name}.svg").write_text("\n".join(out) + "\n", encoding="utf-8")


def box(out: list[str], x: int, y: int, w: int, h: int, fill: str, stroke: str,
        label: str, sub: str = "", lsize: int = 20, ssize: int = 15,
        lcolour: str = "#f8fafc", scolour: str = "#7c93b5", sub2: str = "") -> None:
    out.append(
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="1.6"/>'
    )
    lines = [label] + ([sub] if sub else []) + ([sub2] if sub2 else [])
    total = len(lines)
    start = y + h / 2 - (total - 1) * 13 + 6
    for i, text in enumerate(lines):
        colour = lcolour if i == 0 else scolour
        size = lsize if i == 0 else ssize
        out.append(
            f'<text x="{x + w/2:.0f}" y="{start + i*26:.0f}" font-family="{SANS}" '
            f'font-size="{size}" fill="{colour}" text-anchor="middle">{html.escape(text)}</text>'
        )


def arrow(out: list[str], x1: int, y1: int, x2: int, y2: int, colour: str = "#60a5fa",
          marker: str = "ah", dash: str = "") -> None:
    style = f' stroke-dasharray="{dash}"' if dash else ""
    out.append(
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{colour}" '
        f'stroke-width="2.2"{style} marker-end="url(#{marker})"/>'
    )


def label(out: list[str], x: int, y: int, text: str, size: int = 16,
          colour: str = "#8ea0bd", anchor: str = "start", weight: str = "400") -> None:
    out.append(
        f'<text x="{x}" y="{y}" font-family="{SANS}" font-size="{size}" fill="{colour}" '
        f'text-anchor="{anchor}" font-weight="{weight}">{html.escape(text)}</text>'
    )


# --------------------------------------------------------------------------- #
# terminal captures                                                           #
# --------------------------------------------------------------------------- #

DEPLOY: list[tuple[str, str]] = [
    ("$ python3 run.py deploy                                    # or: make deploy", S),
    (">> agentcore deploy -y --target default", D),
    ("", S),
    ("  Load deployment target ............ 1 ms", D),
    ("  Validate project .................. 682 ms", D),
    ("  Sync CDK dependencies ............. 2 ms", D),
    ("  Build CDK project ................. 2.4 s", D),
    ("  Synthesize CloudFormation ......... 7.1 s", D),
    ("  Check bootstrap status ............ 665 ms", D),
    ("  Check stack status ................ 1.4 s", D),
    ("  Deploy to AWS ..................... 4 m 7 s", D),
    ("  Persist deployment state .......... 715 ms", D),
    ("", S),
    ("Total duration: 4 m 23 s", W),
    ("", S),
    ("Deployed to 'default' (stack: AgentCore-aiauc02-default)", G),
    ("", S),
    ("Outputs:", S),
    ("  ApplicationMemoryAiaUc02MemIdOutput7F0802F1", G),
    ("    aiauc02_aia_uc02_mem-y7Ql9N3D59", W),
    ("  ApplicationAgentAiaUc02RuntimeIdOutput62FFD619", G),
    ("    aiauc02_aia_uc02-ACujAB8uYJ", W),
    ("  ApplicationAgentAiaUc02RuntimeArnOutput9F81CB35", G),
    ("    arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/aiauc02_aia_uc02-ACujAB8uYJ", W),
    ("  ApplicationMemoryAiaUc02MemArnOutput418E65F1", G),
    ("    arn:aws:bedrock-agentcore:us-east-1:123456789012:memory/aiauc02_aia_uc02_mem-y7Ql9N3D59", W),
    ("  StackNameOutput", G),
    ("    AgentCore-aiauc02-default", W),
]


CROSS_SESSION: list[tuple[str, str]] = [
    ("$ python3 run.py invoke --session b0b998ab-89ca-4387-99cb-fc01130e9108-ff3568e8 \\", S),
    ('    --prompt "From now on, only reorder for the North China region. Ignore every other region."', S),
    ("Invoking agent...", D),
    ("Based on your explicit instruction, I'll only reorder for the North China region.", W),
    ("The North China region needs reorders at three stores: Beijing Haidian (42 thermal", S),
    ("flasks), Tianjin Heping (17 insulated mugs), and Shijiazhuang Qiaoxi (8 lunch boxes).", S),
    ("I followed your instruction to only reorder for North China and ignored all other regions. ...", S),
    ("", S),
    ("$ python3 run.py invoke --session 03fd411e-293b-4aa2-a219-bd996c7e3481-6b0df16e \\", S),
    ('    --prompt "Draft this week\'s reorder list."', S),
    ("Invoking agent...", D),
    ("I'll create the reorder list for the North China region as specified in your preferences.", W),
    ("Let me check which stores need reordering.", S),
    ("Here's this week's reorder list for the North China region:", S),
    ("Store: Beijing Haidian, SKU: SKU-1001, Product: thermal flask, Reorder Quantity: 42 units", S),
    ("Store: Tianjin Heping, SKU: SKU-1002, Product: insulated mug, Reorder Quantity: 17 units", S),
    ("Store: Shijiazhuang Qiaoxi, SKU: SKU-1003, Product: lunch box, Reorder Quantity: 8 units", S),
    ("Note: I've applied your documented preference to only reorder for North China region,", G),
    ("ignoring all other regions.", G),
    ("", S),
    ("Session: 03fd411e-293b-4aa2-a219-bd996c7e3481-6b0df16e  ...", T),
]


VERIFY: list[tuple[str, str]] = [
    ("$ make test", S),
    ("", S),
    ("memory", D),
    ("       session 1 e9f9d728131040b1ad532866e69b4981-cd9243d4", D),
    ("       · reply \"I'll get the current reorder list for the North China region only. ...\"", D),
    ("       extraction visible after 1.5s · 1 record(s)", O),
    ("       record '{\"context\":\"Inventory reordering and restocking operations", D),
    ("       for North China region, including historical restoc ...", D),
    ("       session 2 34b26d624d2140d1b767098a09abdfaa-8d1f1d6b · tools ['reorder_candidates']", D),
    ("       reply \"Based on your preference for North China region, here is this", W),
    ("       week's reorder list: ...\"", W),
    ("  PASS assert_memory_1: a second session retrieves a preference written in the first", G),
    ("       actor store_manager_north sees '{\"context\":\"Inventory reordering and restocking operations", D),
    ("       for North China region, including historical restoc ...", D),
    ("       actor store_manager_south sees '{\"context\":\"Managing inventory reorder operations\",\"preference\":\"Only", D),
    ("       reorder for the South China region; igno ...", D),
    ("       actor store_manager_south reply \"Based on your preference for South China", W),
    ("       region only, here's this week's reorder list: ...\"", W),
    ("  PASS assert_memory_2: actor A cannot retrieve actor B memories", G),
    ("       episodic extraction visible after 959s", O),
    ("       episodic record '{\"situation\":\"The user requested a draft of the weekly", D),
    ("       reorder list as part of a routine inventory management workflow, with the assistant d ...", D),
    ("       reply \"... Remember: the Guangzhou warehouse must not be used for North", W),
    ("       China restocks.\"", W),
    ("  PASS assert_memory_3: episodic strategy recalls a previously failed approach", G),
    ("", S),
    ("  PASS independence: no other use case's resources present", G),
    ("", S),
    ("4 passed, 0 failed", W),
]


TEARDOWN: list[tuple[str, str]] = [
    ("$ make down", S),
    (">> agentcore remove all -y", D),
    ("All schemas reset to empty state", S),
    ("Your source code has not been modified. Run `agentcore deploy` to apply changes to AWS.", D),
    (">> agentcore deploy -y --target default", D),
    ("Deploy to AWS...", D),
    ("Tear down stack...", D),
    ("Total Duration: 4m 11s", W),
    ("", S),
    ("$ aia.py status 02", S),
    ("AgentCore Status (target: default, us-east-1)", S),
    ("", S),
    ("Agents", S),
    ("  aia_uc02: Local only", G),
    ("", S),
    ("Memories", S),
    ("  aia_uc02_mem: Local only (USER_PREFERENCE, EPISODIC, SEMANTIC)", G),
    ("", S),
    ("$ aws resourcegroupstaggingapi get-resources \\", S),
    ("    --tag-filters Key=Project,Values=agentcore-in-action --region us-east-1", S),
    ("0", W),
]


# --------------------------------------------------------------------------- #
# figure 1: one memory resource, two halves, three namespaces                 #
# --------------------------------------------------------------------------- #

def figure_architecture() -> None:
    w, h = 1440, 760
    out = head(w, h, "One AgentCore Memory resource split into a short-term event log and three "
                     "long-term namespaces, every namespace keyed by actor id.")

    label(out, 60, 62, "the deployed use case, uc02", 22, "#f8fafc", weight="600")
    label(out, 60, 90, "every resource below is tagged Project=agentcore-in-action, UseCase=uc02", 15)

    # caller
    box(out, 46, 140, 250, 120, "#0e1a33", "#2b3c5e", "caller", "prompt + actor_id", 20, 15)

    # runtime
    box(out, 380, 125, 300, 230, "#122146", "#3b82f6", "AgentCore Runtime", "aia_uc02",
        21, 15, "#f8fafc", "#7c93b5", "app/aia_uc02, CodeZip, PYTHON_3_13")

    arrow(out, 296, 200, 374, 200)
    label(out, 335, 188, "invoke", 13, "#64748b", anchor="middle")

    # model
    box(out, 380, 420, 300, 90, "#0e1a33", "#2b3c5e", "Bedrock", "deepseek.v3.2", 18, 14)
    arrow(out, 530, 355, 530, 414, "#60a5fa", "ah", "5 5")
    label(out, 544, 390, "converse", 14, "#64748b")

    # memory resource
    out.append('<rect x="780" y="112" width="614" height="560" rx="18" fill="#101c37" '
               'stroke="#7c3aed" stroke-width="2"/>')
    label(out, 804, 152, "AgentCore Memory  aia_uc02_mem", 20, "#c4b5fd", weight="600")
    label(out, 804, 178, "eventExpiryDuration 30 d, three extraction strategies", 14, "#7c93b5")

    # write arrow + short-term lane
    arrow(out, 684, 234, 778, 234, "#5eead4", "ah")
    label(out, 690, 222, "write", 14, "#5eead4")
    box(out, 804, 190, 566, 78, "#0d1729", "#0d9488", "short term", "CreateEvent, one event per turn",
        18, 13, "#5eead4", "#7c93b5", "append-only, keyed by (actor, session)")

    # extraction
    out.append('<path d="M 1050 268 L 1050 308" stroke="#ea580c" stroke-width="2.4" '
               'marker-end="url(#ah)" fill="none"/>')
    label(out, 1062, 296, "async extraction", 14, "#fdba74")

    # read arrow
    arrow(out, 778, 339, 686, 339, "#c4b5fd", "ahp", "6 5")
    label(out, 690, 327, "read", 14, "#c4b5fd")

    ns_rows = [
        ("USER_PREFERENCE", "/users/{actorId}/preferences", GREEN),
        ("SEMANTIC", "/users/{actorId}/facts", BLUE),
        ("EPISODIC", "/episodes/{actorId}/{sessionId}", ORANGE),
    ]
    y = 316
    for name, ns, colour in ns_rows:
        out.append(f'<rect x="804" y="{y}" width="566" height="86" rx="12" fill="#0b1428" '
                   f'stroke="{colour}" stroke-width="1.6"/>')
        label(out, 826, y + 36, name, 17, "#f8fafc", weight="600")
        label(out, 826, y + 62, ns, 16, "#cbd5e1")
        y += 98

    label(out, 804, y + 24, "long term: RetrieveMemoryRecords reads one namespace at a time",
          15, "#8ea0bd")
    label(out, 804, y + 48, "the trailing slash on /episodes/{actorId}/ is a prefix read",
          15, "#8ea0bd")

    # footnotes
    label(out, 60, 600, "the actor id sits inside the key, not in a filter, so the", 15, "#8ea0bd")
    label(out, 60, 624, "two managers never share a namespace to begin with.", 15, "#8ea0bd")
    label(out, 60, 672, "teardown: agentcore remove all -y, then a reconciling deploy", 15, "#64748b")
    label(out, 60, 696, "survives: the CDK bootstrap stack and its asset bucket", 15, "#64748b")
    out.append("</svg>")
    (HERE / "F1-memory-architecture.svg").write_text("\n".join(out) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# figure 2: the two-session timeline that the first assertion walks            #
# --------------------------------------------------------------------------- #

def figure_two_sessions() -> None:
    w, h = 1440, 726
    out = head(w, h, "A preference stated in session one is extracted into a record and read "
                     "back by session two, which never saw the first conversation.",
               glow_a=TEAL, glow_b=ORANGE)

    label(out, 60, 62, "the cross-session loop, measured", 22, "#f8fafc", weight="600")
    label(out, 60, 90, "two invocations of the same runtime, two different session ids, one actor",
          15)

    # session 1
    out.append('<rect x="60" y="130" width="560" height="300" rx="18" fill="#0b1428" '
               'stroke="#2563eb" stroke-width="2"/>')
    label(out, 88, 172, "session 1", 20, "#93c5fd", weight="600")
    label(out, 210, 172, "writes the preference", 15, "#7c93b5")
    label(out, 88, 214, 'prompt  "From now on, only reorder for the North China region."', 16, "#cbd5e1")
    label(out, 88, 246, 'reply   "Based on your explicit instruction, I\'ll only reorder"', 15, "#8ea0bd")
    label(out, 88, 268, '        "for the North China region."', 15, "#8ea0bd")
    label(out, 88, 320, "the agent never stores the preference itself.", 15, "#64748b")
    label(out, 88, 346, "it appends the turn; extraction decides what becomes a fact.", 15, "#64748b")

    arrow(out, 624, 280, 700, 280, "#5eead4")

    # extraction
    out.append('<rect x="700" y="180" width="300" height="200" rx="18" fill="#101c37" '
               'stroke="#ea580c" stroke-width="2"/>')
    label(out, 850, 226, "extraction", 21, "#fdba74", weight="600", anchor="middle")
    label(out, 850, 262, "runs after the event", 15, "#8ea0bd", anchor="middle")
    label(out, 850, 292, "not part of the invoke", 15, "#8ea0bd", anchor="middle")
    label(out, 850, 336, "visible after 1.5 s", 18, "#f8fafc", anchor="middle", weight="600")
    label(out, 850, 362, "measured, not estimated", 14, "#64748b", anchor="middle")

    arrow(out, 1004, 280, 1080, 280, "#fdba74")

    # session 2
    out.append('<rect x="1080" y="130" width="300" height="300" rx="18" fill="#0b1428" '
               'stroke="#059669" stroke-width="2"/>')
    label(out, 1230, 172, "session 2", 20, "#6ee7b7", weight="600", anchor="middle")
    label(out, 1230, 204, "a new session id", 15, "#7c93b5", anchor="middle")
    label(out, 1230, 246, 'prompt', 15, "#8ea0bd", anchor="middle")
    label(out, 1230, 272, '"Draft this week\'s', 16, "#cbd5e1", anchor="middle")
    label(out, 1230, 296, 'reorder list."', 16, "#cbd5e1", anchor="middle")
    label(out, 1230, 340, "reordered for", 15, "#8ea0bd", anchor="middle")
    label(out, 1230, 368, "North China only", 18, "#f8fafc", anchor="middle", weight="600")
    label(out, 1230, 404, "wrote   0000001792289323248#0e132265", 15, "#5eead4", anchor="middle")

    # record row
    out.append('<rect x="60" y="462" width="1320" height="116" rx="16" fill="#0b1428" '
               'stroke="#1e2a44" stroke-width="1.5"/>')
    label(out, 88, 502, "the record session 2 read", 18, "#f8fafc", weight="600")
    label(out, 88, 534, "namespace  /users/store_manager_north/preferences", 16, "#34d399")
    label(out, 88, 562, 'preference  "Only reorder for the North China region; ignore every '
                        'other region."', 16, "#cbd5e1")

    # isolation row
    out.append('<rect x="60" y="588" width="1320" height="104" rx="16" fill="#0b1428" '
               'stroke="#1e2a44" stroke-width="1.5"/>')
    label(out, 88, 638, "north   /users/store_manager_north/preferences   North China",
          16, "#34d399")
    label(out, 88, 670, "south   /users/store_manager_south/preferences   South China", 16, "#fdba74")

    label(out, 60, 710, "the event id session 2 wrote is the one traced in "
                        "evidence/17-trace-tokens.json; the record above is what it read.",
          14, "#64748b")

    out.append("</svg>")
    (HERE / "F2-two-sessions.svg").write_text("\n".join(out) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# covers                                                                      #
# --------------------------------------------------------------------------- #

def cover(w: int, h: int, name: str) -> None:
    """Normalised layout, so the same composition works at 1200x675 and 1000x420."""
    out = head(w, h, "An Agent That Remembers: short-term and long-term memory on AgentCore")
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
        (x1, BLUE, "session 1", ["only North China", "matters to me"]),
        (x2, GREEN, "session 2", ["reordered for", "North China only"]),
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
    arrow(out, x1 + card_w + 0.012 * w, ay, x2 - 0.012 * w, ay, "#60a5fa")
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


def main() -> None:
    panel("S1-deploy", "terminal - deploy", DEPLOY,
          "step timings from evidence/04-deploy.txt, outputs from evidence/07-deploy-clean.txt")
    panel("S2-cross-session-recall", "terminal - two sessions, one memory resource", CROSS_SESSION,
          "evidence/09 and 10 · 19 s CLI wall clock each · every cut marked ... · "
          "bold markers stripped · session ids verbatim")
    panel("S3-verify", "terminal - the three memory assertions", VERIFY,
          "evidence/08-test-clean.txt · long lines wrapped · every cut marked ... · "
          "the python3.14 wrapper, timestamps and exit status dropped")
    panel("S4-teardown", "terminal - teardown, and zero tagged resources left", TEARDOWN,
          "Total Duration from evidence/18-down-deploy.txt · the rest from "
          "evidence/12-down-raw.txt, evidence/13 and evidence/14")
    figure_architecture()
    figure_two_sessions()
    cover(1200, 675, "cover")
    cover(1000, 420, "cover-devto")


if __name__ == "__main__":
    main()
