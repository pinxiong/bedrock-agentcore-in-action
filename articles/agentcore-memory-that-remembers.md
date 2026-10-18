---
title: "An Agent That Remembers: Short-Term and Long-Term Memory on AgentCore"
description: "AgentCore Memory tutorial: one memory resource, a preference recalled a session later, two actors kept apart, and an episodic record retrieved by meaning. Measured on us-east-1."
date: 2026-10-18
draft: false
tags: ["ai", "agents", "agentcore", "llm"]
canonical_url: "https://xiongpin.dev/posts/agentcore-memory-that-remembers/"
cover:
  image: "/images/agentcore-memory-that-remembers/cover.png"
  alt: "Cover art: two sessions, one memory resource, a preference stated once and applied later"
---

An agent that forgets the moment the reply finishes is the correct default, and the wrong behaviour for a reorder assistant. This article adds memory to that agent and proves it three ways: a preference survives into a new session, a second manager cannot see the first manager's memory, and a failed restock is recalled by what it meant.

Every number below was measured while writing this, in one AWS account, in `us-east-1`.

## The use case

Northwind Gear runs forty stores and restocks them every Monday. A store manager told the reorder assistant, once, that only the North China region matters to them. The next Monday, in a new session, the assistant asked which region again. Nothing was wrong with the model. The sentence never left the session it was said in, so there was nothing for a later session to find.

## What AgentCore does here

Three of the nine capabilities carry this use case.

- Memory: one memory resource holds both halves. Short term is an append-only event log keyed by actor and session; long term is a set of records the service extracts from those events into namespaces. This article goes deep on that split.
- Runtime: hosts `app/aia_uc02/` as a managed endpoint. Each session gets its own microVM, which is why the session id matters.
- Identity, lightly: the actor id arrives in the invoke payload or in a runtime header, and becomes the partition key of the memory namespace. There is no Cognito pool here.

The other six stay off: no Gateway, no Policy, no Evaluations, no Code Interpreter, no Browser, and no Observability work beyond what the runtime emits.

## Requirements

- Node.js 20 or newer (22.22.2 here), AgentCore CLI 0.31.1, AWS CLI 2.x, uv 0.11.9
- Python 3.10 to 3.14 on the host; the runtime target is PYTHON_3_13, set in the contract
- An AWS account with Bedrock model access, region `us-east-1`
- Model `deepseek.v3.2`, passed through the `MODEL_ID` environment variable
- IAM permissions to create a runtime, its role, and a memory resource with an execution role; the CLI writes both roles for you

```bash
agentcore --version   # 0.31.1
aws configure get region   # us-east-1
aws sts get-caller-identity --query Account --output text
# 123456789012
```

## The code

https://github.com/pinxiong/bedrock-agentcore-in-action/tree/main/usecases/02-memory

```text
02-memory/
├── run.py                     # every operation; forwards to tests/ and agentcore
├── Makefile                   # forwards to run.py, holds no logic
├── agentcore/
│   ├── agentcore.json         # the runtime plus one memory with three strategies
│   └── aws-targets.json       # account 123456789012, region us-east-1
├── app/aia_uc02/
│   ├── main.py                # the agent: prompt, tool, actor resolution, entrypoint
│   ├── memory.py              # the only file that knows short term from long term
│   ├── model/load.py          # MODEL_ID -> BedrockModel
│   └── pyproject.toml         # dependencies packaged into the zip
└── tests/
    ├── smoke.py               # the four assertions, run against the deployment
    └── doctor.py              # toolchain, credentials, memory contract
```

`memory.py` is the whole subject of the article, and `agentcore.json` is where the namespace layout is decided.

## How it works

The memory resource is declared once, and the strategies decide what long-term records exist at all:

```json
"memories": [{
  "name": "aia_uc02_mem",
  "eventExpiryDuration": 30,
  "strategies": [
    {"type": "USER_PREFERENCE", "namespaceTemplates": ["/users/{actorId}/preferences"]},
    {"type": "EPISODIC",        "namespaceTemplates": ["/episodes/{actorId}/{sessionId}"],
                                "reflectionNamespaceTemplates": ["/episodes/{actorId}"]},
    {"type": "SEMANTIC",        "namespaceTemplates": ["/users/{actorId}/facts"]}
  ]
}]
```

Two things follow from that layout. The actor id is inside the namespace, so isolation is a property of the key space rather than a filter some code path has to remember. And the reflection namespace sits one level above the per-session one, so a prefix read of `/episodes/{actorId}/` reaches both a single episode and the lessons written across all of them.

The agent itself never stores a preference. It appends the turn and asks a question:

