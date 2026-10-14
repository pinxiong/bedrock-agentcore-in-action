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
    standalone: true
    knowledge_prereqs: [whatever a reader should already understand]
    deep: [registry, runtime]
    incidental: [observability]
    assertions:
      - one sentence per assertion, in behavioural terms
    cost_usd: 10
    minutes: 200
```

Also update [`docs/06-difficulty-ladder.md`](06-difficulty-ladder.md): no CI job
checks that table, so it is on you.

## 3. Scaffold the skeleton

```bash
python aia.py new 08-your-idea --difficulty 5
```

This reads `deep` from the map, then generates:

```
usecases/08-your-idea/
├── README.md      from the twelve-section template
├── article.md     from the article template
├── .env.example   placeholders only
├── src/main.py    the baseline agent, verified entrypoint contract
├── tests/         smoke.py plus the independence helper
├── agentcore/     agentcore.json is yours to fill; cdk/ is generated
├── diagrams/
└── scripts/
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
| **I4** own source | `src/` must not import another use case. If you need a helper, copy it in. |
| **I2** own cleanup | Tag every resource `UseCase=0X`. Untagged resources are invisible to the cleanup assertion and will silently survive `python aia.py down`. |

The trade-off is duplication, and it is deliberate. Say so out loud in the
**What you repeated** section of the README rather than hiding it. A reader who
mistakes a self-contained example for a microservice repository will draw the
wrong architecture conclusions.

## 5. Write the two documents

| File | Audience | Rule |
|---|---|---|
| `README.md` | someone at a terminal | every step is copy-pasteable, with command, expected output, how to verify, and what to do if it fails. No `...` placeholders. |
| `article.md` | someone reading for the idea | narrative, following the eight-part skeleton. Points at the README for the full detail instead of duplicating it. |

Do not merge them. A document that is both is worse at both jobs.

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
