# How to add a use case

Adding a use case means adding an **independent** one. Read
[the independence contract](../README.md#the-independence-contract) first: five
conditions, all checkable, and CI enforces three of them.

## 1. Claim the number

Numbers are ordered by difficulty, so pick the highest number in `usecases/` and
add one. If your new use case is easier than an existing one, do not append it:
insert it at the right rung and renumber, because the ladder contract is that
difficulty never decreases as the numbers go up.

## 2. Declare it in the capability map

Add an entry to `usecases:` in [`docs/05-capability-map.yaml`](05-capability-map.yaml).
The `deep` list is the contract your smoke test must satisfy.

```yaml
  - id: uc08
    dir: usecases/08-your-idea
    title: Your Idea
    difficulty: 5
    official:
      group: <one of the eight groups in 08-official-alignment.md>
      category: conversational-agents | workflow-automation-agents | coding-assistants
      vertical: <business vertical, e.g. Retail / E-commerce>
      samples:
        - <NN-layer/NN-group/NN-sample/ in awslabs/agentcore-samples>
    standalone: true
    knowledge_prereqs: [whatever a reader should already understand]
    cli: agentcore add registry        # every command here is checked against the installed CLI
    deep: [registry, runtime]
    incidental: [observability]
    assertions:
      - one sentence per assertion, in behavioural terms
    cost_usd: 10
    minutes: 200
```

Two fields are enforced by CI rather than by convention:

- `official.*` is what makes the series mappable onto the AWS samples repository. Without
  it a reader cannot tell where this use case sits in the official taxonomy.
- `cli` is probed with `agentcore <cmd> <sub> --help`. A command that does not exist in
  the installed CLI fails the check. This is not hypothetical: the plan itself carried
  `agentcore create --harness` and `agentcore add identity` for a while, and neither exists.

Also update [`docs/06-difficulty-ladder.md`](06-difficulty-ladder.md): no CI job
checks that table, so it is on you.

## 3. Scaffold the skeleton

```bash
python aia.py new 08-your-idea --difficulty 5
```

This reads `deep` from the map, then generates:

```
usecases/08-your-idea/
├── README.md               from the twelve-section template
├── article.md              from the twelve-section article template
├── .env.example            placeholders only
├── app/aia_uc08/           the baseline agent, verified entrypoint contract
│   ├── main.py
│   ├── model/
│   └── pyproject.toml
├── raw/                    boto3 sidecar: control plane + data plane, never deployed
├── tests/                  smoke.py plus the independence helper
├── agentcore/              agentcore.json is yours to fill; cdk/ is generated
└── diagrams/
```

Pass `--capabilities a,b` to override the map, and `--dry-run` to see what would
happen. The generated `smoke.py` carries a `CAPABILITY_ASSERTIONS` dict with one
`TODO` per declared capability. **`python aia.py test 08` fails until every one is
implemented.** That is the point: a use case is not done because it deploys.

## 4. Build it, and keep it independent

Three rules while you work, matching the contract:

| Rule | Means |
|---|---|
| **I3** own stack | `agentcore/agentcore.json` must not reference another use case's stack. No `Fn.import_value`, no `terraform_remote_state`, no `Outputs` from a sibling. The verifier greps for all of these. |
| **I4** own source | The directory `codeLocation` points at (the CLI's `app/<AgentName>/`) must not import another use case. If you need a helper, copy it in. |
| **I2** own cleanup | Tag every resource `UseCase=0X`. Untagged resources are invisible to the cleanup assertion and will silently survive `python aia.py down`. |

The trade-off is duplication, and it is deliberate. Say so out loud in the
**What you repeated** section of the README rather than hiding it. A reader who
mistakes a self-contained example for a microservice repository will draw the
wrong architecture conclusions.

## 5. Write the two documents

| File | Audience | Rule |
|---|---|---|
| `README.md` | someone at a terminal | every step is copy-pasteable, with command, expected output, how to verify, and what to do if it fails. No `...` placeholders. |
| `article.md` | someone reading for the idea | narrative, following the twelve-section skeleton. Points at the README for the full detail instead of duplicating it. |

Both templates already carry the four blocks borrowed from the official sample READMEs.
Fill them in rather than dropping them:

| Block | Why it is there |
|---|---|
| At a glance (article §1) | the official samples all open with the same metadata table: agent type, capabilities, framework, model, complexity |
| Cleanup | the official templates never omit teardown; the article needs it too, not just the README |
| Files | one row per path, saying what it is and who writes it |
| Related official samples | two to four paths in `awslabs/agentcore-samples` showing the same capability |

Do not merge README and article. A document that is both is worse at both jobs.

## 6. Prove it

```bash
python aia.py up 08 && python aia.py test 08 && python aia.py down 08

python aia.py verify 08    # assertions plus coverage plus independence for uc08
python aia.py verify-all   # the whole repo
```

The acceptance criteria are the eight items in
[PLAN.md](../PLAN.md) section 9. The two that get skipped most often:

- item 3, `python aia.py down 08` zeroes the cost **and** the `UseCase` tag assertion comes
  back empty. Check the manual cleanup list too: CloudWatch log groups, S3
  buckets, Secrets Manager entries and token vault records are not always removed
  by `agentcore remove all`.
- item 8, the declared difficulty still fits its band in the rubric, and the
  sequence is still non-decreasing.

## 7. Check CI expectations

| Workflow | What it enforces |
|---|---|
| `usecase-ci.yml` | only the use cases whose paths changed are deployed and tested |
| `independence-check.yml` | one use case deploys in a clean account with no siblings present, then asserts no sibling resources appeared |
| `docs-link-check.yml` | no dangling links between README, PLAN and `docs/` |
| `eval-gate.yml` | UC06 only: a regression in batch evaluation blocks the pull request |

`verify-coverage.py` also fails the build on four things that are easy to get wrong,
so run it locally before pushing:

```bash
python aia.py verify-all
```

| Class | It fails when |
|---|---|
| `[COVER]` | a capability is not `deep` anywhere, or the 14-item list drifted |
| `[EVID]` | a use case declares `deep: [cap]` but `tests/smoke.py` has no assertion for it |
| `[INDEP]` | the difficulty sequence decreases, agentcore/ is missing, or the `codeLocation` directory imports another use case |
| `[CMD]` | a `cli:` entry names a command, subcommand or flag the installed CLI does not have |