```python
def remember(self, actor, session_id, turns):
    event = self.client.create_event(
        memory_id=self.memory_id, actor_id=actor,
        session_id=session_id, messages=turns)
    return event.get("eventId")

def recall(self, actor, query):
    found = []
    for label, ns, by_path in (("preference", f"/users/{actor}/preferences", False),
                               ("fact", f"/users/{actor}/facts", False),
                               ("episode", f"/episodes/{actor}/", True)):
        try:
            kwargs = {"memory_id": self.memory_id, "query": query, "top_k": TOP_K}
            kwargs["namespace_path" if by_path else "namespace"] = ns
            found += [{"kind": label, "text": _text(r)}
                      for r in self.client.retrieve_memories(**kwargs)]
        except Exception as exc:  # one bad namespace is not fatal
            log.warning("uc02 recall failed for %s: %s", label, exc)
    return found
```

Writing the event is also what starts extraction, which is why the second session can find a sentence the first session said. Extraction is not part of the invoke: the reply returned in 19 seconds and the records arrived later.

Retrieval happens before the model is called, because the records become part of the system prompt:

```python
records = store.recall(actor, prompt) if store else []
agent = Agent(
    model=load_model(),
    system_prompt=f"{SYSTEM_PROMPT}\n\nWhat you remember about this manager:\n{render(records)}",
    conversation_manager=NullConversationManager(),
)
```

A fresh Agent per invoke, not one per session. A cached agent would keep serving the first turn's memories, and a retrieval failure is logged and swallowed: an agent that cannot remember is still useful.

## Deploy it

From the use case folder:

```bash
make doctor
```

```text
toolchain
  ... four checks: python 3.14.0, node v22.22.2, aws cli 2.15.6, uv 0.11.9 ...

agentcore cli
  PASS  agentcore 0.31.1

this folder
  PASS  codeLocation 'app/aia_uc02' exists
  PASS  app environment present at app/aia_uc02/.venv
  PASS  run.py present
  ... four more folder checks ...

memory contract
  PASS  memory 'aia_uc02_mem' declared, events expire in 30d
  PASS  strategy USER_PREFERENCE present (the regional preference the second session has to recall)
  PASS  strategy EPISODIC present (the failed restock a later session has to recall)
  PASS  every strategy namespaces on {actorId}, so actors are isolated by key

aws environment
  ... three checks: credentials work, region is us-east-1, model available ...

19 passed, 0 warned, 0 failed
next: make deploy
```

The memory contract check exists because a deployment missing the EPISODIC strategy would succeed and then fail an assertion much later.

```bash
make deploy
```

```text
  Load deployment target ............ 1 ms
  Validate project .................. 682 ms
  Sync CDK dependencies ............. 2 ms
  Build CDK project ................. 2.4 s
  Synthesize CloudFormation ......... 7.1 s
  Check bootstrap status ............ 665 ms
  Check stack status ................ 1.4 s
  Deploy to AWS ..................... 4 m 7 s
  Persist deployment state .......... 715 ms

Total Duration: 4m 23s

Deployed to 'default' (stack: AgentCore-aiauc02-default)
Outputs:
  ApplicationMemoryAiaUc02MemIdOutput7F0802F1: aiauc02_aia_uc02_mem-y7Ql9N3D59
  ApplicationAgentAiaUc02RuntimeArnOutput9F81CB35:
    arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/aiauc02_aia_uc02-ACujAB8uYJ
```

![Terminal capture: the deploy step timings, the memory id and the runtime ARN](/images/agentcore-memory-that-remembers/S1-deploy.png)

Two sessions, two different session ids. The first only states a preference:

```bash
python3 run.py invoke --session b0b998ab-89ca-4387-99cb-fc01130e9108-ff3568e8 \
  --prompt "From now on, only reorder for the North China region. Ignore every other region."
```

```text
Based on your explicit instruction, I'll only reorder for the North China region.
The North China region needs reorders at three stores: Beijing Haidian (42 thermal
flasks), Tianjin Heping (17 insulated mugs), and Shijiazhuang Qiaoxi (8 lunch boxes). ...
```

The second one is a new session and says nothing about regions:

```bash
python3 run.py invoke --session 03fd411e-293b-4aa2-a219-bd996c7e3481-6b0df16e \
  --prompt "Draft this week's reorder list."
```

```text
I'll create the reorder list for the North China region as specified in your preferences. ...
Here's this week's reorder list for the North China region:
Store: Beijing Haidian, SKU: SKU-1001, ... Reorder Quantity: 42 units
Store: Tianjin Heping, SKU: SKU-1002, ... Reorder Quantity: 17 units
Store: Shijiazhuang Qiaoxi, SKU: SKU-1003, ... Reorder Quantity: 8 units
Note: I've applied your documented preference to only reorder for North China region, ...
```

Both captures are trimmed, and `...` marks every cut; the store lines also lose the bold markers the model emitted, which this page would render as bold. The second session had never seen the sentence about North China. The only place it could have come from is the memory resource.

![Terminal capture: a preference written in one session and applied in the next](/images/agentcore-memory-that-remembers/S2-cross-session-recall.png)

