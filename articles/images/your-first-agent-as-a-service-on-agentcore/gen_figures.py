#!/usr/bin/env python3
"""Generate every image for the uc01 article from the run captured on 2026-10-18.

Every line drawn here comes from `usecases/01-first-agent/evidence/`, files
30 to 48. The terminal panels are the captured output with the account id
redacted to 123456789012, with the spinner frames and the blank lines between
progress steps removed, and with lines longer than the panel wrapped. Nothing
else is changed and nothing is invented.

    python3 gen_figures.py            # writes every .svg next to this file
    render.sh                         # svg -> png, see the comment at the bottom
"""

from __future__ import annotations

import html
import pathlib
import textwrap

HERE = pathlib.Path(__file__).resolve().parent

BG0, BG1 = "#0a1024", "#0d1c3a"
BLUE, PURPLE, ORANGE, GREEN, RED, TEAL = (
    "#2563eb", "#7c3aed", "#ea580c", "#059669", "#e11d48", "#0d9488",
)
SOFT = "#cbd5e1"
DIM = "#8ea0bd"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

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


def shell_box(name: str, title: str, lines: list[tuple[str, str]], subtitle: str = "") -> None:
    """Render captured terminal output as an SVG panel.

    Each line is (text, colour). Leading spaces are preserved, so what you see
    is what the terminal printed, minus the spinner frames.
    """
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


# ── the commands the article runs, and what each one printed ─────────────── #
# Sources: evidence/30-deploy.txt, 32-status.txt, 33-invoke.txt,
# 35-traces-list.txt, 36-trace-get.txt, 37-trace-spans.txt,
# 38-independence.txt, 40-remove-all.txt, 41-reconcile-deploy.txt,
# 42-status-after-down.txt.

DEPLOY: list[tuple[str, str]] = [
    ("$ agentcore deploy -y --target default", S),
    ("✓ Load deployment target", G),
    ("✓ Validate project", G),
    ("✓ Sync CDK dependencies", G),
    ("✓ Build CDK project", G),
    ("✓ Synthesize CloudFormation", G),
    ("✓ Check bootstrap status", G),
    ("✓ Check stack status", G),
    ("✓ Deploy to AWS", G),
    ("✓ Persist deployment state", G),
    ("", S),
    ("✓ Deployed to 'default' (stack: AgentCore-aiauc01-default)", G),
    ("", S),
    ("Outputs:", S),
    ("  ApplicationAgentAiaUc01RoleArnOutput1102B050: arn:aws:iam::123456789012:role/AgentCore-aiauc01-default-ApplicationAgentAiaUc01Ru-aFroZwTcmDts", W),
    ("  ApplicationAgentAiaUc01RuntimeIdOutput734A07B7: aiauc01_aia_uc01-XyX3fXF14g", W),
    ("  ApplicationAgentAiaUc01RuntimeArnOutput3227EF65: arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/aiauc01_aia_uc01-XyX3fXF14g", W),
    ("  StackNameOutput: AgentCore-aiauc01-default", W),
    ("", S),
    ("Note: Transaction search enabled. It takes ~10 minutes for transaction search to be fully active and for traces from invocations to be indexed.", D),
    ("Next: agentcore invoke | agentcore status", D),
    ("Log: agentcore/.cli/logs/deploy/deploy-20261018-132205.log", D),
]

STATUS: list[tuple[str, str]] = [
    ("$ agentcore status", S),
    ("AgentCore Status (target: default, us-east-1)", S),
    ("", S),
    ("Agents", S),
    ("  aia_uc01: Deployed - Runtime: READY (arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/aiauc01_aia_uc01-XyX3fXF14g)", G),
    ("  URL: https://bedrock-agentcore.us-east-1.amazonaws.com/runtimes/arn%3Aaws%3Abedrock-agentcore%3Aus-east-1%3A123456789012%3Aruntime%2Faiauc01_aia_uc01-XyX3fXF14g/invocations", W),
]

