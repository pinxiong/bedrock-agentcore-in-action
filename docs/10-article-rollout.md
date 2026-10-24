# Article rollout (uc01 to uc07)

Seven articles, one per use case, in ladder order. Each is written by one agent,
verified by a different agent, and published only after the verifier passes.
Contract: `docs/09-article-spec.md`. Difficulty ladder:
`docs/06-difficulty-ladder.md`. Capability map: `docs/05-capability-map.yaml`.

## The seven

| # | D | Use case | Title | Slug | 4th tag | Capabilities proven |
|---|---|---|---|---|---|---|
| uc01 | D1 | First Agent | Your First Agent as a Service: Deploying a Support Agent on AgentCore | `your-first-agent-as-a-service-on-agentcore` | aws | Runtime, Observability |
| uc02 | D2 | Memory | An Agent That Remembers: Short-Term and Long-Term Memory on AgentCore | `agentcore-memory-that-remembers` | llm | Memory |
| uc03 | D3 | Gateway and Identity | Reaching Real Systems Without Holding Credentials: Gateway and Identity | `agentcore-gateway-and-identity` | security | Gateway, Identity |
| uc04 | D3 | Policy | Stopping an Agent From Overreaching: Policy in Enforce Mode | `agentcore-policy-enforce-mode` | security | Policy |
| uc05 | D4 | Research Agent | A Research Agent That Searches, Browses and Computes | `agentcore-research-agent-harness` | aws | Harness, Web Search, Browser, Code Interpreter |
| uc06 | D4 | Quality Loop | Finding What Broke: Observability, Evaluation, Optimization | `agentcore-evaluate-and-optimize` | observability | Observability, Evaluations, Optimization |
| uc07 | D5 | Multi-Agent and Registry | Two Specialists, One Orchestrator, One Catalog: A2A and Registry | `agentcore-a2a-multi-agent-registry` | mcp | Runtime, Registry, A2A, MCP hosting, streaming, session isolation |

Fixed tags on all seven: `ai`, `agents`, `agentcore`.

## Per-article loop

1. Fill `shared/templates/agent-prompts/writer-agent.md` for the use case and
   hand it to a fresh agent. It builds or extends `usecases/NN-slug`, runs the
   full loop for real, saves captures to `usecases/NN-slug/evidence/`, writes
   `articles/<slug>.md`, and commits (no push, no publish).
2. Fill `shared/templates/agent-prompts/verifier-agent.md` and hand it to a
   different fresh agent. PASS or a numbered defect list.
3. On PASS, publish:
   ```
   env -u PYTHONPATH /usr/local/bin/python3 shared/scripts/publish_article.py \
     --slug <slug> --devto-create --medium-export
   ```
   Dev.to tags come from the article front matter. The script refuses to run if
   the master has a table, an untagged fence, a non-rooted image path, CJK
   characters, or a word count outside 1000 to 1300.
4. Record the published URLs in this table.

| # | Dev.to | xiongpin.dev | Medium | Date |
|---|---|---|---|---|
| uc01 | https://dev.to/aws-builders/your-first-agent-as-a-service-deploying-a-support-agent-on-agentcore-48hh | https://xiongpin.dev/posts/your-first-agent-as-a-service-on-agentcore/ | manual, checklist in `writing-lab/distribution/` | 2026-10-18 |
| uc02 | https://dev.to/aws-builders/an-agent-that-remembers-short-term-and-long-term-memory-on-agentcore-3bf5 | https://xiongpin.dev/posts/agentcore-memory-that-remembers/ | manual, checklist in `writing-lab/distribution/` | 2026-10-18 |
| uc03 | https://dev.to/aws-builders/reaching-real-systems-without-holding-credentials-gateway-and-identity-3p6a | https://xiongpin.dev/posts/agentcore-gateway-and-identity/ | manual, checklist in `writing-lab/distribution/` | 2026-10-23 |
| uc04 | https://dev.to/aws-builders/stopping-an-agent-from-overreaching-policy-in-enforce-mode-4dgf | https://xiongpin.dev/posts/agentcore-policy-enforce-mode/ | manual, checklist in `writing-lab/distribution/` | 2026-10-24 |
| uc05 | | | | |
| uc06 | | | | |
| uc07 | | | | |

## Budget

The ladder caps cost per use case at roughly $1, $2, $5, $3, $8, $15, $12: about
$46 in total for the seven. Every use case ends with `agentcore remove all -y`
followed by `agentcore deploy -y --target default`, so the spend is incurred once
and stops.
