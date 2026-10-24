#!/usr/bin/env python3
"""Measure arrowhead-tip-to-border distance and box text padding, from pixels.

Box borders and arrowhead tips are parsed out of the generated SVG; every arrow
is then verified in the rendered PNG by scanning along its axis from the target
border into the arrow body and reporting where the head ink stops. Text padding
is the ink bounding box inside each box.

    python3 measure.py
"""
from __future__ import annotations

import pathlib
import re

from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent

FIGURES = [
    ("cover.png", "cover.svg"),
    ("cover-medium.png", "cover-medium.svg"),
    ("cover-devto.png", "cover-devto.svg"),
    ("F1-policy-architecture.png", "F1-policy-architecture.svg"),
]

COVER_BOXES = ["agent", "gateway", "backend"]
F1_BOXES = ["caller", "agent", "engine", "gateway", "lambda", "log"]

# (label, axis+scan direction, target) in SVG polygon draw order
ARROWS = {
    "cover": [
        ("agent->gateway tools/call", "h-", "gateway"),
        ("gateway->backend ALLOW", "h-", "backend"),
        ("DENY stub -> crossbar", "h-", "crossbar"),
    ],
    "F1-policy-architecture": [
        ("caller->agent invoke", "h-", "agent"),
        ("agent->gateway tools/call", "h-", "gateway"),
        ("gateway->engine authorize", "v+", "engine"),
        ("gateway->log every call", "v-", "log"),
        ("gateway->lambda ALLOW", "h-", "lambda"),
    ],
}


def parse_svg(path: pathlib.Path):
    src = path.read_text()
    m = re.search(r'viewBox="0 0 (\d+) (\d+)"', src)
    svg_w, svg_h = int(m.group(1)), int(m.group(2))
    rects = []
    for m in re.finditer(r'<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" '
                         r'height="([\d.]+)" rx="14"[^>]*stroke="(#[0-9a-f]{6})"', src):
        rects.append(dict(x=float(m.group(1)), y=float(m.group(2)),
                          w=float(m.group(3)), h=float(m.group(4)),
                          stroke=rgb(m.group(5))))
    polys = []
    for m in re.finditer(r'<polygon points="([^"]+)" fill="(#[0-9a-f]{6})"', src):
        pts = [tuple(map(float, p.split(","))) for p in m.group(1).split()]
        polys.append(dict(tip=pts[1], fill=m.group(2)))     # base-L, TIP, base-R
    bars = []
    for m in re.finditer(r'<line x1="([\d.]+)" y1="([\d.]+)" x2="([\d.]+)" y2="([\d.]+)" '
                         r'stroke="#fda4af" stroke-width="3.4"', src):
        x1, y1, x2, y2 = map(float, m.groups())
        bars.append(x1)
    return svg_w, svg_h, rects, polys, bars


def rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def near(p, c, tol=95):
    return all(abs(a - b) <= tol for a, b in zip(p, c))


def border_coord(box, raw_tip, axis):
    """The edge of `box` the arrow points at, in SVG units."""
    tx, ty = raw_tip
    cx, cy = box["x"] + box["w"] / 2, box["y"] + box["h"] / 2
    if axis == "h-":
        return box["x"] if tx < cx else box["x"] + box["w"]
    return box["y"] if ty < cy else box["y"] + box["h"]


def main() -> None:
    worst = 0
    print("== tip-to-border, measured in the rendered PNG ==")
    for png_name, svg_name in FIGURES:
        stem = svg_name[:-4]
        kind = "cover" if stem.startswith("cover") else stem
        names = F1_BOXES if kind.startswith("F1") else COVER_BOXES
        svg_w, svg_h, rects, polys, bars = parse_svg(HERE / svg_name)
        img = Image.open(HERE / png_name).convert("RGB")
        s = img.width / svg_w
        print(f"\n{png_name}  {img.width}x{img.height}  scale={s:g}")
        for (label, axis, target), poly in zip(ARROWS[kind], polys):
            tx, ty = poly["tip"]
            fill = rgb(poly["fill"])
            if target == "crossbar":
                border = min(bars, key=lambda x: abs(x - tx))
            else:
                border = border_coord(rects[names.index(target)], (tx, ty), axis)
            in_px = lambda v: round(v * s)
            bx, by = in_px(border), in_px(ty)
            qx, qy = in_px(tx), in_px(border)
            # local dark reference: just past the border, away from the head body
            if axis == "h-":
                dark = img.getpixel((bx + 6, by))
            elif axis == "v+":
                dark = img.getpixel((qx, qy - 6))
            else:
                dark = img.getpixel((qx, qy + 6))
            ink_vec = [c - d for c, d in zip(fill, dark)]
            need = 0.35 * max(ink_vec)

            def is_ink(p):
                return max(c - d for c, d in zip(p, dark)) >= need

            ink = None
            if axis == "h-":                       # body lies left of the border
                for q in range(bx, bx - 60, -1):
                    if is_ink(img.getpixel((q, by))):
                        ink = q
                        break
            elif axis == "v+":                     # body lies below the border
                for q in range(qy, qy + 60):
                    if is_ink(img.getpixel((qx, q))):
                        ink = q
                        break
            else:                                  # "v-": body above the border
                for q in range(qy, qy - 60, -1):
                    if is_ink(img.getpixel((qx, q))):
                        ink = q
                        break
            border_px = bx if axis == "h-" else qy
            gap = abs(border_px - ink) if ink is not None else 999
            worst = max(worst, gap)
            print(f"  {label:26s} tip=({tx:7.1f},{ty:7.1f}) svg  border={border:7.1f}  "
                  f"tip_gap={abs(in_px(tx) - bx) if axis == 'h-' else abs(in_px(ty) - qy)}px  "
                  f"ink_gap={gap}px  {'OK' if gap <= 1 else 'FAIL'}")

    print("\n== box text padding (PNG px) ==")
    for png_name, svg_name in FIGURES:
        stem = svg_name[:-4]
        names = F1_BOXES if stem.startswith("F1") else COVER_BOXES
        svg_w, svg_h, rects, polys, bars = parse_svg(HERE / svg_name)
        img = Image.open(HERE / png_name).convert("RGB")
        s = img.width / svg_w
        print(f"\n{png_name}  scale={s:g}")
        for name, b in zip(names, rects):
            x0, y0 = round(b["x"] * s), round(b["y"] * s)
            x1, y1 = round((b["x"] + b["w"]) * s), round((b["y"] + b["h"]) * s)
            # stay clear of the 2px border stroke and never count its own ink
            inset = round(4 * s) + 4
            lefts, rights = [], []
            for yy in range(y0 + inset, y1 - inset):
                row = [xx for xx in range(x0 + inset, x1 - inset)
                       if sum(img.getpixel((xx, yy))) > 320
                       and not near(img.getpixel((xx, yy)), b["stroke"], 70)]
                if row:
                    lefts.append(row[0])
                    rights.append(row[-1])
            if not lefts:
                print(f"  {name:8s} NO INK")
                continue
            lp, rp = min(lefts) - x0, x1 - max(rights)
            print(f"  {name:8s} pad L={lp:4d} R={rp:4d}  asym={abs(lp - rp):3d}px  "
                  f"{'OK' if abs(lp - rp) <= 4 else 'CHECK'}")

    print(f"\nworst ink gap across all arrows: {worst}px")


if __name__ == "__main__":
    main()
