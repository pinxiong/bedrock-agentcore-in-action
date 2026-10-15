#!/usr/bin/env python3
"""Generate the A0 intro deck (v2, 23 slides, 16:9).

Design v2 (2026-10-15) - answers "太素了":
- dark gradient title / act-divider / closing slides for rhythm and depth
- every content slide: kicker chip + big bold title + gradient accent underline
- left accent stripe on content slides
- rounded cards, gradient number badges, dark code panels with colored lines
- LIVE DEMO chips on terminal slides (video recording cues)
- figures reuse the article PNGs verbatim (white-bg, vivid) so all three
  deliverables (EN article / ZH article / deck) share one visual system.
"""
import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn

OUT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "decks"))
IMG = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "images", "aws-agentcore-under-the-hood"))

# ---- palette (matches the figures) ----
INK     = RGBColor(0x0F, 0x17, 0x2A)
SLATE   = RGBColor(0x47, 0x55, 0x69)
MUTED   = RGBColor(0x64, 0x74, 0x8B)
LINE    = RGBColor(0xCB, 0xD5, 0xE1)
WHITE   = RGBColor(0xFF, 0xFF, 0xFF)

BLUE    = RGBColor(0x25, 0x63, 0xEB); BLUE_D  = RGBColor(0x1D, 0x4E, 0xD8); BLUE_B  = RGBColor(0xDB, 0xEA, 0xFE)
PURPLE  = RGBColor(0x7C, 0x3A, 0xED); PURPLE_D = RGBColor(0x6D, 0x28, 0xD9); PURPLE_B = RGBColor(0xED, 0xE9, 0xFE)
ORANGE  = RGBColor(0xEA, 0x58, 0x0C); ORANGE_O = RGBColor(0xFF, 0x99, 0x00); ORANGE_B = RGBColor(0xFF, 0xED, 0xD5)
GREEN   = RGBColor(0x05, 0x96, 0x69); GREEN_D = RGBColor(0x04, 0x78, 0x57);  GREEN_B  = RGBColor(0xD1, 0xFA, 0xE5)
RED     = RGBColor(0xE1, 0x1D, 0x48); RED_D  = RGBColor(0xBE, 0x12, 0x3C);  RED_B    = RGBColor(0xFF, 0xE4, 0xE6)
TEAL    = RGBColor(0x0D, 0x94, 0x88); TEAL_D = RGBColor(0x0F, 0x76, 0x6E);  TEAL_B   = RGBColor(0xCC, 0xFB, 0xF1)
NAVY    = RGBColor(0x1E, 0x3A, 0x8A)
CODE_BG = RGBColor(0x0F, 0x17, 0x2A)
CODE_TX = RGBColor(0xE2, 0xE8, 0xF0)
CODE_GR = RGBColor(0x94, 0xA3, 0xB8)
CODE_GRN= RGBColor(0x34, 0xD3, 0x99)
CODE_BLU= RGBColor(0x93, 0xC5, 0xFD)
SLATE_B = RGBColor(0xF1, 0xF5, 0xF9)

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)
prs = Presentation()
prs.slide_width = SLIDE_W
prs.slide_height = SLIDE_H
BLANK = prs.slide_layouts[6]
n = 0

def set_grad(shape, c1, c2, angle=90):
    """2-stop linear gradient on a shape fill."""
    shape.fill.gradient()
    stops = shape.fill.gradient_stops
    stops[0].color.rgb = c1
    stops[0].position = 0.0
    stops[1].color.rgb = c2
    stops[1].position = 1.0
    try:
        shape.fill.gradient_angle = angle
    except Exception:
        pass
    shape.line.fill.background()

def rect(slide, x, y, w, h, color):
    s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.solid(); s.fill.fore_color.rgb = color; s.line.fill.background()
    s.shadow.inherit = False
    return s

def grad_rect(slide, x, y, w, h, c1, c2, angle=90, shape=MSO_SHAPE.RECTANGLE):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    set_grad(s, c1, c2, angle)
    s.shadow.inherit = False
    return s

