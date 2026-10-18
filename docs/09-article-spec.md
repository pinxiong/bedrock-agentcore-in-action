# The article contract (English series, UC01 to UC07)

One contract for every article in this series. A writer agent follows it; a
verifier agent fails the article when any line below is violated. Published
articles: GitHub Pages is the canonical home, Dev.to and Medium are copies.

## 1. Scope and language

- English only. No Chinese edition, no deck. The English file is the single
  source of truth.
- One article per use case. Seven use cases, `uc01` to `uc07`.
- Length: **1000 to 1300 words**, measured on the body (front matter, code
  blocks and image captions excluded).
- Every article stands alone: a reader who has never seen another article in the
  series can follow it, deploy it, and tear it down.

## 2. Fixed section order

Headings are literal. No "Part 1" labels, no numbered prefixes, no extra
sections except `## Troubleshooting`, which may be omitted when nothing broke.

| # | Heading | What goes in it |
|---|---|---|
| 1 | `## The use case` | The business situation in two or three sentences. No technology yet: who is unhappy, and about what. |
| 2 | `## What AgentCore does here` | Which of the nine AgentCore capabilities this use case lights up, one line each. Name the capability, then what it does here. |
| 3 | `## Requirements` | Tool versions, IAM permissions, region. Bullets or a code block, never a table. |
| 4 | `## The code` | The GitHub URL of this use case's folder, then the folder tree as a code block, then one line per important file. |
| 5 | `## How it works` | The two to four pieces of core code, each with a real snippet and a paragraph on why it is written that way. |
| 6 | `## Deploy it` | The `agentcore` commands, in order, each followed by a figure of its captured output. Ends with the teardown command. |
| 7 | `## What it produced` | The result, with images. Terminal captures and one diagram. |
| 8 | `## Troubleshooting` | Only real failures hit during the run, each with the symptom and the fix. Omit the section if the run was clean. |
| 9 | `## Takeaways` | Three to five bullets. No preview of the next article, no roadmap. |

The nine capabilities are the core services: Runtime, Memory, Gateway, Identity,
Policy, Code Interpreter, Browser, Observability, Evaluations. If a use case
also uses Harness, Web Search, Optimization, Payments or Registry, list it under
the same section with one line saying it is outside the core nine.

## 3. Formatting rules

- **No markdown tables anywhere.** Medium cannot import them. Use bullets,
  `Field: value` lines, or a code block. This applies to the "at a glance"
  material too.
- **Every fenced block carries a language.** `bash` is the floor; prefer
  `bash`, `json`, `python`, `yaml`, `ts`, `text`. `plaintext` is banned.
  Anything the reader runs is a shell command, so it is `bash`; never leave a
  command block untagged and never tag one `plaintext`.
- **No bold in the body.** No `**...**`. Emphasis comes from structure.
- **Output over prose.** Commands, their real output, and images carry the
  article. A paragraph exists to explain what the reader just saw.
- Account ids in captured output are redacted to `123456789012`.
- Region is `us-east-1` for the whole series.
- **The repository branch is `master`, never `main`.** Every GitHub URL in an
  article says `/tree/master/` and `/blob/master/`. A `/tree/main/` link is a
  404 on this repository and is a blocking defect.

## 4. The real-run rule

Every number, output, trace and screenshot in an article comes from a run
performed while writing it. Specifically:

- Every command shown was executed, and the output shown is the captured output.
- Every timing, token count or cost figure is measured, never estimated.
- Every image is a capture of that run or a diagram generated from it.
- Every capability the use case claims is proven by the output of a native
  command, saved under `evidence/` before the article was written. There is no
  assertion script to hide behind: if the reader cannot reproduce the proof
  with `agentcore` or `aws`, the claim does not go in the article.

If a step cannot be run, it does not go in the article. That is a rule, not
advice: a fabricated figure is worse than a missing section.

## 5. Images

- Stored in `articles/images/<slug>/`, SVG source next to the PNG.
- Referenced by root path: `/images/<slug>/name.png`.
- Every article carries: one architecture diagram, one deploy capture, one
  result capture. More is fine, fewer is not.
- Every command's output is a capture figure. Section 9 is the rule.
- Alt text describes the content in one sentence, no "image of" prefix.

