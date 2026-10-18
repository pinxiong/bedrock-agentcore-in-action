#!/usr/bin/env python3
"""Generate every image for the uc01 article from the run captured on 2026-10-18.

Every number drawn here comes from `usecases/01-first-agent/evidence/`. The
terminal panels are the captured output with the account id redacted to
123456789012 and nothing else changed.

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
SOFT = "#cbd5e1"
DIM = "#8ea0bd"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"


# --------------------------------------------------------------------------- #
# terminal panels                                                             #
# --------------------------------------------------------------------------- #

def panel(name: str, title: str, lines: list[tuple[str, str]], subtitle: str = "") -> None:
    """Render captured terminal output as an SVG panel.

    Each line is (text, colour). Nothing is reformatted except that leading
    spaces are preserved, so what you see is what the terminal printed.
    """
    top = 96
    pad = 34
    size = 17.5
    lh = 27
    width = 1440
    body_w = max(len(t) for t, _ in lines)
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

    # window chrome
    out.append(f'<rect x="28" y="26" width="{width-56}" height="{height-52}" rx="16" '
               f'fill="#0b1428" stroke="#1e2a44" stroke-width="1.5"/>')
    out.append(f'<rect x="28" y="26" width="{width-56}" height="46" rx="16" fill="#101b33"/>')
    out.append(f'<rect x="28" y="58" width="{width-56}" height="14" fill="#101b33"/>')
    for i, colour in enumerate((RED, ORANGE, GREEN)):
        out.append(f'<circle cx="{56 + i*26}" cy="49" r="6.5" fill="{colour}" opacity="0.85"/>')
    out.append(f'<text x="{width//2}" y="55" font-family="{MONO}" font-size="16" fill="{DIM}" '
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
                   f'fill="{DIM}">{html.escape(subtitle)}</text>')
    out.append("</svg>")
    (HERE / f"{name}.svg").write_text("\n".join(out) + "\n", encoding="utf-8")


W, G, O, T, D, S = "#f8fafc", "#34d399", "#fdba74", "#5eead4", "#7c93b5", "#cbd5e1"


def shell_box(name: str, title: str, lines: list[tuple[str, str]], subtitle: str = "") -> None:
    panel(name, title, lines, subtitle)


DEPLOY: list[tuple[str, str]] = [
    ("$ python3 run.py deploy                                    # or: make deploy", S),
    (">> agentcore deploy -y --target default", D),
    ("", S),
    ("  Load deployment target ............ 1 ms", D),
    ("  Validate project .................. 641 ms", D),
    ("  Build CDK project ................. 2.4 s", D),
    ("  Synthesize CloudFormation ......... 15.4 s", D),
    ("  Check bootstrap status ............ 732 ms", D),
    ("  Check stack status ................ 659 ms", D),
    ("  Deploy to AWS ..................... 1 m 27 s", D),
    ("  Persist deployment state .......... 724 ms", D),
    ("", S),
    ("Total duration: 1 m 51 s", W),
    ("", S),
    ("Deployed to 'default' (stack: AgentCore-aiauc01-default)", G),
    ("", S),
    ("Outputs:", S),
    ("  ApplicationAgentAiaUc01RuntimeIdOutput734A07B7", G),
    ("    aiauc01_aia_uc01-R3MXCi9yld", W),
    ("  ApplicationAgentAiaUc01RuntimeArnOutput3227EF65", G),
    ("    arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/aiauc01_aia_uc01-R3MXCi9yld", W),
    ("  StackNameOutput", G),
    ("    AgentCore-aiauc01-default", W),
]

STATUS_INVOKE: list[tuple[str, str]] = [
    ("$ python3 run.py status                # or: make status", S),
    ("AgentCore Status (target: default, us-east-1)", S),
    ("Agents", S),
    ("  aia_uc01: Deployed - Runtime: READY", G),
    ("    arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/aiauc01_aia_uc01-R3MXCi9yld", W),
    ("", S),
    ("$ python3 run.py invoke", S),
    ("--prompt \"A customer returns two items priced 21 each.", S),
    ("          What refund total should I quote? Use the tool.\"", S),
    ("", S),
    ("The refund total you should quote is $42.", W),
    ("", S),
    ("Session: a99e785c-18e2-4b18-abef-368271019e7e", T),
    ("Response time: 9 911 ms", D),
]

TRACE: list[tuple[str, str]] = [
    ("$ agentcore traces get 6ad4087a7220c9ed52be46e901c25cc9", S),
    ("", S),
    ("invoke_agent Strands Agents                      2.50 s   tools=[\"add_numbers\"]", T),
    ("  execute_event_loop_cycle  cycle 1              0.68 s", S),
    ("    chat  deepseek.v3.2                          0.68 s   431 in / 60 out tokens", O),
    ("      BedrockRuntime  ConverseStream             0.67 s", D),
    ("  execute_event_loop_cycle  cycle 2              1.82 s", S),
    ("    chat  deepseek.v3.2                          1.82 s   514 in / 11 out tokens", O),
    ("      BedrockRuntime  ConverseStream             1.80 s", D),
    ("    execute_tool add_numbers                     success  span_kind=INTERNAL", G),
    ("", S),
    ("trace 1-6ad4087a-7220c9ed52be46e901c25cc9   session a99e785c-18e2-4b18-abef-368271019e7e", D),
    ("invoke_agent total: 945 input tokens, 71 output tokens", D),
]

SMOKE: list[tuple[str, str]] = [
    ("$ python3 run.py test                     # or: make test", S),
    ("", S),
    ("runtime", D),
    ("  aiauc01_aia_uc01 v1", D),
    ("    arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/aiauc01_aia_uc01-R3MXCi9yld", W),
    ("  PASS assert_runtime_1", G),
    ("    the runtime exists in the target region and reports status READY", S),
    ("  session 771b1dec-1664-4e54-9e69-409233cfbd5d - 16 events - tools ['add_numbers']", D),
    ("  reply 'The refund total should be $42.'", W),
    ("  PASS assert_runtime_2", G),
    ("    invoking it answers a tool-using prompt and the reply has no model scaffolding", S),
    ("", S),
    ("observability", D),
    ("  trace 1-6ad4087a-7220c9ed52be46e901c25cc9   span 'execute_tool add_numbers'", T),
    ("  PASS assert_observability_1", G),
    ("    that same invoke left an X-Ray trace whose span tree contains an execute_tool span", S),
    ("", S),
    ("  PASS independence: no other use case's resources present", G),
    ("", S),
    ("4 passed, 0 failed", W),
]


# --------------------------------------------------------------------------- #
# figure 1: what the runtime is, and who owns which part                      #
# --------------------------------------------------------------------------- #

def figure_architecture() -> None:
    w, h = 1440, 940
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img">',
        "<title>A support agent as a managed runtime: the folder you own becomes four tagged resources, "
        "and the runtime talks to Bedrock and to CloudWatch.</title>",
        "<defs>",
        '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{BG0}"/><stop offset="1" stop-color="{BG1}"/></linearGradient>',
        '<radialGradient id="gA" cx="0.10" cy="0.05" r="0.7">'
        f'<stop offset="0" stop-color="{BLUE}" stop-opacity="0.24"/>'
        f'<stop offset="1" stop-color="{BLUE}" stop-opacity="0"/></radialGradient>',
        '<radialGradient id="gB" cx="0.90" cy="0.95" r="0.75">'
        f'<stop offset="0" stop-color="{TEAL}" stop-opacity="0.20"/>'
        f'<stop offset="1" stop-color="{TEAL}" stop-opacity="0"/></radialGradient>',
        '<marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="#60a5fa"/></marker>',
        '<marker id="ah2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="#5eead4"/></marker>',
        "</defs>",
        f'<rect width="{w}" height="{h}" fill="url(#bg)"/>',
        f'<rect width="{w}" height="{h}" fill="url(#gA)"/>',
        f'<rect width="{w}" height="{h}" fill="url(#gB)"/>',
        '<g font-family="ui-sans-serif, -apple-system, \'Helvetica Neue\', Arial, sans-serif">',
    ]

    def text(x, y, s, size=19, fill=SOFT, weight=400, anchor="start", mono=False):
        fam = MONO if mono else "inherit"
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" '
                 f'text-anchor="{anchor}" font-family="{fam}">{html.escape(s)}</text>')

    def box(x, y, bw, bh, fill, stroke, rx=16, op=1.0):
        p.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="{rx}" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="1.6" opacity="{op}"/>')

    def zone(x, y, bw, bh, label, colour):
        p.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="22" fill="#0b1428" '
                 f'fill-opacity="0.55" stroke="{colour}" stroke-width="1.4" stroke-dasharray="7 7"/>')
        p.append(f'<rect x="{x+22}" y="{y-13}" width="{len(label)*11+26}" height="26" rx="13" fill="{BG1}"/>')
        text(x + 35, y + 6, label, 17, colour, 700)

    def chip(x, y, bw, bh, label, colour, size=16):
        box(x, y, bw, bh, "#101c36", colour, rx=10)
        text(x + bw / 2, y + bh / 2 + 5, label, size, colour, 500, "middle", mono=True)

    # header
    text(60, 66, "ONE FOLDER IN, FOUR TAGGED RESOURCES OUT", 17, ORANGE, 700)
    text(60, 112, "Your first support agent on AgentCore Runtime", 40, "#ffffff", 800)
    text(60, 146, "measured in us-east-1, 2026-10-18", 18, DIM)

    # ---------- left: what you own ----------
    zone(60, 210, 340, 470, "YOU OWN", BLUE)
    text(82, 258, "usecases/01-first-agent/", 19, "#ffffff", 700, mono=True)
    chip(82, 288, 296, 44, "agentcore.json   the contract", BLUE, 14)
    chip(82, 344, 296, 44, "aws-targets.json   the region", BLUE, 14)
    chip(82, 400, 296, 44, "app/aia_uc01/main.py", BLUE, 14)

    box(82, 462, 296, 176, "#0e1830", "#233052", rx=14)
    text(102, 492, "main.py holds everything", 15, SOFT)
    text(102, 514, "the support agent knows:", 15, SOFT)
    text(102, 546, "SYSTEM_PROMPT   desk tone", 14, TEAL, 500, mono=True)
    text(102, 570, "add_numbers     one tool", 14, TEAL, 500, mono=True)
    text(102, 594, "StreamSanitizer clean text", 14, TEAL, 500, mono=True)
    text(102, 624, "no database, no tickets", 13, DIM, 400, mono=True)

    # ---------- arrow: deploy ----------
    p.append('<path d="M 414 445 L 586 445" stroke="#60a5fa" stroke-width="2.6" '
             'stroke-dasharray="8 6" marker-end="url(#ah)"/>')
    text(500, 424, "agentcore deploy", 18, "#93c5fd", 700, "middle", mono=True)
    text(500, 482, "CodeZip + CDK synth", 15, DIM, 400, "middle", mono=True)
    text(500, 504, "1 m 51 s, measured", 15, DIM, 400, "middle", mono=True)

    # ---------- right: AWS ----------
    zone(600, 210, 780, 470, "AWS  us-east-1", TEAL)
    text(1356, 258, "account 123456789012", 15, DIM, 400, "end", mono=True)
    text(624, 258, "CloudFormation stack: AgentCore-aiauc01-default", 19, "#ffffff", 700, mono=True)

    # runtime
    box(624, 288, 432, 356, "#101c36", BLUE, rx=16)
    p.append(f'<rect x="624" y="288" width="432" height="6" rx="3" fill="{BLUE}"/>')
    text(648, 322, "AgentCore Runtime", 20, "#93c5fd", 700)
    text(648, 346, "aiauc01_aia_uc01", 17, "#ffffff", 600, mono=True)
    text(648, 372, "one microVM per session, serverless", 14, DIM)
    chip(648, 392, 122, 34, "GET /ping", SOFT, 14)
    chip(780, 392, 158, 34, "POST /invocations", SOFT, 14)
    chip(948, 392, 92, 34, "HTTP", SOFT, 14)
    box(648, 442, 384, 74, "#0d1729", "#243352", rx=12)
    text(668, 470, "- your main.py runs here, unchanged", 15, SOFT)
    text(668, 496, "- stream_async yields one SSE per token", 15, SOFT)
    box(648, 532, 384, 90, "#0d1729", "#243352", rx=12)
    text(668, 560, "Agent per session_id, capped at 128", 15, SOFT)
    text(668, 586, "NullConversationManager: no history kept", 14, DIM)
    text(668, 610, "UC02 replaces this with Memory", 14, DIM)

    # role + identity
    box(1080, 288, 264, 168, "#101c36", PURPLE, rx=16)
    p.append(f'<rect x="1080" y="288" width="264" height="6" rx="3" fill="{PURPLE}"/>')
    text(1102, 322, "IAM role, one per runtime", 16, "#c4b5fd", 700)
    text(1102, 350, "bedrock:InvokeModel*", 14, SOFT, mono=True)
    text(1102, 374, "logs:*  -> runtime log group", 13, SOFT, mono=True)
    text(1102, 398, "xray:PutTraceSegments", 14, SOFT, mono=True)
    text(1102, 430, "least privilege, generated", 13, DIM)

    box(1080, 476, 264, 168, "#101c36", ORANGE, rx=16)
    p.append(f'<rect x="1080" y="476" width="264" height="6" rx="3" fill="{ORANGE}"/>')
    text(1102, 510, "tags -> auditable cleanup", 16, "#fdba74", 700)
    text(1102, 538, "Project=agentcore-in-action", 12.5, SOFT, mono=True)
    text(1102, 562, "UseCase=01", 13, SOFT, mono=True)
    text(1102, 586, "AutoDelete=true", 13, SOFT, mono=True)
    text(1102, 618, "make down reads these", 13, DIM)

    # ---------- two things it talks to ----------
    p.append('<path d="M 840 286 L 840 188" stroke="#5eead4" stroke-width="2.6" marker-end="url(#ah2)"/>')
    box(624, 118, 432, 62, "#101c36", TEAL, rx=14)
    text(648, 148, "Amazon Bedrock  ·  deepseek.v3.2", 19, "#5eead4", 700, mono=True)
    text(648, 170, "ConverseStream  -  $0.62 / $1.85 per 1M tokens", 13, DIM)

    p.append('<path d="M 840 646 L 840 738" stroke="#5eead4" stroke-width="2.6" marker-end="url(#ah2)"/>')
    box(624, 748, 432, 62, "#101c36", TEAL, rx=14)
    text(648, 778, "CloudWatch logs + X-Ray traces", 19, "#5eead4", 700, mono=True)
    text(648, 800, "the reason this article can say where the time went", 13, DIM)

    # ---------- footer of measured facts ----------
    box(60, 730, 500, 172, "#0b1428", "#233052", rx=16)
    text(88, 766, "measured on this run", 16, ORANGE, 700)
    for i, (k, v) in enumerate([
        ("deploy, cold stack", "1 m 51 s"),
        ("invoke, cold session", "9 911 ms"),
        ("invoke_agent span", "2.50 s"),
        ("tokens per invoke", "945 in / 71 out"),
        ("model cost per invoke", "$0.00072"),
    ]):
        y = 800 + i * 22
        p.append(f'<circle cx="94" cy="{y-5}" r="3.5" fill="{ORANGE}"/>')
        text(108, y, k, 15, DIM)
        text(480, y, v, 15, "#ffffff", 600, "end", mono=True)

    box(1080, 730, 300, 172, "#0b1428", "#233052", rx=16)
    text(1104, 766, "what you never write", 16, RED, 700)
    for i, s in enumerate([
        "no Dockerfile",
        "no task definition",
        "no load balancer",
        "no IAM policy document",
        "no OTEL exporter config",
    ]):
        y = 798 + i * 22
        p.append(f'<circle cx="1118" cy="{y-5}" r="3.5" fill="{RED}"/>')
        text(1130, y, s, 15, SOFT)

    p.append("</g></svg>")
    (HERE / "F1-support-agent-runtime.svg").write_text("\n".join(p) + "\n", encoding="utf-8")


def figure_loop() -> None:
    """The five commands that make up the loop, with what each one costs you."""
    w, h = 1440, 620
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img">',
        "<title>The deploy loop: doctor, dev, deploy, invoke, traces, down, with the measured "
        "output each one returns.</title>",
        "<defs>",
        '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{BG0}"/><stop offset="1" stop-color="{BG1}"/></linearGradient>',
        '<radialGradient id="gA" cx="0.15" cy="0.1" r="0.8">'
        f'<stop offset="0" stop-color="{PURPLE}" stop-opacity="0.22"/>'
        f'<stop offset="1" stop-color="{PURPLE}" stop-opacity="0"/></radialGradient>',
        "</defs>",
        f'<rect width="{w}" height="{h}" fill="url(#bg)"/>',
        f'<rect width="{w}" height="{h}" fill="url(#gA)"/>',
        '<g font-family="ui-sans-serif, -apple-system, \'Helvetica Neue\', Arial, sans-serif">',
        f'<text x="60" y="66" font-size="17" fill="{ORANGE}" font-weight="700">'
        "THE WHOLE LOOP IN SIX COMMANDS</text>",
        f'<text x="60" y="112" font-size="38" fill="#ffffff" font-weight="800">One loop, reproducible</text>',
        f'<text x="60" y="146" font-size="18" fill="{DIM}">every output below was captured while writing this article</text>',
    ]

    steps = [
        ("doctor", "15 passed, 0 warned, 0 failed", "local", "n/a", TEAL),
        ("dev", "Uvicorn on 127.0.0.1:8080", "real model", "~$0.0007 / call", BLUE),
        ("deploy", "Runtime: READY", "stack create", "1 m 51 s", PURPLE),
        ("invoke", "'The refund total should be $42.'", "one session", "9 911 ms", GREEN),
        ("traces get", "execute_tool add_numbers", "X-Ray", "about 2 min lag", ORANGE),
        ("down", "0 resources tagged UseCase=01", "stack delete", "1 m 28 s", RED),
    ]
    x0, y0, cw, ch = 60, 196, 208, 356
    gap = 22
    for i, (cmd, result, kind, metric, colour) in enumerate(steps):
        x = x0 + i * (cw + gap)
        p.append(f'<rect x="{x}" y="{y0}" width="{cw}" height="{ch}" rx="16" fill="#101c36" '
                 f'stroke="{colour}" stroke-width="1.6"/>')
        p.append(f'<rect x="{x}" y="{y0}" width="{cw}" height="6" rx="3" fill="{colour}"/>')
        p.append(f'<text x="{x+22}" y="{y0+46}" font-size="15" fill="{DIM}" font-family="{MONO}">step {i+1}</text>')
        p.append(f'<text x="{x+22}" y="{y0+80}" font-size="24" fill="#ffffff" font-weight="700" '
                 f'font-family="{MONO}">{html.escape(cmd)}</text>')
        # wrapped result text
        words, line, lines = result.split(), "", []
        for word in words:
            if len(line) + len(word) + 1 > 22:
                lines.append(line)
                line = word
            else:
                line = f"{line} {word}".strip()
        lines.append(line)
        y = y0 + 122
        for ln in lines:
            p.append(f'<text x="{x+22}" y="{y}" font-size="15" fill="{SOFT}" '
                     f'font-family="{MONO}">{html.escape(ln)}</text>')
            y += 24
        p.append(f'<line x1="{x+22}" y1="{y0+ch-96}" x2="{x+cw-22}" y2="{y0+ch-96}" '
                 f'stroke="{colour}" stroke-opacity="0.35" stroke-width="1"/>')
        p.append(f'<text x="{x+22}" y="{y0+ch-70}" font-size="14" fill="{DIM}">{html.escape(kind)}</text>')
        p.append(f'<text x="{x+22}" y="{y0+ch-38}" font-size="18" fill="{colour}" font-weight="700" '
                 f'font-family="{MONO}">{html.escape(metric)}</text>')
        if i < len(steps) - 1:
            p.append(f'<text x="{x+cw+gap/2}" y="{y0+ch/2+7}" font-size="20" fill="#3b4a68" '
                     f'text-anchor="middle">&#8250;</text>')
    p.append("</g></svg>")
    (HERE / "F2-deploy-loop.svg").write_text("\n".join(p) + "\n", encoding="utf-8")


def figure_span_tree() -> None:
    """The span tree, drawn from the X-Ray trace of the invoke above."""
    w, h = 1440, 520
    rows = [
        (0, "invoke_agent Strands Agents", "2.50 s", "tools=[\"add_numbers\"]  945 in / 71 out", TEAL),
        (1, "execute_event_loop_cycle  cycle 1", "0.68 s", "the model asks for the tool", SOFT),
        (2, "chat  deepseek.v3.2", "0.68 s", "431 in / 60 out", ORANGE),
        (3, "BedrockRuntime  ConverseStream", "0.67 s", "finish_reason=tool_use", DIM),
        (1, "execute_event_loop_cycle  cycle 2", "1.82 s", "the model reads the tool result", SOFT),
        (2, "chat  deepseek.v3.2", "1.82 s", "514 in / 11 out", ORANGE),
        (3, "BedrockRuntime  ConverseStream", "1.80 s", "finish_reason=end_turn", DIM),
        (2, "execute_tool add_numbers", "success", "gen_ai.tool.name=add_numbers", GREEN),
    ]
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img">',
        "<title>The X-Ray span tree of one invoke: two model round trips and one execute_tool span.</title>",
        "<defs>",
        '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{BG0}"/><stop offset="1" stop-color="{BG1}"/></linearGradient>',
        "</defs>",
        f'<rect width="{w}" height="{h}" fill="url(#bg)"/>',
        '<g font-family="ui-sans-serif, -apple-system, \'Helvetica Neue\', Arial, sans-serif">',
        f'<text x="60" y="62" font-size="17" fill="{ORANGE}" font-weight="700">'
        "WHAT OBSERVABILITY RECORDED</text>",
        f'<text x="60" y="106" font-size="34" fill="#ffffff" font-weight="800">The agent loop, one span per step</text>',
        f'<text x="60" y="136" font-size="17" fill="{DIM}">trace 1-6ad4087a-7220c9ed52be46e901c25cc9</text>',
    ]
    y = 190
    for depth, name, metric, note, colour in rows:
        x = 70 + depth * 42
        if depth:
            p.append(f'<line x1="{x-24}" y1="{y-8}" x2="{x-24}" y2="{y+16}" '
                     f'stroke="#334155" stroke-width="1.6"/>')
            p.append(f'<line x1="{x-24}" y1="{y+14}" x2="{x-6}" y2="{y+14}" '
                     f'stroke="#334155" stroke-width="1.6"/>')
        p.append(f'<text x="{x}" y="{y+14}" font-size="18.5" fill="{colour}" font-weight="'
                 f'{700 if depth == 0 else 500}" font-family="{MONO}">{html.escape(name)}</text>')
        p.append(f'<text x="{w-480}" y="{y+14}" font-size="17" fill="#ffffff" font-weight="600" '
                 f'font-family="{MONO}">{html.escape(metric)}</text>')
        p.append(f'<text x="{w-330}" y="{y+14}" font-size="15" fill="{DIM}">{html.escape(note)}</text>')
        y += 38
    p.append(f'<text x="70" y="{h-32}" font-size="15" fill="{DIM}">'
             "spans are asynchronous: they took about two minutes to become queryable in this account</text>")
    p.append("</g></svg>")
    (HERE / "F3-span-tree.svg").write_text("\n".join(p) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# covers                                                                      #
# --------------------------------------------------------------------------- #

def cover() -> None:
    w, h = 1200, 675
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img">',
        "<title>Cover: your first agent as a service. A support agent deployed on AgentCore Runtime, "
        "measured in us-east-1.</title>",
        "<defs>",
        '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{BG0}"/><stop offset="1" stop-color="{BG1}"/></linearGradient>',
        '<radialGradient id="gA" cx="0.12" cy="0.06" r="0.75">'
        f'<stop offset="0" stop-color="{ORANGE}" stop-opacity="0.22"/>'
        f'<stop offset="1" stop-color="{ORANGE}" stop-opacity="0"/></radialGradient>',
        '<radialGradient id="gB" cx="0.95" cy="0.92" r="0.8">'
        f'<stop offset="0" stop-color="{BLUE}" stop-opacity="0.26"/>'
        f'<stop offset="1" stop-color="{BLUE}" stop-opacity="0"/></radialGradient>',
        '<radialGradient id="gC" cx="0.45" cy="1.15" r="0.6">'
        f'<stop offset="0" stop-color="{TEAL}" stop-opacity="0.20"/>'
        f'<stop offset="1" stop-color="{TEAL}" stop-opacity="0"/></radialGradient>',
        '<linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="#463414"/><stop offset="1" stop-color="#1b2236"/></linearGradient>',
        '<linearGradient id="g2" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="#0d403c"/><stop offset="1" stop-color="#1b2236"/></linearGradient>',
        '<linearGradient id="g3" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="#173561"/><stop offset="1" stop-color="#1b2236"/></linearGradient>',
        '<clipPath id="c1"><rect x="72" y="400" width="336" height="196" rx="18"/></clipPath>',
        '<clipPath id="c2"><rect x="432" y="400" width="336" height="196" rx="18"/></clipPath>',
        '<clipPath id="c3"><rect x="792" y="400" width="336" height="196" rx="18"/></clipPath>',
        "</defs>",
        f'<rect width="{w}" height="{h}" fill="url(#bg)"/>',
        f'<rect width="{w}" height="{h}" fill="url(#gA)"/>',
        f'<rect width="{w}" height="{h}" fill="url(#gB)"/>',
        f'<rect width="{w}" height="{h}" fill="url(#gC)"/>',
        '<g font-family="ui-sans-serif, -apple-system, \'Helvetica Neue\', Arial, sans-serif">',
        f'<rect x="72" y="72" width="42" height="5" rx="2.5" fill="{ORANGE}"/>',
        f'<text x="130" y="81" font-size="19" font-weight="700" letter-spacing="3" fill="#fb923c">'
        "RUNTIME + OBSERVABILITY · MEASURED</text>",
        f'<text x="72" y="196" font-size="82" font-weight="800" fill="#ffffff">YOUR FIRST AGENT</text>',
        f'<text x="72" y="288" font-size="82" font-weight="800" fill="#ffffff">AS A <tspan fill="#38bdf8">SERVICE</tspan></text>',
        f'<text x="72" y="334" font-size="23" fill="#a6b6cd">A support agent on AgentCore Runtime, end to end</text>',
        f'<text x="72" y="364" font-size="18" fill="{DIM}" font-family="{MONO}">'
        "agentcore deploy -y --target default</text>",
    ]
    cards = [
        (72, "#f59e0b", "#fcd34d", "ONE FOLDER", "the support prompt + one tool", "no Dockerfile anywhere", "#f59e0b"),
        (432, "#14b8a6", "#5eead4", "ONE COMMAND", "1 m 51 s to READY", "9 911 ms per cold invoke", "#14b8a6"),
        (792, "#3b82f6", "#93c5fd", "ONE TRACE", "execute_tool add_numbers", "945 tokens in, 71 out", "#3b82f6"),
    ]
    for x, accent, bright, title, sub1, sub2, edge in cards:
        p.append(f'<rect x="{x}" y="400" width="336" height="196" rx="18" fill="url(#g'
                 f'{1 if x == 72 else 2 if x == 432 else 3})" stroke="{edge}" stroke-opacity="0.6" stroke-width="1.5"/>')
        cid = "c1" if x == 72 else "c2" if x == 432 else "c3"
        p.append(f'<g clip-path="url(#{cid})"><rect x="{x}" y="400" width="336" height="7" fill="{accent}"/></g>')
        p.append(f'<text x="{x+26}" y="466" font-size="34" font-weight="800" fill="{bright}">{title}</text>')
        p.append(f'<text x="{x+26}" y="498" font-size="18" fill="#cbd5e1">{sub1}</text>')
        p.append(f'<line x1="{x+26}" y1="524" x2="{x+310}" y2="524" stroke="{accent}" stroke-opacity="0.35" stroke-width="1"/>')
        p.append(f'<text x="{x+26}" y="554" font-size="15.5" fill="{bright}">{sub2}</text>')
    p.append("</g></svg>")
    (HERE / "cover.svg").write_text("\n".join(p) + "\n", encoding="utf-8")


def cover_devto() -> None:
    w, h = 1000, 420
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img">',
        "<title>Cover: your first agent as a service. Deploying a support agent on AgentCore.</title>",
        "<defs>",
        '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{BG0}"/><stop offset="1" stop-color="{BG1}"/></linearGradient>',
        '<radialGradient id="gA" cx="0.9" cy="0.1" r="0.8">'
        f'<stop offset="0" stop-color="{BLUE}" stop-opacity="0.26"/>'
        f'<stop offset="1" stop-color="{BLUE}" stop-opacity="0"/></radialGradient>',
        '<radialGradient id="gB" cx="0.1" cy="1.0" r="0.7">'
        f'<stop offset="0" stop-color="{ORANGE}" stop-opacity="0.22"/>'
        f'<stop offset="1" stop-color="{ORANGE}" stop-opacity="0"/></radialGradient>',
        "</defs>",
        f'<rect width="{w}" height="{h}" fill="url(#bg)"/>',
        f'<rect width="{w}" height="{h}" fill="url(#gA)"/>',
        f'<rect width="{w}" height="{h}" fill="url(#gB)"/>',
        '<g font-family="ui-sans-serif, -apple-system, \'Helvetica Neue\', Arial, sans-serif">',
        f'<rect x="56" y="62" width="38" height="5" rx="2.5" fill="{ORANGE}"/>',
        f'<text x="108" y="70" font-size="16" font-weight="700" letter-spacing="2.5" fill="#fb923c">'
        "AGENTCORE IN ACTION · USE CASE 01</text>",
        f'<text x="56" y="164" font-size="62" font-weight="800" fill="#ffffff">YOUR FIRST AGENT</text>',
        f'<text x="56" y="236" font-size="62" font-weight="800" fill="#ffffff">AS A <tspan fill="#38bdf8">SERVICE</tspan></text>',
        f'<text x="56" y="278" font-size="20" fill="#a6b6cd">Deploying a support agent on Bedrock AgentCore</text>',
        f'<text x="56" y="318" font-size="17" fill="{DIM}" font-family="{MONO}">'
        "deploy 1 m 51 s   invoke 9 911 ms   945 tokens</text>",
    ]
    tags = [("Runtime: READY", GREEN), ("execute_tool add_numbers", TEAL), ("no Dockerfile", PURPLE)]
    x = 56
    for label, colour in tags:
        bw = len(label) * 10 + 28
        p.append(f'<rect x="{x}" y="344" width="{bw}" height="34" rx="17" fill="{colour}" opacity="0.18"/>')
        p.append(f'<text x="{x+14}" y="366" font-size="15" fill="{colour}" font-weight="600" '
                 f'font-family="{MONO}">{html.escape(label)}</text>')
        x += bw + 14
    p.append("</g></svg>")
    (HERE / "cover-devto.svg").write_text("\n".join(p) + "\n", encoding="utf-8")


def main() -> None:
    shell_box("S1-deploy", "terminal - deploy", DEPLOY, "captured from evidence/06-deploy-raw.txt and the deploy log")
    shell_box("S2-status-invoke", "terminal - status and invoke", STATUS_INVOKE,
              "captured from evidence/07-status-after.txt and evidence/08-invoke-raw.txt")
    shell_box("S3-trace", "terminal - one trace", TRACE,
              "captured from the X-Ray trace behind evidence/13-span-tree.txt")
    shell_box("S4-verify", "terminal - the four assertions", SMOKE, "captured from evidence/09-smoke-raw.txt")
    figure_architecture()
    figure_loop()
    figure_span_tree()
    cover()
    cover_devto()
    print("wrote", len(list(HERE.glob("*.svg"))), "svg files in", HERE)


if __name__ == "__main__":
    main()
