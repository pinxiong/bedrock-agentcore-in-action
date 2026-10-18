---
title: "An Agent That Remembers: Short-Term and Long-Term Memory on AgentCore"
description: "AgentCore Memory, measured: a preference recalled four minutes later in a new session, three managers kept apart by actor id, and a failed restock quoted seventeen minutes later."
date: 2026-10-18
draft: false
tags: ["ai", "agents", "agentcore", "llm"]
canonical_url: "https://xiongpin.dev/posts/agentcore-memory-that-remembers/"
cover:
  image: "/images/agentcore-memory-that-remembers/cover.png"
  alt: "Cover art: two sessions, one memory resource, a preference stated once and applied later"
---

An agent that forgets when the reply finishes is the right default and the wrong behaviour for a reorder assistant. This article adds memory to one and proves it three ways: a preference survives into a new session, three managers never see each other's memory, and a failed restock is quoted back seventeen minutes later. Every number was measured in one account, in `us-east-1`.

## The use case

Northwind Gear runs forty stores and restocks them every Monday. A store manager told the reorder assistant, once, that only the North China region matters to them. The next Monday, in a new session, the assistant asked which region again. Nothing was wrong with the model: the sentence never left the session it was said in.

## What AgentCore does here

Three of the nine capabilities carry this use case.

- Memory: one resource holds both halves. Short term is an append-only event log keyed by actor and session; long term is what the service extracts from those events into namespaces. This article goes deep on that split.
- Runtime: hosts `app/aia_uc02/` as a managed endpoint, one microVM per session, which is why the session id matters.
- Identity, lightly: the actor id becomes the partition key of the namespace and travels as `--user-id`. No Cognito pool here.

The other six stay off: no Gateway, no Policy, no Evaluations, no Code Interpreter, no Browser, and no Observability beyond the traces the runtime emits.

## Requirements

- Node.js 20 or newer (22.22.2 here), the AgentCore CLI 0.31.1, AWS CLI 2.x, uv 0.11.9
- Python 3.10 to 3.14 on the host; the runtime target is PYTHON_3_13, set in the contract
- An AWS account with Bedrock model access; region `us-east-1` for everything
- Model `deepseek.v3.2`, passed to the code through `MODEL_ID`
- IAM permissions to create a runtime, its role, and a memory resource with an execution role; the CLI writes both roles

## The code

https://github.com/pinxiong/bedrock-agentcore-in-action/tree/master/usecases/02-memory

```text
02-memory/
├── agentcore/
│   ├── agentcore.json         # the runtime plus one memory with three strategies
│   └── aws-targets.json       # account 123456789012, region us-east-1
├── app/aia_uc02/
│   ├── main.py                # the agent: prompt, tool, actor resolution, entrypoint
│   ├── memory.py              # the only file that knows short term from long term
│   ├── model/load.py          # MODEL_ID -> BedrockModel
│   └── pyproject.toml         # dependencies packaged into the zip
└── tests/
    └── test_sanitize.py       # offline unit tests for the sanitizer, no AWS
```

`memory.py` is the subject of the article; `agentcore.json` decides the namespace layout.

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

The actor id sits inside the namespace, so isolation is a property of the key space rather than a filter some code path has to remember. The reflection namespace sits one level up, so a prefix read of `/episodes/{actorId}/` reaches a single episode and the lessons written across all of them.

The agent never stores a preference itself. It appends the turn and asks a question:

```python
def remember(self, actor, session_id, turns):
    # ... the real one wraps this in try/except and returns None on failure
    event = self.client.create_event(
        memory_id=self.memory_id, actor_id=actor,
        session_id=session_id, messages=turns)
    return event.get("eventId")

def recall(self, actor, query):
    # ... condensed: the real one also drops records whose text is empty,
    # and continues past a namespace that failed instead of falling through
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

Writing the event starts extraction, which is how a later session finds a sentence the earlier one said. It is not part of the invoke: the call returned in 17 seconds, the record arrived later.

Retrieval runs before the model, because the records become part of the system prompt:

```python
records = store.recall(actor, prompt) if store else []
agent = Agent(
    model=load_model(),
    system_prompt=f"{SYSTEM_PROMPT}\n\nWhat you remember about this manager:\n{render(records)}",
    # ... tools=list(TOOLS) and conversation_manager=NullConversationManager() too
)
```

A fresh `Agent` per invoke: a cached one would keep serving the first turn's memories. A retrieval failure is logged and swallowed.

## Deploy it

From the use case folder:

```bash
agentcore deploy -y --target default
```

![Terminal capture: the deploy steps and the two resource ids](/images/agentcore-memory-that-remembers/S1-deploy.png)

Wall clock: 4 minutes 20 seconds, ending in a memory id and a runtime ARN.

```bash
agentcore status
```

![Terminal capture: one runtime READY and one memory with three strategies](/images/agentcore-memory-that-remembers/S2-status.png)

One contract, so one deploy creates both halves, and the memory names its three strategies: the cheapest proof the extraction was requested.

```bash
agentcore invoke --user-id store_manager_south --session-id 7d1f4a0c9b2e4d38a5c6e7f801234567-229cdb2d \
  --prompt "From now on, only reorder for the South China region. Ignore every other region."
```

![Terminal capture: the preference is accepted and applied immediately](/images/agentcore-memory-that-remembers/S3-preference-south.png)

A new session, four minutes later:

```bash
agentcore invoke --user-id store_manager_south --session-id 8b2c5d1e0f3a4b6c9d8e7f6054321098-33438667 \
  --prompt "Draft this week's reorder list."