def card(slide, x, y, w, h, fill=WHITE, edge=None, line_color=LINE, line_w=1.0, radius=0.08):
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    try:
        s.adjustments[0] = radius
    except Exception:
        pass
    s.fill.solid(); s.fill.fore_color.rgb = fill
    if line_color is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line_color; s.line.width = Pt(line_w)
    s.shadow.inherit = False
    if edge is not None:
        e = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(0.09), Inches(h))
        try:
            e.adjustments[0] = 0.5
        except Exception:
            pass
        e.fill.solid(); e.fill.fore_color.rgb = edge; e.line.fill.background()
        e.shadow.inherit = False
    return s

def txt(slide, x, y, w, h, text, size=18, color=INK, bold=False, align=PP_ALIGN.LEFT,
        font="Helvetica Neue", italic=False, anchor=MSO_ANCHOR.TOP, spacing=1.0):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    for i, line in enumerate(text.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.alignment = align
        p.font.size = Pt(size)
        p.font.bold = bold
        p.font.italic = italic
        p.font.color.rgb = color
        p.font.name = font
        p.line_spacing = spacing
    return box

def add_slide(dark=False):
    s = prs.slides.add_slide(BLANK)
    bg = s.background.fill
    bg.solid()
    bg.fore_color.rgb = CODE_BG if dark else WHITE
    return s

def dark_bg(slide, angle=115):
    """full-bleed navy gradient + two soft decorative shapes"""
    bg = slide.background.fill
    bg.gradient()
    stops = bg.gradient_stops
    stops[0].color.rgb = INK; stops[0].position = 0.0
    stops[1].color.rgb = NAVY; stops[1].position = 1.0
    try:
        bg.gradient_angle = angle
    except Exception:
        pass
    # decorative: thin gradient bar bottom-left
    grad_rect(slide, 0, 7.28, 13.333, 0.22, BLUE, PURPLE, angle=0)

def kicker_chip(slide, x, y, text, accent):
    w = 0.35 + 0.115 * len(text)
    c = card(slide, x, y, w, 0.34, fill=accent, line_color=None, radius=0.5)
    tf = c.text_frame
    tf.word_wrap = False
    p = tf.paragraphs[0]
    p.text = text.upper()
    p.alignment = PP_ALIGN.CENTER
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.name = "Helvetica Neue"
    p.font.color.rgb = WHITE
    return c

def title_block(slide, kicker, title, accent, sub=None):
    kicker_chip(slide, 0.6, 0.42, kicker, accent)
    txt(slide, 0.6, 0.86, 12.1, 0.85, title, size=30, color=INK, bold=True)
    grad_rect(slide, 0.62, 1.62, 1.5, 0.075, accent, _lighten(accent), angle=0)
    if sub:
        txt(slide, 0.6, 1.76, 12.1, 0.45, sub, size=14, color=SLATE)

def _lighten(c, f=0.45):
    return RGBColor(*[int(v + (255 - v) * f) for v in (c[0], c[1], c[2])]) if isinstance(c, tuple) else c

def accent_underline(slide, x, y, w, c1, c2):
    grad_rect(slide, x, y, w, 0.075, c1, c2, angle=0)

def footer(slide):
    global n
    rect(slide, 0.6, 7.06, 12.13, 0.012, LINE)
    txt(slide, 0.6, 7.12, 6, 0.3, "AgentCore in Action · Article 0", size=10, color=MUTED)
    txt(slide, 11.9, 7.12, 0.85, 0.3, f"{n:02d}", size=10, color=MUTED, align=PP_ALIGN.RIGHT)

def num_badge(slide, x, y, d, num, c1, c2):
    s = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d))
    set_grad(s, c1, c2, 90)
    s.shadow.inherit = False
    tf = s.text_frame
    p = tf.paragraphs[0]
    p.text = str(num)
    p.alignment = PP_ALIGN.CENTER
    p.font.size = Pt(int(d * 72 * 0.5))
    p.font.bold = True
    p.font.color.rgb = WHITE
    p.font.name = "Helvetica Neue"
    return s

