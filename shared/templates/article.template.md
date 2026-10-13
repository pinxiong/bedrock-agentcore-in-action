# UC{{UC_NUM}} · {{UC_TITLE}}

Follows the series skeleton in [PLAN.md](../../PLAN.md) section 8.3. The operations
doc is `README.md`; this file is the narrative. Keep them separate: the README
must be copy-pasteable, the article must be readable.

> Verified on 2026-XX-XX against AgentCore as of that date.

---

## 1. The problem

{{Business situation, no technology. Who is unhappy, and about what.}}

## 2. Why the obvious approach breaks

{{The naive solution a competent engineer would try first, and the specific way it
fails in production. This section is where the article earns a reader's attention.}}

## 3. Architecture

{{One diagram. Mark what AgentCore hosts and what you own.}}

## 4. Walkthrough

{{The few commands that matter. Point at `usecases/{{UC_NUM}}-{{rest}}/` for the
full version rather than pasting everything.}}

## 5. Verification

{{Real output. A screenshot beats a paragraph.}}

## 6. What surprised me

{{The thing that cost you an hour. This is what gets shared.}}

## 7. When not to use this

{{Honest boundaries. Say what this is not for.}}

## 8. Try it yourself

```bash
cd usecases/{{UC_NUM}}-{{rest}}
make up && make test && make down
```

This use case is self-contained: you do not need any other use case deployed first.
