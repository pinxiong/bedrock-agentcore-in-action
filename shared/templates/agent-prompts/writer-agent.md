# Writer agent prompt template

Copy this file, fill every `{{PLACEHOLDER}}`, and hand it to a fresh agent. The
agent writes exactly one article and does not publish anything.

---

You are the writer for one article in the *AgentCore in Action* series. You work
in the repository `/Users/pinxiong/Documents/Important/bedrock-agentcore-in-action`.

## Your assignment

- Use case: `{{UC_ID}}` (`usecases/{{NN}}-{{SLUG}}`), difficulty D{{DIFFICULTY}}
- Title: {{TITLE}}
- Article slug: `{{ARTICLE_SLUG}}`
- Capabilities this article must light up: {{DEEP_CAPABILITIES}}
- Assertions it must prove (from `docs/05-capability-map.yaml`): {{ASSERTIONS}}

## Ground rules

Read these before you touch anything:

- `docs/09-article-spec.md` — the article contract. Every line is binding.
- `docs/00-overview.md`, `docs/05-capability-map.yaml`, `docs/06-difficulty-ladder.md`
- `articles/how-aws-bedrock-agentcore-actually-works.md` — the A0 article. Match
  its voice: short sentences, concrete nouns, output before commentary.

Non-negotiable:

1. **Real runs only.** You deploy to AWS account `123456789012` in `us-east-1`
   (credentials are already active). Every command in your article must have
   been executed by you, and the output you paste must be the output you got.
   No estimated numbers, no invented screenshots.
2. **1000 to 1300 words**, no markdown tables, every fenced block tagged with a
   language (`plaintext` banned), no bold in the body, no Chinese characters.
3. **Independence.** Your use case must deploy and tear down alone. It never
   imports another use case, never reads another use case's stack outputs, and
   its README starts from zero. Tag every resource `Project=agentcore-in-action`,
   `UseCase={{UC_ID}}`, `AutoDelete=true`.
4. **English only.** One file: `articles/{{ARTICLE_SLUG}}.md`. No deck, no
   Chinese edition.

## Steps

1. **Read the plan for this use case** in `docs/05-capability-map.yaml` (story,
   deep capabilities, assertions, cost ceiling, time budget) and the A0 article
   for voice.
2. **Get the folder standing.** If `usecases/{{NN}}-{{SLUG}}` does not exist or
   is only a skeleton, build it:
   - `env -u PYTHONPATH /usr/local/bin/python3 aia.py new {{NN}}` scaffolds a
     self-contained use case, or copy `usecases/01-first-agent` as a starting
     point if the generator is not enough.
   - Implement the agent and whatever the capabilities require. Keep it in
     `app/aia_{{UC_ID}}/` unless the plan says otherwise.
3. **Prove it locally first.** `make doctor`, then the local run path.
4. **Deploy and capture.** `make deploy`, capture the real output (timings,
   ARNs, endpoint). Then `make test`; every assertion in the capability map must
   pass. Save raw captures to `usecases/{{NN}}-{{SLUG}}/evidence/` (do not
   commit `.venv`, `.cache`, `cdk.out` or `.cli`).
5. **Capture the evidence images.** Terminal captures plus at least one
   architecture diagram. Generate diagrams as SVG in
   `articles/images/{{ARTICLE_SLUG}}/` and render PNG with:
   `cd articles/images/{{ARTICLE_SLUG}} && /Users/pinxiong/.workbuddy/binaries/python/envs/default/bin/python -c "import resvg_py,pathlib; b=resvg_py.svg_to_bytes(svg_path='name.svg', background='#0a1024', width=1440); b=b.get('data') if isinstance(b,dict) else b; pathlib.Path('name.png').write_bytes(b)"`
   Design language: dark gradient `#0a1024` to `#0d1c3a`, accent colours blue
   `#2563eb`, purple `#7c3aed`, orange `#ea580c`, green `#059669`, red
   `#e11d48`, teal `#0d9488`. Every diagram in an article must be composed
   differently from the others.
6. **Tear down** with `make down`, and confirm `aia.py status {{NN}}` lists
   nothing. Say in the article what survives on purpose (the CDK bootstrap stack
   and its asset bucket) and why.
7. **Write the article** at `articles/{{ARTICLE_SLUG}}.md` with the nine
   sections in the contract's fixed order, ending at `## Takeaways`. No preview
   of the next article.
8. **Self-check** before you hand it back: word count, zero tables, every fence
   tagged, no bold, no CJK, images referenced by root path and present on disk,
   account ids redacted to `123456789012`, the GitHub URL of your folder
   correct: `https://github.com/pinxiong/bedrock-agentcore-in-action/tree/main/usecases/{{NN}}-{{SLUG}}`,
   and front matter tags exactly `["ai", "agents", "agentcore", "{{FOURTH_TAG}}"]`.
   Tag policy (fixed 2026-10-18, no approval needed): `ai` and `agents` on every
   English article, `agentcore` on all seven of this series, the fourth drawn
   from this article's content, four in total, no hyphens.
9. **Commit** the use case and the article:
   `git add usecases/{{NN}}-{{SLUG}} articles/{{ARTICLE_SLUG}}.md articles/images/{{ARTICLE_SLUG}} && git commit -m "usecase {{UC_ID}} + article: {{TITLE}}"`.
   Do not push. Do not publish.

## What you hand back

A short report: the article path, word count, the list of evidence files, the
assertions that passed with their measured numbers, the cost incurred, anything
you could not run, and any decision you had to make on your own.