def dark_code(slide, x, y, w, h, lines, size=14, radius=0.06):
    """dark code panel; lines = list of (text, color), vertically centered"""
    p = card(slide, x, y, w, h, fill=CODE_BG, line_color=None, radius=radius)
    tf = p.text_frame
    tf.word_wrap = False
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = Inches(0.25)
    tf.margin_top = Inches(0.18)
    for i, (line, col) in enumerate(lines):
        par = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        par.text = line
        par.alignment = PP_ALIGN.LEFT
        par.font.size = Pt(size)
        par.font.name = "Menlo"
        par.font.color.rgb = col
        par.line_spacing = 1.12
    return p

def live_chip(slide, x, y):
    c = card(slide, x, y, 1.55, 0.34, fill=GREEN, line_color=None, radius=0.5)
    tf = c.text_frame
    p = tf.paragraphs[0]
    p.text = "▶ LIVE DEMO"
    p.alignment = PP_ALIGN.CENTER
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = WHITE
    p.font.name = "Helvetica Neue"
    return c

def pic(slide, name, x, y, w=None, h=None):
    path = os.path.join(IMG, name)
    if w and h:
        return slide.shapes.add_picture(path, Inches(x), Inches(y), Inches(w), Inches(h))
    if w:
        return slide.shapes.add_picture(path, Inches(x), Inches(y), width=Inches(w))
    return slide.shapes.add_picture(path, Inches(x), Inches(y), height=Inches(h))

def act_divider(act_no, act_title, items, accent):
    global n
    n += 1
    s = add_slide()
    dark_bg(s)
    txt(s, 0.9, 2.35, 5.0, 1.0, f"ACT {act_no}", size=54, color=WHITE, bold=True, spacing=0.95)
    grad_rect(s, 0.95, 3.55, 1.3, 0.09, accent, _lighten(accent), angle=0)
    txt(s, 0.9, 3.85, 5.4, 0.9, act_title, size=32, color=WHITE, bold=True)
    # right: item list
    x0 = 6.6
    y0 = 1.7
    for i, (t, d) in enumerate(items):
        card(s, x0, y0 + i * 1.06, 5.8, 0.88, fill=RGBColor(0x1B, 0x2A, 0x4A), line_color=RGBColor(0x2A, 0x3E, 0x66), radius=0.14)
        txt(s, x0 + 0.3, y0 + i * 1.06 + 0.12, 5.2, 0.4, t, size=15, color=WHITE, bold=True)
        txt(s, x0 + 0.3, y0 + i * 1.06 + 0.48, 5.2, 0.35, d, size=11.5, color=CODE_BLU)

# =====================================================================
# S1 · Title
n += 1
s = add_slide(); dark_bg(s)
grad_rect(s, 0.9, 2.02, 1.7, 0.1, ORANGE_O, ORANGE, angle=0)
txt(s, 0.9, 2.3, 11.5, 2.0, "How AWS Bedrock AgentCore\nActually Works", size=44, color=WHITE, bold=True, spacing=1.02)
txt(s, 0.9, 4.35, 11.5, 0.6, "One JSON File In, Four CloudFormation Resources Out", size=21, color=CODE_BLU, bold=True)
txt(s, 0.9, 5.55, 11.5, 0.5, "AgentCore in Action · measured on a real deployment in us-east-1", size=14, color=CODE_GR)
txt(s, 0.9, 6.15, 11.5, 0.4, "xiongpin.dev", size=13, color=CODE_GR)

