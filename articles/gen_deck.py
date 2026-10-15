#!/usr/bin/env python3
"""Generate the A0 intro deck (17 slides, 16:9) from the article structure."""
import os
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

OUT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "decks"))
IMG = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "images", "aws-agentcore-under-the-hood"))

# palette (matches figures)
TEXT    = RGBColor(0x1A, 0x1A, 0x2E)
TEXT_LT = RGBColor(0x55, 0x55, 0x55)
BLUE    = RGBColor(0x2E, 0x86, 0xDE)
PURPLE  = RGBColor(0x8E, 0x44, 0xAD)
GRAY    = RGBColor(0x7F, 0x8C, 0x8D)
ORANGE  = RGBColor(0xE6, 0x7E, 0x22)
GREEN   = RGBColor(0x27, 0xAE, 0x60)
RED     = RGBColor(0xE7, 0x4C, 0x3C)
WHITE   = RGBColor(0xFF, 0xFF, 0xFF)
BG      = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT   = RGBColor(0xF4, 0xF6, 0xF7)

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

prs = Presentation()
prs.slide_width = SLIDE_W
prs.slide_height = SLIDE_H
BLANK = prs.slide_layouts[6]

def add_slide():
    s = prs.slides.add_slide(BLANK)
    bg = s.background.fill
    bg.solid()
    bg.fore_color.rgb = BG
    return s

def txt(slide, x, y, w, h, text, size=18, color=TEXT, bold=False, align=PP_ALIGN.LEFT, font="Helvetica Neue", italic=False, anchor=MSO_ANCHOR.TOP, line_spacing=1.0):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    lines = text.split("\n")
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.alignment = align
        p.font.size = Pt(size)
        p.font.bold = bold
        p.font.italic = italic
        p.font.color.rgb = color
        p.font.name = font
        if line_spacing != 1.0:
            p.line_spacing = line_spacing
    return box

def title_bar(slide, text, color=TEXT, kicker=None, kicker_color=None):
    if kicker:
        txt(slide, 0.6, 0.35, 12.1, 0.4, kicker.upper(), size=13, color=kicker_color or GRAY, bold=True)
    txt(slide, 0.6, 0.75, 12.1, 1.0, text, size=30, color=color, bold=True)

def footer(slide, n):
    txt(slide, 12.35, 7.05, 0.6, 0.35, f"{n:02d}", size=11, color=GRAY, align=PP_ALIGN.RIGHT)

def code_box(slide, x, y, w, h, code, size=15, lang_color=BLUE):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = False
    lines = code.strip("\n").split("\n")
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.font.size = Pt(size)
        p.font.name = "Menlo"
        p.font.color.rgb = TEXT
        p.line_spacing = 1.05
    # background
    box.fill.solid()
    box.fill.fore_color.rgb = LIGHT
    return box

def pic(slide, name, x, y, w=None, h=None):
    path = os.path.join(IMG, name)
    if w and h:
        return slide.shapes.add_picture(path, Inches(x), Inches(y), Inches(w), Inches(h))
    if w:
        return slide.shapes.add_picture(path, Inches(x), Inches(y), width=Inches(w))
    return slide.shapes.add_picture(path, Inches(x), Inches(y), height=Inches(h))

n = 0

# ---- S1: title ----
n += 1
s = add_slide()
txt(s, 0.9, 2.1, 11.5, 1.6, "How AWS Bedrock AgentCore\nActually Works", size=40, color=TEXT, bold=True)
txt(s, 0.9, 3.9, 11.5, 0.6, "One JSON File In, Four CloudFormation Resources Out", size=20, color=BLUE, bold=True)
txt(s, 0.9, 5.6, 11.5, 0.5, "AgentCore Series · Article 0 of 8 · measured on a real deployment in us-east-1", size=14, color=TEXT_LT)
txt(s, 0.9, 6.3, 11.5, 0.4, "xiongpin.dev", size=13, color=GRAY)

# ---- S2: hook ----
n += 1
s = add_slide()
title_bar(s, "The usual story ends with a Dockerfile and a prayer", kicker="hook")
txt(s, 0.9, 2.2, 11.5, 1.4, "Dockerfile → instance size → hand-rolled IAM role → hope the YAML is right", size=22, color=TEXT_LT)
txt(s, 0.9, 3.8, 11.5, 1.2, "AgentCore: the whole deployment contract\nis one JSON file.", size=30, color=TEXT, bold=True)
txt(s, 0.9, 5.6, 11.5, 0.8, "One command turns it into a running, observable endpoint.", size=20, color=GREEN, bold=True)
footer(s, n)