```

![Terminal capture: the new session reorders for South China without being told](/images/agentcore-memory-that-remembers/S4-recall-south.png)

255 seconds separate the event from the answer, and this session never saw the sentence. Only the memory resource could have supplied it.

```bash
agentcore invoke --user-id store_manager_east --session-id 9c3d6e2f1a4b5c7d8e9f0a1b23456789-584aa045 \
  --prompt "From now on, only reorder for the East China region. Ignore every other region."
```

![Terminal capture: the eastern manager's first turn, before extraction has run](/images/agentcore-memory-that-remembers/S5-preference-east.png)

```bash
agentcore invoke --user-id store_manager_east --session-id 0d4e7f3a2b5c6d8e9f0a1b2c34567890-37ad719d \
  --prompt "Draft this week's reorder list."
```

![Terminal capture: East China, from a session that never mentioned a region](/images/agentcore-memory-that-remembers/S6-recall-east.png)

236 seconds after its own event, the eastern manager is answered for East China. Now the same question to the southern one, seconds later:

```bash
agentcore invoke --user-id store_manager_south --session-id 1e5f8a4b3c6d7e9f0a1b2c3d45678901-4a0d1bea \
  --prompt "Draft this week's reorder list."
```

![Terminal capture: the same prompt, the other manager, the other region](/images/agentcore-memory-that-remembers/S7-isolation.png)

Two actors, one prompt, two answers, no overlap: the actor id is part of the key.

```bash
agentcore invoke --user-id store_manager_east --session-id 2f6a9b5c4d7e8f0a1b2c3d4e56789012-0fa33c38 \
  --prompt "I tried restocking my stores from the Guangzhou warehouse last month. It failed: the lead time was 9 days and three stores stocked out. Make a note of it."
```

![Terminal capture: a failed restock noted in one session](/images/agentcore-memory-that-remembers/S8-episode.png)

Seventeen minutes later, nobody re-sends that sentence:

```bash
agentcore invoke --user-id store_manager_east --session-id 3a7b0c6d5e8f9a1b2c3d4e5f67890123-31527d8a \
  --prompt "Is it a good idea to ship this week's East China restock from the Guangzhou warehouse?"
```

![Terminal capture: the answer quotes the 9-day lead time nobody mentioned](/images/agentcore-memory-that-remembers/S9-episode-recall.png)

1,022 seconds after the episode was written, the answer recommends against Guangzhou and names the 9-day lead time: the episodic strategy recalling an event by meaning.

Every invoke left a trace:

```bash
agentcore traces list
```

![Terminal capture: one row per invoke of this runtime](/images/agentcore-memory-that-remembers/S10-traces-list.png)

```bash
agentcore traces get 6ad46781381df402758baa6d42b96dd3
```

![Terminal capture: the trace is written to a local JSON file](/images/agentcore-memory-that-remembers/S11-trace-get.png)

![Terminal capture: the span table, three memory reads before one model call](/images/agentcore-memory-that-remembers/S12-trace-spans.png)

Three `RetrieveMemoryRecords` calls at 349, 268 and 262 milliseconds, one per namespace, then `invoke_agent` at 2,228 milliseconds with 1,400 input and 94 output tokens. Memory work happens before the model runs, which is what the code promises.

```bash
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=agentcore-in-action --region us-east-1
```

![Terminal capture: four resources, every one tagged UseCase=02](/images/agentcore-memory-that-remembers/S13-independence.png)

Four resources, all this use case.

Teardown is two commands, and the second one deletes:

```bash
agentcore remove all -y
agentcore deploy -y --target default
agentcore status
```

![Terminal capture: remove all, the reconciling deploy, an empty account](/images/agentcore-memory-that-remembers/S14-teardown.png)

`remove all` empties the local contract and deletes nothing on AWS; the deploy after it reconciles the stack to nothing in 4 minutes 13 seconds, and the tag query then returns zero rows. Both JSON files are emptied, so restore them from git.

## What it produced

![The memory resource as two halves: an event log and three namespaces keyed by actor id](/images/agentcore-memory-that-remembers/F1-memory-architecture.png)

![The cross-session loop: an event, its extracted record, and a second session reading the record](/images/agentcore-memory-that-remembers/F2-two-sessions.png)

Three actors, three namespaces, one prompt producing two different lists. Extraction lag was 255 seconds for a preference and 1,022 for an episode, which decides every deadline you write.

A prefix read of `/episodes/store_manager_east/` returns a `BASE` episode filed under its session and a `REFLECTION` written one level up, hence the `{sessionId}` in one template and not the other.

## Troubleshooting

- `Invalid length for parameter runtimeSessionId, value: 22, valid min length: 33`. Short readable session ids fail before they are sent. Build them from two uuid4 halves, because one hex uuid is 32 characters, one short of the minimum.
- The actor id sent as `-H x-amzn-bedrock-agentcore-runtime-custom-actor-id: ...` never reached the agent, and the reply described the northern manager's memory because the code fell back to its default actor. Send it as `--user-id`, which arrives as `x-amzn-bedrock-agentcore-runtime-user-id`, and log the header names you receive once. This cost one deploy to find and is kept in `evidence/27`.
- Episodic extraction took 17 minutes, so a 300-second deadline can only fail. Choose the deadline from a measurement.
- `remove all` needs `-y` in any non-interactive shell, and it empties `agentcore.json` and `aws-targets.json`. Restore both from git before deploying again.

## Takeaways

- Memory is two mechanisms: an event log you write, and records the service extracts. Only the second reaches a new session.
- Put the actor id inside the namespace template. Isolation then costs nothing and cannot be forgotten in a code path.
- Extraction is asynchronous and slow, and strategies differ. Every assertion needs a deadline longer than the slowest one.
- Send the actor id with `--user-id` and verify it arrived. A silent fallback to a default actor looks like working memory and is the opposite.
- Teardown is real: `remove all` empties the contract, the deploy after it does the deleting.