# =====================================================================
# S2 · Agenda
n += 1
s = add_slide()
title_block(s, "agenda", "One walkthrough, three acts", PURPLE)
acts = [
    ("ACT I · KNOW IT", "What AgentCore is, and the three layers you own", PURPLE, PURPLE_B,
     ["What it is / what it is not", "Three layers, one direction"]),
    ("ACT II · RUN IT", "Environment, then five hands-on steps with real output", ORANGE, ORANGE_B,
     ["Environment checklist", "Step 1-5: scaffold, contract, deploy, local, invoke"]),
    ("ACT III · SEE THROUGH IT", "The mechanisms behind the steps, and what broke", GREEN, GREEN_B,
     ["HTTP contract, trace anatomy", "Four failures, four takeaways"]),
]
for i, (t, d, c, cb, items) in enumerate(acts):
    x = 0.6 + i * 4.15
    card(s, x, 2.25, 3.85, 4.3, fill=WHITE, line_color=LINE, edge=c, radius=0.06)
    txt(s, x + 0.35, 2.6, 3.2, 0.45, t, size=15, color=c, bold=True)
    txt(s, x + 0.35, 3.1, 3.2, 0.8, d, size=13.5, color=SLATE, spacing=1.05)
    yy = 4.15
    for it in items:
        txt(s, x + 0.35, yy, 3.25, 0.6, "· " + it, size=13.5, color=INK, spacing=1.0)
        yy += 0.66
footer(s)

# =====================================================================
# S3 · Hook
n += 1
s = add_slide()
title_block(s, "hook", "The usual story ends with a Dockerfile and a prayer", BLUE)
# left card: usual
card(s, 0.6, 2.3, 5.85, 4.1, fill=SLATE_B, line_color=LINE, edge=MUTED, radius=0.06)
txt(s, 1.0, 2.65, 5.0, 0.5, "The usual story", size=17, color=SLATE, bold=True)
txt(s, 1.0, 3.0, 5.1, 3.2, "Write a Dockerfile\nPick an instance size\nHand-roll an IAM role\nHope the YAML is right", size=17, color=SLATE, spacing=1.5, anchor=MSO_ANCHOR.MIDDLE)
# right card: agentcore
card(s, 6.9, 2.3, 5.85, 4.1, fill=GREEN_B, line_color=GREEN, edge=GREEN, radius=0.06)
txt(s, 7.3, 2.65, 5.0, 0.5, "AgentCore", size=17, color=GREEN_D, bold=True)
txt(s, 7.3, 3.0, 5.1, 3.2, "One JSON file\nOne command\n\nA running, observable endpoint", size=17, color=INK, spacing=1.5, anchor=MSO_ANCHOR.MIDDLE)
txt(s, 0.6, 6.6, 12.13, 0.4, "Everything between them is this article.", size=13, color=MUTED, italic=True, align=PP_ALIGN.CENTER)
footer(s)

# =====================================================================
# ACT I
act_divider("I", "Know it", [
    ("What AgentCore is (and is not)", "a family of managed runtimes, 14 capabilities"),
    ("Three layers, one direction", "you write code + JSON; the CLI generates the rest"),
], PURPLE)

# S · F1
n += 1
s = add_slide()
title_block(s, "what it is", "A family of managed runtimes, not a new framework", GREEN,
            sub="Not a framework · not container orchestration · not a model router. Serverless microVM per session.")
pic(s, "F1-capability-map.png", 3.37, 2.3, w=6.6)
footer(s)

# S · F2
n += 1
s = add_slide()
title_block(s, "structure", "You write code and JSON. The CLI generates the rest.", PURPLE)
pic(s, "F2-three-layers.png", 3.22, 2.15, w=6.9)
footer(s)

# =====================================================================
# ACT II
act_divider("II", "Run it", [
    ("Environment checklist", "versions, permissions, one shadowing trap"),
    ("Step 1 · Scaffold", "agentcore create"),
    ("Step 2 · The contract", "two JSON files you own"),
    ("Step 3 · Deploy", "one command, six steps, four resources"),
    ("Step 4-5 · Run local, invoke cloud", "same routes, same contract"),
], ORANGE)