## 6. Front matter

```yaml
---
title: "<sentence case, matches the published title>"
description: "<270 characters or fewer; the keywords come first>"
date: YYYY-MM-DD
draft: false
tags: ["ai", "agents", "agentcore", "<one drawn from the article's content>"]
canonical_url: "https://xiongpin.dev/posts/<slug>/"
cover:
  image: "/images/<slug>/cover.png"
  alt: "<one sentence>"
---
```

The slug equals the title, lowercased and hyphenated.

### Tags (ruled on 2026-10-18, no per-article approval needed)

Every English article carries exactly four tags:

1. `ai` and `agents` are fixed. Every article in every series uses them.
2. `agentcore` is required for all seven articles of this series.
3. The fourth tag is drawn from the article's own content, for example
   `aws`, `security`, `observability`, `llm`, `mcp`, `serverless`.
4. Dev.to accepts four tags at most and rejects hyphens, so all four must be
   single words. `shared/scripts/publish_article.py` enforces this and reads the
   tags from the front matter; it never invents them.

The planned fourth tag per use case: uc01 `aws`, uc02 `llm`, uc03 `security`,
uc04 `security`, uc05 `aws`, uc06 `observability`, uc07 `mcp`.

## 7. Publication chain

1. The English master lives at `articles/<slug>.md` in this repository.
2. `shared/scripts/publish_article.py` copies it into the Hugo site, rewrites
   image paths to root paths, commits and pushes. GitHub Pages publishes it.
3. The same script creates or updates the Dev.to article through the API, with
   `canonical_url` pointing back at xiongpin.dev.
4. The same script writes a Medium import file. Medium has no write API and
   cannot import tables, which is why rule 3 in section 3 exists.

## 8. Native commands only (ruled on 2026-10-18)

The point of the series is to teach the reader AgentCore. Every step in an
article is therefore a command the reader can type with the AgentCore CLI or
the AWS CLI, and nothing else.

- The commands shown are `agentcore ...` and `aws ...`. A project script is
  never the thing the article tells the reader to run. No `make <target>`, no
  `python3 run.py <target>`, no wrapper of any kind.
- The use case folder ships **no self-written operational scripts**: no
  `run.py`, no `Makefile`, no `tests/doctor.py`, no `tests/smoke.py`, no
  `tests/copy_check.py`. What the reader needs is `agentcore.json`,
  `aws-targets.json`, the agent code, and the commands. A pytest unit test for
  the agent's own Python is fine and stays; nothing that runs a deployment or
  asserts a deployed capability does.
- Verifying a capability is done with native commands and their output:
  `agentcore status`, `agentcore invoke`, `agentcore traces list`,
  `agentcore traces get <id>` piped through `jq`, and
  `aws resourcegroupstaggingapi get-resources` for the independence check.
  Where an assertion used to live in `tests/smoke.py`, the article now shows
  the native command whose output proves it.
- Self-containedness is still asserted, but by reading the folder with native
  tooling: no import from another use case, no path leaving the folder, no
  cross-stack reference in the CDK output. The check is run by the repository
  tooling, not by a script inside the use case folder.
- `agentcore remove all -y` is the teardown command. It empties
  `agentcore.json` and `aws-targets.json`; say so, and tell the reader to
  restore both from git before deploying again.

## 9. Every command's output is an image, never a code block

- A command block is followed by its output as a **figure**, not by a fenced
  output block. Printing the same output twice, once as text and once as an
  image, is a blocking defect.
- Every command shown has a figure. If a command has no figure yet, render one.
- The figure's content is the captured output of that command on the run the
  article describes, redacted and wrapped, nothing invented. Rendering it as a
  terminal panel is fine; the bytes on screen must be the bytes the terminal
  printed.
- Figures are generated, so the SVG, the PNG and the generator must agree.
  Change one, change all three.

## 10. Process

- One writer agent per article. It builds or extends the use case, runs it,
  captures evidence, and writes the English master.
- One verifier agent per article, a different agent, which checks this contract
  and the evidence. It either passes the article or returns a numbered list of
  defects for the writer to fix.
- Only after the verifier passes does anything get published.

See `shared/templates/agent-prompts/writer-agent.md` and
`verifier-agent.md` for the two prompts.