INVOKE: list[tuple[str, str]] = [
    ('$ agentcore invoke --prompt "A customer returns two items priced 21 each. What refund total should I quote? Use the tool."', S),
    ("", S),
    ("I'll use the tool to calculate the refund total.", W),
    ("", S),
    ("The refund total you should quote is $42.", W),
    ("", S),
    ("Session: 75596b56-1b64-4c4e-9225-8074940fbb87", T),
    ("To resume: agentcore invoke --session-id 75596b56-1b64-4c4e-9225-8074940fbb87", D),
    ("Log: agentcore/.cli/logs/invoke/invoke-aia_uc01-20261018-132438.log", D),
]

TRACES_LIST: list[tuple[str, str]] = [
    ("$ agentcore traces list", S),
    ("Traces for aia_uc01 (target: default)", S),
    ("", S),
    ("Trace ID                     Timestamp          Session ID", D),
    ("6ad45817558974710d8c3b6d35f5 2026-10-18         75596b56-1b64-4c4e-9225-8074940f", W),
    ("a089                         05:24:48Z          bb87", W),
    ("", S),
    ("Console: https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1#/gen-ai-observability/agent-core/agent-alias/aiauc01_aia_uc01-XyX3fXF14g/endpoint/DEFAULT/agent/aia_uc01?start=-43200000&resourceId=arn%3Aaws%3Abedrock-agentcore%3Aus-east-1%3A123456789012%3Aruntime%2Faiauc01_aia_uc01-XyX3fXF14g%2Fruntime-endpoint%2FDEFAULT%3ADEFAULT&serviceName=aia_uc01.DEFAULT&tabId=traces", D),
    ("Note: Traces may take 2-3 minutes to appear in CloudWatch", D),
]

TRACE_GET: list[tuple[str, str]] = [
    ("$ agentcore traces get 6ad45817558974710d8c3b6d35f5a089", S),
    ("Trace saved to:", S),
    ("/Users/pinxiong/Documents/Important/bedrock-agentcore-in-action/usecases/01-first-agent/agentcore/.cli/traces/aia_uc01-6ad45817558974710d8c3b6d35f5a089.json", W),
    ("Console: https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1#/gen-ai-observability/agent-core/agent-alias/aiauc01_aia_uc01-XyX3fXF14g/endpoint/DEFAULT/agent/aia_uc01?start=-43200000&resourceId=arn%3Aaws%3Abedrock-agentcore%3Aus-east-1%3A123456789012%3Aruntime%2Faiauc01_aia_uc01-XyX3fXF14g%2Fruntime-endpoint%2FDEFAULT%3ADEFAULT&serviceName=aia_uc01.DEFAULT&tabId=traces", D),
]

SPANS: list[tuple[str, str]] = [
    ("""$ jq -r '[.[] ."@message" | select(type == "object" and .name != null)] as $spans""", S),
    ("""      | ($spans | map({(.spanId): .name}) | add) as $parent""", S),
    ("""      | $spans | sort_by(.startTimeUnixNano) | .[] | (.attributes // {}) as $a""", S),
    ("""      | [.name, .kind, (((.durationNano // 0) / 1000000 | floor | tostring) + " ms"),""", S),
    ("""         (if $a["gen_ai.usage.input_tokens"] then ($a["gen_ai.usage.input_tokens"] | tostring)""", S),
    ("""            + " in / " + ($a["gen_ai.usage.output_tokens"] | tostring) + " out" else "-" end),""", S),
    ("""         ($parent[.parentSpanId // ""] // "root")] | @tsv' \\""", S),
    ("  agentcore/.cli/traces/aia_uc01-6ad45817558974710d8c3b6d35f5a089.json | column -t -s $'\\t'", S),
    ("", S),
    ("POST /invocations            SERVER    2574 ms  -                root", T),
    ("invoke_agent Strands Agents  INTERNAL  2428 ms  955 in / 81 out  POST /invocations", T),
    ("execute_event_loop_cycle     INTERNAL  1906 ms  -                invoke_agent Strands Agents", S),
    ("chat                         INTERNAL  1903 ms  431 in / 70 out  execute_event_loop_cycle", O),
    ("chat deepseek.v3.2           CLIENT    1886 ms  431 in / 70 out  chat", O),
    ("execute_tool add_numbers     INTERNAL  1 ms     -                execute_event_loop_cycle", G),
    ("execute_event_loop_cycle     INTERNAL  520 ms   -                invoke_agent Strands Agents", S),
    ("chat                         INTERNAL  519 ms   524 in / 11 out  execute_event_loop_cycle", O),
    ("chat deepseek.v3.2           CLIENT    517 ms   524 in / 11 out  chat", O),
]