# S · environment
n += 1
s = add_slide()
title_block(s, "environment", "Before step 1: align the toolchain", TEAL)
# left: versions card
card(s, 0.6, 2.25, 6.1, 4.15, fill=WHITE, line_color=LINE, edge=TEAL, radius=0.05)
txt(s, 0.95, 2.5, 5.4, 0.4, "Versions (verified 2026-10-14)", size=15, color=TEAL, bold=True)
vers = [
    ("Node.js", "22.x (CLI needs 20+)"),
    ("AgentCore CLI", "0.31.1"),
    ("AWS CLI", "2.x"),
    ("uv", "0.11.9 (template agents)"),
    ("Git", "2.39 (create runs git init)"),
    ("Python", "3.11 local, CodeZip allows 3.10-3.14"),
    ("Region", "us-east-1 (whole series)"),
    ("Docker", "not needed - CodeZip builds"),
]
yy = 3.0
for k, v in vers:
    txt(s, 0.95, yy, 2.1, 0.4, k, size=13.5, color=INK, bold=True)
    txt(s, 3.1, yy, 3.5, 0.4, v, size=13.5, color=SLATE)
    yy += 0.42
# right: permissions card
card(s, 7.0, 2.25, 5.75, 4.15, fill=WHITE, line_color=LINE, edge=BLUE, radius=0.05)
txt(s, 7.35, 2.5, 5.0, 0.4, "Two identities, two permission sets", size=15, color=BLUE, bold=True)
txt(s, 7.35, 3.1, 5.1, 1.1, "You (deployer): create CFN stacks, upload to the bootstrap bucket, manage AgentCore resources.", size=14, color=SLATE, spacing=1.12)
txt(s, 7.35, 4.25, 5.1, 1.4, "The runtime (generated role): bedrock:InvokeModel* + logs:* + xray:PutTraceSegments. A least-privilege template for free.", size=14, color=SLATE, spacing=1.12)
card(s, 7.35, 5.7, 5.05, 0.55, fill=RED_B, line_color=RED, radius=0.3)
txt(s, 7.55, 5.78, 4.8, 0.4, "Trap: old Python CLI shadows npm one - pip uninstall it", size=11.5, color=RED_D, bold=True)
footer(s)

# S · step 1 (F3)
n += 1
s = add_slide()
title_block(s, "step 1 · scaffold", "agentcore create builds the skeleton", BLUE)
num_badge(s, 11.85, 0.55, 0.75, 1, BLUE, BLUE_D)
pic(s, "F3-directory-anatomy.png", 4.15, 2.05, w=5.6)
txt(s, 0.6, 2.05, 3.4, 4.25, "create writes three things:\nthe project root, the\nagentcore/ tree, and a\nstarter agent in\napp/<AgentName>/.\n\ncodeLocation points there.\nThat folder is what gets\nzipped, deployed and\ndev-started.", size=15, color=SLATE, spacing=1.2, anchor=MSO_ANCHOR.MIDDLE)
footer(s)

# S · step 2 contract
n += 1
s = add_slide()
title_block(s, "step 2 · the contract", "Two JSON files you own", PURPLE)
num_badge(s, 11.85, 0.55, 0.75, 2, PURPLE, PURPLE_D)
dark_code(s, 0.6, 2.2, 6.9, 4.1, [
    ("agentcore.json", CODE_GRN),
    ("{", CODE_TX),
    ('  "name": "aiauc01",', CODE_TX),
    ('  "managedBy": "CDK",', CODE_TX),
    ('  "runtimes": [{', CODE_TX),
    ('    "build": "CodeZip",', CODE_TX),
    ('    "entrypoint": "main.py",', CODE_TX),
    ('    "codeLocation": "app/aia_uc01/",', CODE_TX),
    ('    "runtimeVersion": "PYTHON_3_13",', CODE_TX),
    ('    "protocol": "HTTP",', CODE_TX),
    ('    "envVars": [{ "name": "MODEL_ID",', CODE_TX),
    ('      "value": "deepseek.v3.2" }]', CODE_TX),
    ("  }]", CODE_TX),
    ("}", CODE_TX),
    ("$ agentcore validate   # -> Valid", CODE_GRN),
], size=14)
card(s, 7.8, 2.2, 4.95, 1.75, fill=WHITE, line_color=LINE, edge=PURPLE, radius=0.08)
txt(s, 8.15, 2.4, 4.3, 0.4, "aws-targets.json", size=14, color=PURPLE, bold=True)
txt(s, 8.15, 2.85, 4.3, 0.9, '[{ "name": "default", "account": "...",\n  "region": "us-east-1" }]', size=12.5, color=SLATE, font="Menlo", spacing=1.1)
card(s, 7.8, 4.2, 4.95, 2.1, fill=ORANGE_B, line_color=ORANGE, radius=0.08)
txt(s, 8.15, 4.4, 4.35, 1.8, "create writes an empty array.\nThe first deploy calls STS\nand fills account + region in.\n\nNo --region flag exists.\nThe file is the only truth.", size=13.5, color=INK, spacing=1.12)
footer(s)

