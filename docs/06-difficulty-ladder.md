# The difficulty ladder

Every use case declares `difficulty: 1` to `5` in
[`docs/05-capability-map.yaml`](05-capability-map.yaml). The number is not a
feeling: it has to fit the rubric below, and `shared/scripts/verify-coverage.py`
fails CI when a declaration falls outside its band or when the sequence over the
ladder stops being non-decreasing.

## The rubric

| Level | New capabilities | New external dependencies | What you must understand to finish | Time budget |
|:--:|---|---|---|---|
| **D1** | 1 to 2 | none beyond the account and Bedrock | where the agent runs, what a session is | 30 min |
| **D2** | 1 to 2 | one stateful AWS resource | what it remembers, and per whom | 1 h |
| **D3** | 2 to 3 | an identity system or a third-party API | what it is allowed to do, and who vouches for it | 2 h 30 |
| **D4** | 3 to 5 | several services plus async or streaming | whether it is doing the job well | 4 h |
| **D5** | 5 or more | multiple agents plus org-level governance | how it coexists with other agents | 4 h |

A level is decided by the **highest** dimension, not the average. A use case that
adds one capability but asks you to stand up an identity provider is D3.

## The ladder as declared

| | 01 | 02 | 03 | 04 | 05 | 06 | 07 | Bonus |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| Level | D1 | D2 | D3 | D3 | D4 | D4 | D5 | D3 |
| Cost | < $1 | < $2 | < $5 | < $3 | < $8 | < $15 | < $12 | ~$2 |
| Time | 30 min | 1 h | 2.5 h | 2 h | 3 h | 4 h | 4 h | 2 h |

Two levels appear twice. That is deliberate: D3 and D4 each contain a pair of
use cases that are peers in cognitive load, and forcing artificial separation
would produce misleading numbers. The contract is non-decreasing, not strictly
increasing.

The bonus entry sits **outside the ladder** and is allowed to declare D3 without
breaking monotonicity, because it carries an external gate (a wallet account)
that would interrupt anyone working through the sequence.

## Why the ladder is ordered this way

The levels are not "simple feature, then complex feature". Each one answers a
different question, and the questions have a natural order:

1. **D1 asks where it runs.** Until you have deployed something and watched a
   trace, everything else is theory.
2. **D2 asks what it remembers.** State is the first thing that stops a demo
   agent from being useful, and the first thing that can leak between tenants.
3. **D3 asks what it is allowed to do.** Connecting to real systems and restricting
   those connections are two different problems, which is why the ladder has two
   D3 use cases rather than one bigger one.
4. **D4 asks whether it is any good.** Metrics only make sense once the agent is
   reaching real systems and producing real artifacts.
5. **D5 asks how it coexists.** Isolation, protocols and catalogs are questions
   that only appear when there is more than one agent.

## Editing this file

If you add a use case, keep two things consistent: the `difficulty` value in
`docs/05-capability-map.yaml` and the tables above. The verifier checks the YAML,
not this document, so an out-of-date table here is a documentation bug that no
CI job will catch. Treat this file as part of the change, not as an afterthought.