The assertions run against the deployment:

```bash
make test
```

```text
memory
       session 1 e9f9d728131040b1ad532866e69b4981-cd9243d4
       extraction visible after 1.5s · 1 record(s)
       session 2 34b26d624d2140d1b767098a09abdfaa-8d1f1d6b · tools ['reorder_candidates']
       reply "Based on your preference for North China region, here is this
       week's reorder list: ..."
  PASS assert_memory_1: a second session retrieves a preference written in the first
       actor store_manager_north sees '...Only reorder for the North China region...'
       actor store_manager_south sees '...Only reorder for the South China region...'
       actor store_manager_south reply "Based on your preference for South China
       region only, here's this week's reorder list: ..."
  PASS assert_memory_2: actor A cannot retrieve actor B memories
       episodic extraction visible after 959s
       reply "... Remember: the Guangzhou warehouse must not be used for North
       China restocks."
  PASS assert_memory_3: episodic strategy recalls a previously failed approach

  PASS independence: no other use case's resources present

4 passed, 0 failed
```

The 1.5 seconds needs explaining: that preference had already been extracted by an earlier run against the same resource, so the read found it immediately. The episode was new, and took 959.

![Terminal capture: the three memory assertions and the independence check](/images/agentcore-memory-that-remembers/S3-verify.png)

Teardown is two steps, and the second one deletes:

```bash
make down
aia.py status 02
```

```text
>> agentcore remove all -y
All schemas reset to empty state
>> agentcore deploy -y --target default
Deploy to AWS...
Tear down stack...
Total Duration: 4m 11s

$ aia.py status 02
AgentCore Status (target: default, us-east-1)

Agents
  aia_uc02: Local only

Memories
  aia_uc02_mem: Local only (USER_PREFERENCE, EPISODIC, SEMANTIC)
```

![Terminal capture: remove all, the reconciling deploy, and both resources reporting Local only](/images/agentcore-memory-that-remembers/S4-teardown.png)

Removal only empties the local contract; the reconciling deploy destroys the stack. One thing survives on purpose: the CDK bootstrap stack and its asset bucket. The memory resource does not survive, which is why a re-deploy starts empty and has to re-earn every assertion.

## What it produced

![The memory resource as two halves: an event log and three namespaces keyed by actor id](/images/agentcore-memory-that-remembers/F1-memory-architecture.png)

The measured loop, one actor, two sessions:

![The cross-session loop: an event, its extracted record, and a second session reading the record](/images/agentcore-memory-that-remembers/F2-two-sessions.png)

The two actors wrote to `/users/store_manager_north/preferences` and `/users/store_manager_south/preferences`; a semantic query for "which region does this store manager reorder for" returned North China to one and South China to the other, and asking the model the same question produced South China for the southern manager. There is no filter to get wrong, because the actor id is part of the key.

The third assertion is the one that taught me something. Episodic extraction is slow: the episodes in this resource were written 15 minutes 11 seconds to 15 minutes 14 seconds after the event timestamp they came from. It is not a broken strategy, it is a slower queue, and a 300-second deadline can only ever fail against it.

A prefix read of `/episodes/store_manager_north/` returns two kinds of record: a `BASE` episode filed under the session that produced it, and a `REFLECTION` written one level up, over all of them. That is why the namespace template has a `{sessionId}` and the reflection template does not:

```text
BASE        /episodes/store_manager_north/195f957a...-78cd451f/
            {"situation":"The user reported a failed restocking attempt ... 9-day lead time"}
REFLECTION  /episodes/store_manager_north/
            {"title":"Structured Output Format for Reorder and Inventory Lists"}
```

Cost, measured on one traced invoke: 3,433 input and 210 output tokens across two model calls, which at 0.62 and 1.85 USD per million tokens is 0.0025 USD. Memory storage and the extraction calls bill separately; I did not measure that line.

## Troubleshooting

- `Invalid length for parameter runtimeSessionId, value: 22, valid min length: 33`. Short readable session ids look fine and fail before they are sent. The smoke test now builds ids from two uuid4 halves, because one hex uuid is 32 characters, one short of the minimum.
- `no episodic record ... within 1500s`. Not a broken strategy, just a slow queue: raise the deadline past the observed fifteen minutes, and print how long the wait actually took so the number in the article is a measurement.

## Takeaways

- Memory is two mechanisms, not one: an event log you write, and records the service extracts. Only the second one survives a new session.
- Put the actor id inside the namespace template. Isolation then costs nothing and cannot be forgotten in a code path.
- Extraction is asynchronous and slow: fifteen minutes for an episode. Every assertion needs a deadline, and every deadline needs to be longer than you think.
- Retrieval belongs in the system prompt, before the model call, not in a tool the model may or may not choose.
- Teardown is real: `remove all` empties the contract, the deploy that follows does the deleting.