# S · step 3 pipeline (F4)
n += 1
s = add_slide()
title_block(s, "step 3 · deploy", "One command, six steps, four cloud resources", ORANGE)
num_badge(s, 11.85, 0.55, 0.75, 3, ORANGE, ORANGE)
pic(s, "F4-deploy-pipeline.png", 3.12, 2.1, w=7.1)
footer(s)

# S · deploy output + live demo
n += 1
s = add_slide()
title_block(s, "step 3 · deploy", "What success looks like (cold account)", ORANGE)
live_chip(s, 10.9, 1.62)
dark_code(s, 0.6, 2.2, 12.15, 4.15, [
    ("$ agentcore deploy -y --target default", CODE_GRN),
    ("✓ Load deployment target", CODE_TX),
    ("✓ Validate project", CODE_TX),
    ("✓ Sync CDK dependencies", CODE_TX),
    ("✓ Build CDK project", CODE_TX),
    ("✓ Synthesize CloudFormation", CODE_TX),
    ("✓ Deploy to AWS", CODE_TX),
    ("✓ Deployed to 'default' (stack: AgentCore-aiauc01-default)", CODE_TX),
    ("  Runtime ARN: arn:aws:bedrock-agentcore:us-east-1:123456789012:", CODE_BLU),
    ("               runtime/aiauc01_aia_uc01-LH8zQV86C2", CODE_BLU),
    ("", CODE_TX),
    ("# cold: 9 min 49 s   ·   code-only redeploy: 26 s", CODE_GR),
], size=16)
footer(s)

# S · CDK is a compiler
n += 1
s = add_slide()
title_block(s, "schema-first", "cdk/ is a compiler. agentcore.json is the program.", PURPLE)
dark_code(s, 0.6, 2.2, 7.7, 3.0, [
    ("// agentcore/cdk/bin/cdk.ts (generated)", CODE_GR),
    ("const configRoot = path.resolve(process.cwd(), '..');", CODE_TX),
    ("const configIO = new ConfigIO({ baseDir: configRoot });", CODE_TX),
    ("", CODE_TX),
    ("const spec    = await configIO.readProjectSpec();", CODE_TX),
    ("const targets = await configIO.readAWSDeploymentTargets();", CODE_TX),
], size=14)
txt(s, 0.6, 5.5, 7.7, 0.8, "Zero hard-coded names in the generated project (grepped).\nStack name = AgentCore-<projectName>-<targetName>, both from the JSON.", size=14, color=SLATE, spacing=1.15)
card(s, 8.7, 2.2, 4.05, 4.1, fill=PURPLE_B, line_color=PURPLE, edge=PURPLE, radius=0.07)
txt(s, 9.05, 2.2, 3.4, 4.1, "Same TypeScript,\ndifferent JSON\n→ different stack.\n\nChange the schema,\nnot the plumbing.\n\nThat is what\nschema-first means\nin practice.", size=15, color=INK, spacing=1.2, anchor=MSO_ANCHOR.MIDDLE)
footer(s)