# ---- S3: what it is / is not (F1) ----
n += 1
s = add_slide()
title_bar(s, "A family of managed runtimes, not a new framework", kicker="what it is / is not", kicker_color=BLUE)
pic(s, "F1-capability-map.png", 3.35, 1.85, w=6.6)
txt(s, 0.9, 7.02, 11.5, 0.42, "Not a framework · not container orchestration · not a model router. Serverless microVM per session.", size=14, color=TEXT_LT, align=PP_ALIGN.CENTER)
footer(s, n)

# ---- S4: three layers (F2) ----
n += 1
s = add_slide()
title_bar(s, "You write code and JSON. The CLI generates the rest.", kicker="mental model", kicker_color=PURPLE)
pic(s, "F2-three-layers.png", 3.1, 1.85, w=7.1)
footer(s, n)

# ---- S5: directory anatomy (F3) ----
n += 1
s = add_slide()
title_bar(s, "Two colours: what you write vs what is generated", kicker="project anatomy", kicker_color=BLUE)
pic(s, "F3-directory-anatomy.png", 3.4, 1.8, w=6.5)
footer(s, n)

# ---- S6: project root rule ----
n += 1
s = add_slide()
title_bar(s, "A project = directory + agentcore.json, both required", kicker="project detection", kicker_color=RED)
code_box(s, 1.6, 2.1, 10.1, 1.6, """
walk up from cwd until a folder contains BOTH:
    agentcore/                and    agentcore/agentcore.json
either alone is not a project
""", size=17)
txt(s, 1.6, 4.3, 10.1, 0.9, '"No agentcore project found" does not tell you which one is missing.', size=19, color=TEXT_LT, italic=False)
txt(s, 1.6, 5.4, 10.1, 0.9, 'Run from the directory that contains agentcore/, or the CLI refuses.', size=19, color=RED, bold=True)
footer(s, n)

# ---- S7: the contract ----
n += 1
s = add_slide()
title_bar(s, "The contract: two JSON files you own", kicker="the contract", kicker_color=PURPLE)
code_box(s, 0.7, 2.0, 6.4, 4.3, """
agentcore.json
{
  "name": "aiauc01",
  "managedBy": "CDK",
  "runtimes": [{
    "build": "CodeZip",
    "entrypoint": "main.py",
    "runtimeVersion": "PYTHON_3_13",
    "envVars": [{
      "name": "MODEL_ID",
      "value": "deepseek.v3.2"
    }]
  }]
}
""", size=15)
code_box(s, 7.4, 2.0, 5.2, 1.6, """
aws-targets.json
[{ "name": "default",
   "account": "...",
   "region": "us-east-1" }]
""", size=15)
txt(s, 7.4, 4.0, 5.2, 2.4, "create writes an empty array.\nThe first deploy calls STS\nand fills account + region in.\n\nNo --region flag exists.\nThe file is the only truth.", size=17, color=TEXT_LT)
footer(s, n)

# ---- S8: pipeline (F4) ----
n += 1
s = add_slide()
title_bar(s, "Deploy: six steps, four cloud resources", kicker="what deploy does", kicker_color=ORANGE)
pic(s, "F4-deploy-pipeline.png", 2.6, 2.0, w=8.1)
footer(s, n)

# ---- S9: CDK is a compiler ----
n += 1
s = add_slide()
title_bar(s, "cdk/ is a compiler. agentcore.json is the program.", kicker="schema-first", kicker_color=PURPLE)
code_box(s, 0.7, 2.0, 7.6, 3.6, """
// agentcore/cdk/bin/cdk.ts (generated)
const configRoot = path.resolve(process.cwd(), '..');
const configIO = new ConfigIO({ baseDir: configRoot });

const spec    = await configIO.readProjectSpec();
const targets = await configIO.readAWSDeploymentTargets();
""", size=16)
txt(s, 0.7, 5.9, 7.6, 0.8, "Zero hard-coded names in the generated project (grepped).", size=17, color=TEXT_LT)
txt(s, 8.6, 2.0, 4.1, 4.4, "Stack name comes\nfrom the JSON too:\n\nAgentCore-\n  <project>-\n  <target>\n\nSame TS, different\nJSON → different\nstack.", size=17, color=TEXT, font=None)
footer(s, n)

# ---- S10: local dev ----
n += 1
s = add_slide()
title_bar(s, "Local: same app, same routes, no deployment", kicker="running it", kicker_color=GRAY)
code_box(s, 0.7, 2.0, 5.9, 2.2, """
$ agentcore dev
Server: http://localhost:8080/invocations
(ping / invocations — same two routes)
""", size=15)
txt(s, 0.7, 4.6, 5.9, 1.8, "Uvicorn + hot reload.\nModel calls still go to Bedrock:\ncredentials needed, deployment not.", size=17, color=TEXT_LT)
txt(s, 7.0, 2.6, 5.6, 2.6, "Same prompt, same code,\nsame contract —\n\ndeployed runtime answers\nthrough the data plane.", size=19, color=TEXT)
footer(s, n)

