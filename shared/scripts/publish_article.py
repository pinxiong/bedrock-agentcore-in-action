#!/usr/bin/env python3
"""Publish one article in the AgentCore in Action series.

Chain: articles/<slug>.md (master)
       -> Hugo site content/posts/<slug>.md + static/images/<slug>/ -> push (canonical)
       -> Dev.to via API (canonical_url back to xiongpin.dev)
       -> Medium import file (Medium has no write API)

Usage:
    # 1. Hugo only
    publish_article.py --slug <slug>
    # 2. Hugo + Dev.to (tags must be pre-approved by the human)
    publish_article.py --slug <slug> --devto-create --tags aws,bedrock,agentcore,serverless
    publish_article.py --slug <slug> --devto-update --tags aws,bedrock,agentcore,serverless
    # 3. Medium export file
    publish_article.py --slug <slug> --medium-export

The Dev.to API key is read from $DEVTO_KEY or ~/.workbuddy/secrets/devto_api_key.
Tags are never invented here: they must be passed in, because tag choice is a
human decision in this project.
"""
import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

REPO = pathlib.Path("/Users/pinxiong/Documents/Important/bedrock-agentcore-in-action")
SITE = pathlib.Path("/Users/pinxiong/Documents/Important/pinxiong.github.io")
DIST = SITE / "writing-lab" / "distribution"
STATE = DIST / "publish-state.json"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
API = "https://dev.to/api"


def read_key():
    k = os.environ.get("DEVTO_KEY")
    if k:
        return k
    p = pathlib.Path.home() / ".workbuddy/secrets/devto_api_key"
    if p.exists():
        return p.read_text().strip()
    sys.exit("no Dev.to API key: set DEVTO_KEY or create ~/.workbuddy/secrets/devto_api_key")


def split_front_matter(text):
    if not text.startswith("---\n"):
        sys.exit("master has no front matter")
    _, fm, body = text.split("---\n", 2)
    return fm, body


def fm_get(fm, key):
    m = re.search(rf"^{key}:\s*(.+)$", fm, re.M)
    return m.group(1).strip().strip('"') if m else None


def check_master(slug):
    p = REPO / "articles" / f"{slug}.md"
    if not p.exists():
        sys.exit(f"master not found: {p}")
    text = p.read_text(encoding="utf-8")
    fm, body = split_front_matter(text)

    problems = []
    if re.search(r"^draft:\s*true", fm, re.M):
        problems.append("draft: true in front matter")
    bad_img = re.findall(r"!\[[^\]]*\]\((?!/images/)([^)]+)\)", body)
    if bad_img:
        problems.append(f"image paths not rooted: {bad_img[:3]}")
    if re.search(r"^\|", body, re.M):
        problems.append("markdown table present (Medium cannot import it)")
    plain = body.count("```plaintext")
    if plain:
        problems.append(f"{plain} plaintext code blocks")
    untagged = len(re.findall(r"^```\s*$", body, re.M))
    if untagged:
        problems.append(f"{untagged} code fences without a language tag")
    if re.search(r"[一-鿿]", body):
        problems.append("CJK characters in the English master")
    words = len(re.findall(r"\b[\w'-]+\b", re.sub(r"```.*?```", "", body, flags=re.S)))
    if not 1000 <= words <= 1300:
        problems.append(f"word count {words} outside 1000-1300")
    if problems:
        sys.exit("master failed pre-publish checks:\n  - " + "\n  - ".join(problems))
    return p, text, fm, body, words


def publish_hugo(slug, text):
    post = SITE / "content" / "posts" / f"{slug}.md"
    post.parent.mkdir(parents=True, exist_ok=True)
    post.write_text(text, encoding="utf-8")

    src_dir = REPO / "articles" / "images" / slug
    dst_dir = SITE / "static" / "images" / slug
    dst_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    for f in src_dir.iterdir():
        if f.suffix in {".png", ".jpg", ".svg"} and not f.name.startswith("."):
            shutil.copy2(f, dst_dir / f.name)
            copied.append(f.name)

    subprocess.run(["git", "add", str(post.relative_to(SITE)),
                    str(dst_dir.relative_to(SITE))], cwd=SITE, check=True)
    r = subprocess.run(["git", "commit", "-m", f"post: {slug}"], cwd=SITE,
                       capture_output=True, text=True)
    if r.returncode == 0:
        subprocess.run(["git", "push", "origin", "master"], cwd=SITE, check=True)
        print(f"hugo: committed and pushed ({len(copied)} images)")
    else:
        print("hugo: nothing to commit" if "nothing to commit" in r.stdout else r.stdout)
    return copied