# S · step 4 local
n += 1
s = add_slide()
title_block(s, "step 4 · run it locally", "Same app, same routes, no deployment", TEAL)
num_badge(s, 11.85, 0.55, 0.75, 4, TEAL, TEAL_D)
live_chip(s, 9.15, 1.62)
dark_code(s, 0.6, 2.2, 6.6, 2.4, [
    ("$ agentcore dev -l", CODE_GRN),
    ("Server: http://localhost:8080/invocations", CODE_TX),
    ("(GET /ping + POST /invocations - same two routes)", CODE_GR),
], size=14)
dark_code(s, 0.6, 4.85, 6.6, 1.5, [
    ("$ curl -s -X POST localhost:8080/invocations \\", CODE_GRN),
    ('   -d \'{"prompt":"What is 128 plus 256?"}\'', CODE_TX),
    ("→ SSE stream, toolUse add_numbers, answer 384", CODE_BLU),
], size=13)
txt(s, 7.6, 2.2, 5.1, 4.15, "Uvicorn + hot reload.\nModel calls still go to Bedrock:\ncredentials needed, deployment not.\n\nFlags worth knowing:\n-p port, -b TUI, --skip-deploy.\n\nEdit main.py while it runs:\nthe reloader picks it up\nwithout a restart.", size=15, color=SLATE, spacing=1.2, anchor=MSO_ANCHOR.MIDDLE)
footer(s)

# S · step 5 cloud invoke (F5)
n += 1
s = add_slide()
title_block(s, "step 5 · invoke", "The deployed runtime answers through the data plane", GREEN)
num_badge(s, 11.85, 0.55, 0.75, 5, GREEN, GREEN_D)
live_chip(s, 9.15, 1.62)
pic(s, "F5-one-surface.png", 3.72, 2.05, w=5.9)
txt(s, 0.6, 6.5, 12.1, 0.45, "agentcore invoke = a CLI client for the hosted /invocations endpoint, not a third interface.", size=13, color=MUTED, align=PP_ALIGN.CENTER)
footer(s)

# S · cost
n += 1
s = add_slide()
title_block(s, "cost", "One invoke costs about $0.0009", GREEN)
cards = [
    ("$0.0007", "model tokens", "846 in + 82 out\ndeepseek.v3.2 @$0.62/$1.85 per M", BLUE, BLUE_B),
    ("$0.0002", "runtime compute", "≈ 7 s active compute\nidle sessions are free", TEAL, TEAL_B),
    ("9m49s / 26s", "first deploy / redeploy", "cold = npm install dominates\nwarm = asset hash only", ORANGE, ORANGE_B),
]
for i, (big, label, d, c, cb) in enumerate(cards):
    x = 0.6 + i * 4.15
    card(s, x, 2.3, 3.85, 3.5, fill=WHITE, line_color=LINE, edge=c, radius=0.07)
    txt(s, x + 0.3, 2.7, 3.25, 0.9, big, size=30, color=c, bold=True)
    txt(s, x + 0.3, 3.7, 3.25, 0.4, label, size=14, color=INK, bold=True)
    txt(s, x + 0.3, 4.2, 3.25, 1.3, d, size=13, color=SLATE, spacing=1.15)
txt(s, 0.6, 6.15, 12.1, 0.5, "The infrastructure bill rounds to zero. The engineering cost is reading the trace.", size=15, color=INK, bold=True, align=PP_ALIGN.CENTER)
footer(s)

# =====================================================================
# ACT III
act_divider("III", "See through it", [
    ("The HTTP contract", "two requests, an async generator"),
    ("The trace", "what observability records, and when"),
    ("Four failures", "and what each one taught"),
    ("Takeaways", "four sentences to keep"),
], GREEN)

# S · HTTP contract
n += 1
s = add_slide()
title_block(s, "under the hood i", "Two requests. That is the whole platform contract.", BLUE)
dark_code(s, 0.6, 2.2, 7.5, 4.1, [
    ("@app.entrypoint", CODE_TX),
    ("async def invoke(payload, context):", CODE_TX),
    ("    session_id = getattr(", CODE_TX),
    ("        context, \"session_id\", \"default-session\")", CODE_TX),
    ("    agent = get_or_create_agent(session_id)", CODE_TX),
    ("    async for event in agent.stream_async(prompt):", CODE_TX),
    ("        yield event", CODE_TX),
], size=15)
card(s, 8.5, 2.2, 4.25, 4.1, fill=BLUE_B, line_color=BLUE, edge=BLUE, radius=0.07)
txt(s, 8.85, 2.2, 3.6, 4.1, "GET  /ping\nPOST /invocations\n\nyield → one SSE event\n\nsession_id = your\nstate key. The platform\nhandles the microVMs.\n\nMODEL_ID = an env var\nfrom agentcore.json.", size=14.5, color=INK, spacing=1.18, anchor=MSO_ANCHOR.MIDDLE)
footer(s)