INDEPENDENCE: list[tuple[str, str]] = [
    ("$ aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=agentcore-in-action \\", S),
    ("    --region us-east-1 --query 'ResourceTagMappingList[].{arn:ResourceARN,tags:Tags[?Key==`UseCase`].Value|[0]}' --output text", S),
    ("", S),
    ("arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/aiauc01_aia_uc01-XyX3fXF14g/runtime-endpoint/DEFAULT  01", W),
    ("arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/aiauc01_aia_uc01-XyX3fXF14g                          01", W),
    ("arn:aws:bedrock-agentcore:us-east-1:123456789012:workload-identity-directory/default/workload-identity/aiauc01_aia_uc01-XyX3fXF14g  01", W),
]

TEARDOWN: list[tuple[str, str]] = [
    ("$ agentcore remove all -y", S),
    ("All schemas reset to empty state", O),
    ("Your source code has not been modified. Run `agentcore deploy` to apply changes to AWS.", O),
    ("", S),
    ("$ agentcore deploy -y --target default", S),
    ("✓ Load deployment target", G),
    ("✓ Validate project", G),
    ("✓ Validate AWS credentials", G),
    ("✓ Sync CDK dependencies", G),
    ("✓ Build CDK project", G),
    ("✓ Synthesize CloudFormation", G),
    ("✓ Check bootstrap status", G),
    ("✓ Check stack status", G),
    ("✓ Deploy to AWS", G),
    ("✓ Tear down stack", G),
    ("", S),
    ("✓ Deployed to 'default' (stack: AgentCore-aiauc01-default)", G),
    ("", S),
    ("Log: agentcore/.cli/logs/deploy/deploy-20261018-133429.log", D),
    ("", S),
    ("$ agentcore status", S),
    ("AgentCore Status (target: )", S),
    ("No resources match the given filters.", O),
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
    text(500, 504, "1 m 31 s, measured", 15, DIM, 400, "middle", mono=True)

    # ---------- right: AWS ----------
    zone(600, 210, 780, 470, "AWS  us-east-1", TEAL)
    text(1356, 258, "account 123456789012", 15, DIM, 400, "end", mono=True)
    text(624, 258, "CloudFormation stack: AgentCore-aiauc01-default", 19, "#ffffff", 700, mono=True)

    # runtime
    box(624, 288, 432, 356, "#101c36", BLUE, rx=16)
    p.append(f'<rect x="624" y="288" width="432" height="6" rx="3" fill="{BLUE}"/>')
    text(648, 322, "AgentCore Runtime", 20, "#93c5fd", 700)
    text(648, 346, "aiauc01_aia_uc01-XyX3fXF14g", 17, "#ffffff", 600, mono=True)
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
    text(1102, 618, "get-resources reads these", 13, DIM)

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
        ("deploy, cold stack", "1 m 31 s"),
        ("invoke, cold session", "9 954 ms"),
        ("invoke_agent span", "2.43 s"),
        ("tokens per invoke", "955 in / 81 out"),
        ("model cost per invoke", "$0.00074"),
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
    """The six native commands that make up the loop, with what each one costs."""
    w, h = 1440, 620
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img">',
        "<title>The deploy loop: deploy, status, invoke, traces list, traces get, remove all, "
        "with the measured output each one returns.</title>",
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
        ("deploy -y", "Runtime: READY", "stack create", "1 m 31 s", PURPLE),
        ("status", "Deployed - READY", "one read", "under 1 s", BLUE),
        ("invoke", "quotes $42", "one session", "9 954 ms", GREEN),
        ("traces list", "1 trace, 1 session", "X-Ray", "about 3 min lag", ORANGE),
        ("traces get", "execute_tool add_numbers", "one JSON file", "62 kB", TEAL),
        ("remove all", "0 tagged resources", "then deploy again", "1 m 40 s", RED),
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
    p.append(f'<text x="60" y="{h-28}" font-size="15" fill="{DIM}">'
             "every command above is `agentcore ...` or `aws ...`; this use case ships no script of its own</text>")
    p.append("</g></svg>")
    (HERE / "F2-deploy-loop.svg").write_text("\n".join(p) + "\n", encoding="utf-8")


def figure_span_tree() -> None:
    """The span tree, drawn from the trace of the invoke above."""
    w, h = 1440, 565
    rows = [
        (0, "POST /invocations", "2574 ms", "the runtime accepts the call", TEAL),
        (1, "invoke_agent Strands Agents", "2428 ms", "tools=[\"add_numbers\"]  955 in / 81 out", TEAL),
        (2, "execute_event_loop_cycle  cycle 1", "1906 ms", "the model asks for the tool", SOFT),
        (3, "chat  deepseek.v3.2", "1903 ms", "431 in / 70 out", ORANGE),
        (4, "chat deepseek.v3.2  ConverseStream", "1886 ms", "finish_reason=tool_use", DIM),
        (2, "execute_tool add_numbers", "1 ms", "gen_ai.tool.name=add_numbers", GREEN),
        (2, "execute_event_loop_cycle  cycle 2", "520 ms", "the model reads the tool result", SOFT),
        (3, "chat  deepseek.v3.2", "519 ms", "524 in / 11 out", ORANGE),
        (4, "chat deepseek.v3.2  ConverseStream", "517 ms", "finish_reason=end_turn", DIM),
    ]
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img">',
        "<title>The span tree of one invoke: two model round trips and one execute_tool span.</title>",
        "<defs>",
        '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{BG0}"/><stop offset="1" stop-color="{BG1}"/></linearGradient>',
        "</defs>",
        f'<rect width="{w}" height="{h}" fill="url(#bg)"/>',
        '<g font-family="ui-sans-serif, -apple-system, \'Helvetica Neue\', Arial, sans-serif">',
        f'<text x="60" y="62" font-size="17" fill="{ORANGE}" font-weight="700">'
        "WHAT OBSERVABILITY RECORDED</text>",
        f'<text x="60" y="106" font-size="34" fill="#ffffff" font-weight="800">The agent loop, one span per step</text>',
        f'<text x="60" y="136" font-size="17" fill="{DIM}">trace 6ad45817558974710d8c3b6d35f5a089</text>',
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
        y += 34
    p.append(f'<text x="70" y="{h-32}" font-size="15" fill="{DIM}">'
             "spans are asynchronous: this trace was queryable about three minutes after the invoke</text>")
    p.append("</g></svg>")
    (HERE / "F3-span-tree.svg").write_text("\n".join(p) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# covers                                                                      #
# --------------------------------------------------------------------------- #

COVER_TITLE = ("<title>Cover: your first agent as a service. A support agent deployed on "
               "AgentCore Runtime, measured in us-east-1.</title>")


def cover_parts() -> list[str]:
    """The cover composition, drawn at 1200x675.

    Returns the gradients, the background and the one open <g> that holds the
    artwork, so a caller can wrap it at any size.
    """
    w, h = 1200, 675
    p = [
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
        (432, "#14b8a6", "#5eead4", "ONE COMMAND", "1 m 31 s to READY", "9 954 ms per cold invoke", "#14b8a6"),
        (792, "#3b82f6", "#93c5fd", "ONE TRACE", "execute_tool add_numbers", "955 tokens in, 81 out", "#3b82f6"),
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
    return p


def cover() -> None:
    w, h = 1200, 675
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img">',
        COVER_TITLE,
    ]
    p += cover_parts()
    p.append("</g></svg>")
    (HERE / "cover.svg").write_text("\n".join(p) + "\n", encoding="utf-8")


def cover_medium() -> None:
    """The same composition at Medium's feature size, 1400x788 = the cover scaled 7/6."""
    w, h = 1400, 788
    scale = w / 1200
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img">',
        COVER_TITLE,
        f'<g transform="scale({scale:.6f})">',
    ]
    p += cover_parts()
    p.append("</g></g></svg>")
    (HERE / "cover-medium.svg").write_text("\n".join(p) + "\n", encoding="utf-8")


def cover_devto() -> None:
    # the 2.38:1 Dev.to cover is also its 1200x627 social card source, which
    # crops 9.8% off each side: the art keeps its proportions and sits on a
    # wider gradient field instead of being reflowed
    w, h = 1000, 420
    W = round(w / (1 - 2 * 0.105))
    H = round(W * h / w)
    px, py = (W - w) // 2, (H - h) // 2
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-px} {-py} {W} {H}" width="{W}" height="{H}" role="img">',
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
        f'<rect x="{-px}" y="{-py}" width="{W}" height="{H}" fill="url(#bg)"/>',
        f'<rect x="{-px}" y="{-py}" width="{W}" height="{H}" fill="url(#gA)"/>',
        f'<rect x="{-px}" y="{-py}" width="{W}" height="{H}" fill="url(#gB)"/>',
        f'<g font-family="ui-sans-serif, -apple-system, \'Helvetica Neue\', Arial, sans-serif">',
        f'<rect x="56" y="62" width="38" height="5" rx="2.5" fill="{ORANGE}"/>',
        f'<text x="108" y="70" font-size="16" font-weight="700" letter-spacing="2.5" fill="#fb923c">'
        "AGENTCORE IN ACTION · USE CASE 01</text>",
        f'<text x="56" y="164" font-size="62" font-weight="800" fill="#ffffff">YOUR FIRST AGENT</text>',
        f'<text x="56" y="236" font-size="62" font-weight="800" fill="#ffffff">AS A <tspan fill="#38bdf8">SERVICE</tspan></text>',
        f'<text x="56" y="278" font-size="20" fill="#a6b6cd">Deploying a support agent on Bedrock AgentCore</text>',
        f'<text x="56" y="318" font-size="17" fill="{DIM}" font-family="{MONO}">'
        "deploy 1 m 31 s   invoke 9 954 ms   955 tokens</text>",
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
    shell_box("S1-deploy", "terminal - agentcore deploy", DEPLOY,
              "captured from evidence/30-deploy.txt; step timings in evidence/31-deploy-log.txt")
    shell_box("S2-status", "terminal - agentcore status", STATUS,
              "captured from evidence/32-status.txt; long line re-wrapped to this width")
    shell_box("S3-invoke", "terminal - agentcore invoke", INVOKE,
              "captured from evidence/33-invoke.txt; the invoke log records 9 954 ms")
    shell_box("S4-traces-list", "terminal - agentcore traces list", TRACES_LIST,
              "captured from evidence/35-traces-list.txt, run three minutes after the invoke")
    shell_box("S5-trace-get", "terminal - agentcore traces get", TRACE_GET,
              "captured from evidence/36-trace-get.txt")
    shell_box("S6-trace-spans", "terminal - the spans in that trace", SPANS,
              "captured from evidence/37-trace-spans.txt; the file is evidence/39-trace-invoke.json")
    shell_box("S7-independence", "terminal - nothing else in the account", INDEPENDENCE,
              "captured from evidence/38-independence.txt; three rows, all UseCase=01")
    shell_box("S8-teardown", "terminal - remove all, then the reconciling deploy", TEARDOWN,
              "captured from evidence/40, 41 and 42; the stack delete is 9.6 s of a 1 m 40 s run")
    figure_architecture()
    figure_loop()
    figure_span_tree()
    cover()
    cover_medium()
    cover_devto()
    print("wrote", len(list(HERE.glob("*.svg"))), "svg files in", HERE)


if __name__ == "__main__":
    main()