def devto(slug, fm, body, tags, create):
    key = read_key()
    if len(tags) > 4 or any("-" in t for t in tags):
        sys.exit(f"bad tags {tags}: Dev.to allows 4 max and no hyphens")
    desc = fm_get(fm, "description") or ""
    if len(desc) > 140:
        desc = desc[:137].rsplit(" ", 1)[0] + "..."
    payload = {"article": {
        "title": fm_get(fm, "title"),
        "body_markdown": body.lstrip("\n"),
        "published": False,
        "description": desc,
        "tags": tags,
        "canonical_url": f"https://xiongpin.dev/posts/{slug}/",
        "main_image": "https://xiongpin.dev" + (fm_get(fm, "image") or f"/images/{slug}/cover.png"),
        "organization_id": 2794,  # AWS Community Builders
    }}

    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    art_id = state.get(slug, {}).get("devto_id")

    def call(method, url, data=None):
        req = urllib.request.Request(url, data=json.dumps(data).encode() if data else None,
                                     headers={"api-key": key, "Content-Type": "application/json",
                                              "Accept": "application/vnd.forem.api-v1+json",
                                              "User-Agent": UA}, method=method)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            sys.exit(f"Dev.to HTTP {e.code}: {e.read().decode()[:600]}")

    if create and not art_id:
        d = call("POST", f"{API}/articles", payload)
        art_id = d["id"]
        print(f"devto: created draft {art_id}")
    elif art_id:
        d = call("PUT", f"{API}/articles/{art_id}", payload)
        print(f"devto: updated {art_id}")
    else:
        sys.exit("no known Dev.to id; pass --devto-create")

    d = call("PUT", f"{API}/articles/{art_id}", {"article": {"published": True}})
    state.setdefault(slug, {})["devto_id"] = art_id
    state[slug]["devto_url"] = d.get("url")
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2))
    print(f"devto: published {d.get('url')} canonical={d.get('canonical_url')}")
    return d


def medium_export(slug, fm, body):
    DIST.mkdir(parents=True, exist_ok=True)
    out = DIST / f"{slug}-medium.md"
    out.write_text(body.lstrip("\n"), encoding="utf-8")
    checklist = DIST / f"{slug}-medium-checklist.md"
    checklist.write_text(f"""# Medium import checklist: {slug}

1. Open <https://medium.com/p/import>, paste `https://xiongpin.dev/posts/{slug}/`,
   click Import. It arrives as a draft, never published automatically.
2. Check the byline line: `Originally published at ... on {fm_get(fm, 'date')}.`
3. Title: {fm_get(fm, 'title')}
4. Subtitle / SEO description: {fm_get(fm, 'description')}
5. Feature image: upload `static/images/{slug}/cover-medium.png` (1400x788).
6. Verify: images in order, code blocks intact, no tables (there should be none).
7. Publish now, then confirm canonical points back at xiongpin.dev.
""", encoding="utf-8")
    print(f"medium: wrote {out.name} and {checklist.name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--tags", help="comma separated, max 4, no hyphens (human-approved)")
    ap.add_argument("--devto-create", action="store_true")
    ap.add_argument("--devto-update", action="store_true")
    ap.add_argument("--medium-export", action="store_true")
    ap.add_argument("--skip-hugo", action="store_true")
    a = ap.parse_args()

    p, text, fm, body, words = check_master(a.slug)
    print(f"master OK: {words} words")
    if not a.skip_hugo:
        publish_hugo(a.slug, text)
    if a.devto_create or a.devto_update:
        if a.tags:
            tags = [t.strip() for t in a.tags.split(",")]
        else:
            # Tag policy (docs/09-article-spec.md, ruled 2026-10-18): four tags,
            # ai + agents fixed, agentcore on this series, fourth from content.
            m = re.search(r"^tags:\s*\[(.+?)\]", fm, re.M)
            if not m:
                sys.exit("no tags in front matter and none passed on the command line")
            tags = [t.strip().strip('"').strip("'") for t in m.group(1).split(",")]
        devto(a.slug, fm, body, tags, a.devto_create)
    if a.medium_export:
        medium_export(a.slug, fm, body)


if __name__ == "__main__":
    main()