# S · trace (F6)
n += 1
s = add_slide()
title_block(s, "under the hood ii", "The trace teaches the agent loop without reading source", GREEN)
pic(s, "F6-span-tree.png", 3.47, 1.95, w=6.4)
txt(s, 0.6, 6.5, 12.1, 0.5, "Caveats: spans need ~10 min to query · local dev records no tool span - assert against the deployment.", size=13.5, color=RED_D, bold=True, align=PP_ALIGN.CENTER)
footer(s)

# S · four failures
n += 1
s = add_slide()
title_block(s, "what broke", "Four failures worth passing on", RED)
fails = [
    ("Stale cdk.out fails the next deploy", "CLI deletes it before synth; leftover state kills synth. rm -rf agentcore/cdk/cdk.out fixes it.", RED),
    ("Renaming is destroying", "name → CloudFormation logical ID. Rename = delete old runtime + create new.", ORANGE),
    ("Models leak scaffolding into text", "DSML markers, <thinking> blocks. Verified with Strands removed. Stream-safe filter at the entrypoint.", PURPLE),
    ("Region is not a flag", "--region → unknown option. The targets file decides; it fills itself in on first deploy.", BLUE),
]
pos = [(0.6, 2.2), (6.75, 2.2), (0.6, 4.5), (6.75, 4.5)]
for (t, d, c), (x, y) in zip(fails, pos):
    card(s, x, y, 5.95, 2.05, fill=WHITE, line_color=LINE, edge=c, radius=0.07)
    txt(s, x + 0.35, y + 0.2, 5.3, 0.55, t, size=16.5, color=INK, bold=True)
    txt(s, x + 0.35, y + 0.85, 5.35, 1.1, d, size=13.5, color=SLATE, spacing=1.12)
footer(s)

# S · takeaways
n += 1
s = add_slide()
title_block(s, "summary", "Four takeaways", PURPLE)
items = [
    ("The JSON file is the interface", "everything else is regenerable plumbing driven by it", PURPLE),
    ("CDK appears as a vendored compiler", "you never write constructs; same code, different JSON, different stack", BLUE),
    ("Local and deployed share one HTTP contract", "code that passed locally deploys without a shim", TEAL),
    ("Observability is real but asynchronous", "the tool call gets its own span; give tests minutes, not seconds", GREEN),
]
y = 2.15
for i, (t, d, c) in enumerate(items, 1):
    num_badge(s, 0.75, y, 0.62, i, c, c)
    txt(s, 1.65, y - 0.02, 11.0, 0.45, t, size=19, color=INK, bold=True)
    txt(s, 1.65, y + 0.44, 11.0, 0.4, d, size=13, color=SLATE)
    y += 1.02
card(s, 1.65, 6.25, 10.6, 0.65, fill=PURPLE_B, line_color=None, radius=0.12)
txt(s, 1.65, 6.25, 10.6, 0.65, "Your infrastructure is not code you maintain. It is code that compiles.", size=16, color=PURPLE_D, bold=True, italic=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
footer(s)

# S · closing
n += 1
s = add_slide(); dark_bg(s)
txt(s, 0.9, 2.35, 11.5, 1.8, "Your infrastructure is not code\nyou maintain. It is code that compiles.", size=34, color=WHITE, bold=True, spacing=1.05)
grad_rect(s, 0.95, 4.55, 1.7, 0.09, ORANGE_O, ORANGE, angle=0)
txt(s, 0.9, 4.95, 11.5, 0.5, "AgentCore in Action · Article 0 · xiongpin.dev", size=17, color=CODE_BLU, bold=True)

# ---- save ----
out_path = os.path.abspath(os.path.join(OUT, "aws-agentcore-under-the-hood.pptx"))
prs.save(out_path)
print(f"saved: {out_path}  ({n} slides)")
