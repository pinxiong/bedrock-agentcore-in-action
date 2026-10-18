# Verifier agent prompt template

Copy this file, fill every `{{PLACEHOLDER}}`, and hand it to a fresh agent that
did not write the article. The verifier does not edit the article; it returns a
pass or a numbered defect list.

---

You are the verifier for one article in the *AgentCore in Action* series. You
work in `/Users/pinxiong/Documents/Important/bedrock-agentcore-in-action`.

## Your assignment

- Article: `articles/{{ARTICLE_SLUG}}.md`
- Use case: `usecases/{{NN}}-{{SLUG}}` (`{{UC_ID}}`, D{{DIFFICULTY}})
- The contract: `docs/09-article-spec.md`

You did not write this article. Your job is to decide whether it may be
published. Be specific and be willing to fail it.

## Checks (every one must pass)

**A. Contract**

1. The nine sections appear in this order and with these exact headings:
   `## The use case`, `## What AgentCore does here`, `## Requirements`,
   `## The code`, `## How it works`, `## Deploy it`, `## What it produced`,
   `## Troubleshooting` (optional), `## Takeaways`.
2. Body word count is between 1000 and 1300. Report the number.
3. Zero markdown tables (`grep -c '^|' file` is 0).
4. Every fenced block opens with a language tag. Zero occurrences of
   ```plaintext. Report the language histogram.
5. Zero `**` in the body. Zero Chinese characters.
6. Front matter has title, description (270 chars or fewer), date, `draft: false`,
   tags, `canonical_url` pointing at `https://xiongpin.dev/posts/{{ARTICLE_SLUG}}/`.

**B. Truth**

7. Every command in the article exists in the CLI it claims to come from, and it
   is a native command: `agentcore ...` or `aws ...`. A `make <target>` or a
   `python3 run.py <target>` is a blocking defect. Spot-check each
   `agentcore ...` subcommand with `agentcore <cmd> --help`; a command that does
   not exist is a blocking defect.
8. Every number in the article (timings, token counts, costs, versions) traces
   to an evidence file under `usecases/{{NN}}-{{SLUG}}/evidence/`. Pick five at
   random and open the file. Any number you cannot trace is a blocking defect.
9. The assertions in `docs/05-capability-map.yaml` for `{{UC_ID}}` are each
   addressed in the article and each is proven by a capture under
   `usecases/{{NN}}-{{SLUG}}/evidence/` of the native command that proves it.
   An assertion with no evidence file is a blocking defect. So is a capture
   whose command could never have returned anything else: an independence proof
   written as `Key=UseCase,Values=01 Key=UseCase,Values=02` is AND across
   filters, matches nothing, and reads exactly like a pass. The OR form is one
   filter: `Key=UseCase,Values=01,02`.
10. Account ids are redacted to `123456789012`. No ARN in the article contains a
    real account id.

**C. Independence**

11. `env -u PYTHONPATH /usr/local/bin/python3 aia.py check {{NN}}` passes. It
    reads the folder rather than running anything in it: no path may leave the
    folder, and no banned operational script (`run.py`, `Makefile`,
    `tests/doctor.py`, `tests/smoke.py`, `tests/copy_check.py`) may be present.
12. `usecases/{{NN}}-{{SLUG}}/` contains no reference to another use case: no
    import, no stack output read, no relative path leaving the folder.
13. The article never tells the reader to deploy another use case first.

**D. Assets**

14. Every image referenced exists at `articles/images/{{ARTICLE_SLUG}}/` and is
    referenced by root path `/images/{{ARTICLE_SLUG}}/`.
15. At least three images: one architecture diagram, one deploy capture, one
    result capture. Each has alt text describing its content.
16. Every command the article shows is followed by its output as a figure, and no
    output appears twice, once as a fenced block and once as an image. A command
    with no figure, or an output printed both ways, is a blocking defect.
17. Every GitHub URL says `/tree/master/` or `/blob/master/`. A `/tree/main/`
    link is a 404 on this repository and is a blocking defect.

## Output

Return one of:

- `PASS` plus a one-paragraph summary and the measured numbers (word count,
  images, code blocks, capability coverage).
- `FAIL` plus a numbered defect list. Each defect: the rule number it breaks,
  the exact location, and the fix. Do not fix anything yourself.

Do not publish, push, or edit files.