# ---- S11: SSE stream ----
n += 1
s = add_slide()
title_bar(s, "The tool call is visible in the raw stream", kicker="data plane", kicker_color=BLUE)
code_box(s, 0.7, 2.0, 11.9, 2.9, """
contentBlockStart:  toolUse  name=add_numbers  input={"a": 17, "b": 25}
messageStop:        stopReason=tool_use      # the loop stops to run the tool
contentBlockDelta:  "17 plus 25 equals 42."  # the second message
""", size=16)
txt(s, 0.7, 5.4, 11.9, 1.0, "Native Bedrock toolUse protocol blocks — no new tool protocol to learn.", size=19, color=TEXT, bold=True)
footer(s, n)

# ---- S12: cost ----
n += 1
s = add_slide()
title_bar(s, "One invoke costs about $0.0009", kicker="cost", kicker_color=GREEN)
txt(s, 0.9, 2.4, 5.6, 2.8, "deepseek.v3.2 (us-east-1)\n$0.62 / M input tokens\n$1.85 / M output tokens", size=19, color=TEXT_LT)
txt(s, 0.9, 4.4, 5.6, 1.6, "846 in + 82 out\n≈ $0.0007 model + $0.0002 compute", size=19, color=TEXT, bold=True)
txt(s, 7.0, 2.4, 5.6, 3.6, "First deploy: 9 min 49 s\nRedeploy: 26 s\n\nThe infra bill rounds to zero.\nThe engineering cost is\nreading the trace.", size=19, color=TEXT)
footer(s, n)

# ---- S13: HTTP contract ----
n += 1
s = add_slide()
title_bar(s, "Two requests. That is the whole platform contract.", kicker="entrypoint", kicker_color=BLUE)
code_box(s, 0.7, 2.0, 7.4, 4.4, """
@app.entrypoint
async def invoke(payload, context):
    session_id = getattr(
        context, "session_id", "default-session")
    agent = get_or_create_agent(session_id)
    async for event in agent.stream_async(prompt):
        yield event
""", size=17)
txt(s, 8.5, 2.0, 4.2, 4.6, "GET  /ping\nPOST /invocations\n\nyield → one SSE event\n\nsession_id = your\nstate key. Platform\nhandles the microVMs.", size=17, color=TEXT)
footer(s, n)

# ---- S14: trace (F6) ----
n += 1
s = add_slide()
title_bar(s, "The trace teaches the agent loop without reading source", kicker="observability", kicker_color=GREEN)
pic(s, "F6-span-tree.png", 2.8, 1.9, w=7.7)
footer(s, n)

# ---- S15: four failures ----
n += 1
s = add_slide()
title_bar(s, "Four failures worth passing on", kicker="what broke", kicker_color=RED)
items = [
    ("Stale cdk.out fails the next deploy", "rm -rf agentcore/cdk/cdk.out fixes it"),
    ("Renaming is destroying", "name → CloudFormation logical ID"),
    ("Models leak scaffolding into text", "verified with Strands removed; filter at entrypoint"),
    ("Region is not a flag", "the targets file decides; it fills itself in"),
]
y = 2.1
for t, d in items:
    txt(s, 0.9, y, 5.9, 0.8, t, size=19, color=TEXT, bold=True)
    txt(s, 0.9, y+0.55, 5.9, 0.7, d, size=15, color=TEXT_LT)
    y += 1.22
footer(s, n)

# ---- S16: takeaways ----
n += 1
s = add_slide()
title_bar(s, "Four takeaways", kicker="summary", kicker_color=PURPLE)
items = [
    "The JSON file is the interface.",
    "CDK appears as a vendored compiler.",
    "Local and deployed share one HTTP contract.",
    "Observability is real but asynchronous.",
]
y = 2.1
for i, t in enumerate(items, 1):
    txt(s, 0.9, y, 0.7, 0.8, f"{i}", size=24, color=PURPLE, bold=True)
    txt(s, 1.7, y+0.06, 10.8, 0.8, t, size=21, color=TEXT)
    y += 0.95
txt(s, 1.7, 6.1, 10.8, 0.9, "Your infrastructure is not code you maintain. It is code that compiles.", size=20, color=BLUE, bold=True, italic=True)
footer(s, n)

# ---- S17: roadmap (F7) ----
n += 1
s = add_slide()
title_bar(s, "Next: 7 use cases, rising difficulty, one pattern", kicker="series", kicker_color=ORANGE)
pic(s, "F7-series-roadmap.png", 2.7, 1.95, w=7.9)
footer(s, n)

# ---- save ----
out_path = os.path.abspath(os.path.join(OUT, "aws-agentcore-under-the-hood.pptx"))
prs.save(out_path)
print(f"saved: {out_path}  ({n} slides)")
