# 一个 JSON 文件进去，四个云资源出来：拆解 AWS Bedrock AgentCore 的底层机制

> 本文是 AgentCore 系列第 0 篇。英文原版（canonical）：*How AWS Bedrock AgentCore Actually Works*，发布于 xiongpin.dev。

多数 Agent 部署故事的结局都一样：写 Dockerfile、选实例规格、手工搓 IAM 角色，然后祈祷 YAML 没写错。AWS Bedrock AgentCore 走了另一条路：**整个部署契约就是一个 JSON 文件，一条命令把它变成一个可运行、可观测的线上服务。**

我按这条路部署了一个 Agent，中途搞挂过几次，也把从 JSON 文件到线上 endpoint 之间的每一步都翻了一遍。这篇文章按真实操作顺序走完全程：先备环境，再一步步部署、调用、看 trace，每一步都附上我实测的命令和输出。文中所有数据都来自 us-east-1 的真实部署，不是抄文档。

![AgentCore CLI 全生命周期：六条命令](images/aws-agentcore-under-the-hood/F0-command-map.png)

## 一、AgentCore 是什么，不是什么

AgentCore 是一组面向 AI Agent 的托管运行时，全家桶共 14 项能力：Runtime、Memory、Gateway、Identity、Policy、Web Search、Browser、Code Interpreter、Observability、Evaluations、Optimization、Payments、Registry 等。本文只点亮其中两格：Runtime 和 Observability。

![AgentCore：14 项能力，本文点亮 2 项](images/aws-agentcore-under-the-hood/F1-capability-map.png)

**不是什么，比是什么更重要：**

- 不是新的 Agent 框架。你照旧用 Strands、LangChain、OpenAI SDK 或者裸 Python 写 Agent；
- 不是容器编排服务。Runtime 是 serverless 的，每个 session 一个 microVM，扩缩容平台包了；
- 不是模型路由器。你的代码调 Bedrock 的方式和其他任何地方一模一样。

自管过 ECS 或 Fargate 的话，体感差异非常直接：没有 Dockerfile、没有任务定义、没有 target group、没有健康检查配置。Runtime 只要求你的代码提供两个路由，其他全是平台的。

## 二、三层心智模型

**你写 Agent 代码，写两个 JSON 文件，CLI 生成其余一切，AWS 跑一个你永远不用看的 CloudFormation 栈。**

![三层模型：你的代码、契约、管道](images/aws-agentcore-under-the-hood/F2-three-layers.png)

| 层 | 放什么 | 谁维护 |
|---|---|---|
| 你的代码 | `src/` 里的 Agent 入口 | 你 |
| 契约 | `agentcore.json` + `aws-targets.json` | 你，手写 |
| 管道 | `agentcore/cdk/` 下的 CDK 工程 | CLI，每次 deploy 重新生成 |

一条规则解释了绝大部分设计：**声明的都在 JSON 里，CLI 生成的一切都可重新生成。** 这篇文章剩下的部分，就是把这条规则从头到尾走一遍。

## 三、开跑之前：环境清单

动手前先对齐环境。以下版本全部实测过（2026-10-14）：

| 工具 | 实测版本 | 说明 | 自检 |
|---|---|---|---|
| Node.js | 22.x | CLI 要求 20+ | `node --version` |
| AgentCore CLI | 0.31.1 | 装法见下 | `agentcore --version` |
| AWS CLI | 2.x | 任意近期版本 | `aws --version` |
| Python | 本地 3.11 | CodeZip 支持 3.10–3.13 | `python3 -V` |
| AWS 账号 | 任意 | 权限见下 | `aws sts get-caller-identity` |
| 区域 | us-east-1 | 全系列统一 | `aws configure get region` |
| Docker | 不需要 | 本系列统一 CodeZip 构建 | 不适用 |

安装 CLI、把区域对准 us-east-1：

```bash
npm install -g @aws/agentcore@latest
aws configure set region us-east-1
```

然后跑四条自检，对照这个输出：

```bash
agentcore --version
# 0.31.1

aws sts get-caller-identity --query '[Account,Arn]' --output text
# 123456789012    arn:aws:iam::123456789012:user/yourname

aws configure get region
# us-east-1

aws bedrock list-foundation-models --region us-east-1 \
  --query 'modelSummaries[?modelId==`deepseek.v3.2`].modelId' --output text
# deepseek.v3.2
```

**权限分两种，别混：**

- **你（部署者）**：要有建 CloudFormation 栈、传 CDK bootstrap 桶、管 AgentCore 资源的权限。沙箱账号直接上 admin 最省事；收得很紧的账号也不用慌，CLI 权限不够时会大声报错并点名缺哪个 action，按报错逐个补即可；
- **Runtime（部署出去的 Agent）**：它的 IAM 角色是 CLI 自动生成的。我实测生成的角色只有三组权限：`bedrock:InvokeModel*`（调模型）、`logs:*`（写 `/aws/bedrock-agentcore/runtimes/` 下的日志组）、`xray:PutTraceSegments`（上报 trace）。这份自动生成的策略本身就是最小权限的好模板。

一个五秒钟的坑：如果 `agentcore --version` 报错但命令存在，多半是老的 Python 包 `bedrock-agentcore-starter-toolkit` 遮蔽了 npm 版，`pip uninstall bedrock-agentcore-starter-toolkit` 解决。

> **📸 截图位 1 · 环境自检**
> 跑完上面四条自检后，把终端截图贴到这里（替换本段）。

## 四、Step 1 · 生成项目骨架

`agentcore create` 负责搭骨架。这里用 `--no-agent` 保持最小脚手架，去掉该参数会顺带生成一个示例 Agent：

```bash
mkdir demo && cd demo
agentcore create --name demo_proj --project-name demoproj --no-agent --build CodeZip
```

实测输出：

```text
[done]  Create demoproj/ project directory
```

真正值得看的是磁盘上多了什么：一层放你未来的代码，一层属于 CLI：

![项目解剖：你写的 vs CLI 生成的](images/aws-agentcore-under-the-hood/F3-directory-anatomy.png)

关于这个布局，两个事实值得记住：

- 蓝色方块是你的输入，灰色方块是生成物。**永远不要手改灰色文件**，下一条命令就会覆盖它；
- 项目根检测很严格：CLI 从当前目录逐级向上，找到同时包含 `agentcore/` 目录和 `agentcore/agentcore.json` 文件的那一层。两者缺一都不算项目，而报错 `No agentcore project found` 不会告诉你缺的是哪个。在 `agentcore/` 里执行命令会直接报 `Please run this command from your project root directory`。

打开生成的契约文件看一眼，设计的形态一目了然：`agentcore.json` 带 15 个资源数组、全部为空；`aws-targets.json` 里只有一个 `[]`。接下来就轮到你来填了。

> **📸 截图位 2 · 项目骨架**
> 跑完 `agentcore create` 后，把输出和 `tree agentcore/` 的截图贴到这里。

## 五、Step 2 · 写契约：两个 JSON 文件

部署定义的全部内容（节选关键字段）：

```json
{
  "name": "aiauc01",
  "managedBy": "CDK",
  "runtimes": [{
    "name": "aia_uc01",
    "build": "CodeZip",
    "entrypoint": "main.py",
    "runtimeVersion": "PYTHON_3_13",
    "envVars": [{ "name": "MODEL_ID", "value": "deepseek.v3.2" }]
  }]
}
```

`create` 生成这个文件时所有资源数组都是空的，`agentcore add` 家族的子命令往里塞条目。允许手编，但以官方 schema 为准，CLI 逐字段校验。

第二个文件决定部署到哪：

```json
[{ "name": "default", "account": "123456789012", "region": "us-east-1" }]
```

这里有个反直觉的设计：`create` 只写一个空数组，账号和区域是**首次 `deploy` 时回填的**，CLI 调 STS 查明你的身份再把 target 写回文件。deploy/status/remove 都没有 `--region` 参数，这个文件就是部署位置的唯一真相源。

## 六、Step 3 · 部署：一条命令，六步

到本文的名字时刻了。在项目根目录执行：

```bash
agentcore deploy -y --target default
```

实测输出（冷账号首次部署）：

```text
✓ Load deployment target
✓ Validate project
✓ Sync CDK dependencies
✓ Build CDK project
✓ Synthesize CloudFormation
✓ Check bootstrap status
✓ Check stack status
✓ Deploy to AWS
✓ Persist deployment state
✓ Deployed to 'default' (stack: AgentCore-aiauc01-default)
  ...RuntimeArnOutput...: arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/aiauc01_aia_uc01-LH8zQV86C2
```

从命令到最后的 checkmark，一共发生六件事：

![部署六步流水线，附实测耗时](images/aws-agentcore-under-the-hood/F4-deploy-pipeline.png)

1. **打包代码**：`src/` 加平台依赖压成一个资产包，我的 Hello World 是 41 MB，本地 `.venv` 被排除，全程没有镜像构建；
2. **合成**：CLI 跑内置的 CDK app，读两个 JSON，产出 CloudFormation 模板到 `cdk.out/`；
3. **上传资产**：zip 进 S3 桶（`cdk bootstrap` 一次性建的）；
4. **建栈**：CloudFormation 只建 4 个资源：Runtime 本体、IAM 角色、IAM 策略、元信息；
5. **记录状态**：ARN 和 endpoint 写进 `deployed-state.json`；
6. **打印 endpoint**。

合成这步最能看到 schema-first 的本质。生成的 CDK app 里没有任何项目知识：

```ts
// agentcore/cdk/bin/cdk.ts（生成工程原文）
const configRoot = path.resolve(process.cwd(), '..');
const spec = await configIO.readProjectSpec();             // agentcore.json
const targets = await configIO.readAWSDeploymentTargets(); // aws-targets.json
```

栈名也来自 JSON：`AgentCore-<项目名>-<目标名>`，我的是 `AgentCore-aiauc01-default`。我 grep 过整个生成工程，硬编码名字零命中。**同一份 TypeScript，喂什么 JSON 就合成什么栈。** 这就是 schema-first 的实践形态：cdk/ 是编译器，agentcore.json 是程序。

耗时也交代一下：冷账号首次部署 9 分 49 秒（大头是 CDK 工程的 npm install，221 个包）；只改代码的重部署 26 秒。跑完用 `agentcore status` 验证，看到 `Runtime: READY` 即可。

> **📸 截图位 3 · 首次部署**
> 把你的 `agentcore deploy` 成功输出贴到这里，带栈名和 ARN 那几行。

## 七、Step 4 · 本地先跑一遍

部署前（或者不部署也行），`agentcore dev` 在本地 Uvicorn 起同一个 app、同样的两个路由，模型调用照样走 Bedrock（要凭证，但不用部署）：

```bash
agentcore dev
# 另开一个终端
curl -s -X POST http://localhost:8080/invocations \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"What is 128 plus 256? Use the tool."}'
```

回复以 SSE 流返回，工具调用明晃晃地在里面。我边跑边改 `main.py`，热重载直接生效，不用重启。

> **📸 截图位 4 · 本地运行**
> 把你的 `agentcore dev` 会话贴到这里：server 启动那一行 + curl 的回复。

## 八、Step 5 · 调用线上 Runtime

部署后的 Runtime 走数据面响应。CLI 给了一层友好的封装：

```bash
agentcore invoke --prompt "What is 17 plus 25? Use the tool."
```

实测输出：

```text
I'll use the addition tool to calculate the sum of 17 and 25.

17 plus 25 equals 42.

Session: 53451706-bd56-43f3-84ef-1eceaa3c2aee
To resume: agentcore invoke --session-id 53451706-bd56-43f3-84ef-1eceaa3c2aee
Log: .../agentcore/.cli/logs/invoke/invoke-aia_uc01-20261014-153601.log
```

同样的 prompt 打原始数据面（boto3 `invoke_agent_runtime`），拿到的是 SSE 流，工具调用就明晃晃地在里面：

```text
data: {"event": {"contentBlockStart": {"start": {"toolUse": {"name": "add_numbers"}}, ...}}}
data: {"event": {"contentBlockDelta": {"delta": {"toolUse": {"input": "{\"a\": 11, \"b\": 31}"}}, ...}}}
data: {"event": {"messageStop": {"stopReason": "tool_use"}}}
data: {"event": {"messageStart": {"role": "assistant"}}}
data: {"event": {"contentBlockDelta": {"delta": {"text": "11 plus 31 equals 42."}, ...}}}
data: {"event": {"messageStop": {"stopReason": "end_turn"}}}
data: {"event": {"metadata": {"usage": {"inputTokens": 471, "outputTokens": 9}, "metrics": {"latencyMs": 820}}}}
```

![同一张 HTTP 面孔，两种宿主](images/aws-agentcore-under-the-hood/F5-one-surface.png)

先把这张图的标题说清楚。「同一张面孔」指的是你必须实现的两个路由：`GET /ping` 做健康检查，`POST /invocations` 干活。「两种宿主」指的是同时提供这两个路由的两套环境：本地那套是 `agentcore dev` 起的 Uvicorn 进程，地址 `localhost:8080`；线上那套是 AgentCore 托管的一台 microVM，同一组路由挂在 `https://bedrock-agentcore.<region>.amazonaws.com/runtimes/<runtime-arn>/invocations` 上。路由、扩缩容、TLS 全在平台侧，你的代码不知道自己跑在哪一套里。而 `agentcore invoke` 不是第三种接法，它只是线上这个 `/invocations` 入口的 CLI 客户端，和 boto3 是同一层的东西。

**AgentCore 没有发明新的工具协议，本地和云端用的都是 Bedrock 原生 `toolUse` 协议块。**

花了多少钱？DeepSeek V3.2 在 us-east-1 的价格是输入 $0.62/M、输出 $1.85/M token。一次两轮调用 846 输入 + 82 输出，模型费约 $0.0007，Runtime 计算约 $0.0002。教学级 Agent 的基础设施账单约等于零。

> **📸 截图位 5 · 线上调用**
> 把你的 `agentcore invoke` 回复贴到这里（带 Session ID 的那种）。

## 九、原理深挖 I：入口契约，不是魔法

刨掉工具层，Runtime 对你的代码只发两种请求：`GET /ping` 健康检查，`POST /invocations` 干活。`BedrockAgentCoreApp` 是个薄适配器，把路由接到你写的异步生成器上：

```python
@app.entrypoint
async def invoke(payload, context):
    session_id = getattr(context, "session_id", "default-session")
    agent = get_or_create_agent(session_id)
    async for event in agent.stream_async(prompt):
        yield event
```

（真实代码还会把每个文本增量过一层流式过滤器，见第十一节的故障。）

三个要点：

- **入口是异步生成器**，每个 yield 的 dict 变成一个 SSE 事件。流式是平台的默认形态，不是附加项；
- **`context.session_id` 是你分片状态的钥匙**。每个 session 独立 microVM，扩缩容平台管，你只管按 session 键控状态；
- **模型是个参数**。`MODEL_ID` 是 `agentcore.json` 声明的环境变量，换模型改一个 JSON 值。

## 十、原理深挖 II：trace 里到底记了什么

一次线上 invoke 在 X-Ray 里长这样（`agentcore traces list` 在调用后约 2–3 分钟能看到）：

![一次工具调用的 X-Ray span 树](images/aws-agentcore-under-the-hood/F6-span-tree.png)

```text
invoke_agent Strands Agents              gen_ai.agent.tools=["add_numbers"]  tokens=934
├── execute_event_loop_cycle  (cycle 1)
│   ├── execute_tool add_numbers         gen_ai.tool.status=success  span_kind=TOOL
│   └── chat  deepseek.v3.2 (LLM, 451 tokens)
│       └── BedrockRuntime ConverseStream   finish_reason=tool_use
└── execute_event_loop_cycle  (cycle 2)
    └── chat  deepseek.v3.2 (LLM, 483 tokens)
        └── BedrockRuntime ConverseStream   finish_reason=end_turn
```

不用读框架源码，这棵树就把 Agent Loop 讲明白了：**每轮模型往返一个 cycle，工具调用是 cycle 里独立的 span，第二个 cycle 消费工具结果。**

两个实测出来的坑：

- **span 是异步的**：Transaction Search 要约 10 分钟才能查到，invoke 完立刻 grep CloudWatch 必然失败；
- **本地 dev 的 trace 没有独立 tool span**：工具调用只记在日志里。要在 trace 里断言工具 span，必须打线上。

> **📸 截图位 6 · 可观测**
> 把 CloudWatch GenAI observability 控制台（或 `agentcore traces get` 的输出）贴到这里，要能看到 `execute_tool` 那一层。

## 十一、四个真实故障

- **陈旧的 `cdk.out` 会弄挂下一次 deploy**。CLI 每次 synth 前删 `cdk.out`，残留状态让 synth 报 `Subprocess exited with error 1`。手动跑 `cdk synth` 是通的，说明工程没坏。`rm -rf agentcore/cdk/cdk.out` 解决。把 `cdk.out` 当普通构建产物：随时可删；
- **改名即销毁**。`name` 字段变成 CloudFormation 的 Logical ID，改名不是重命名，是删旧建新；
- **模型往文本通道漏脚手架**。DeepSeek 漏内部模板标记碎片，Nova 漏 `<thinking>` 块。我绕开 Strands 直调 `converse_stream` 验证过，试的四个模型全漏，这是模型行为不是框架 bug。修复在入口处加流式安全的过滤器：按 `messageStart` 为每个 assistant message 重建过滤器，因为一次工具调用其实是多条消息，上一条截断了不能把下一条也静音；
- **区域不是 flag**。所有 `--region` 猜测都报 `unknown option`，targets 文件说了算。

## 十二、带走四句话

1. **JSON 文件就是接口**，其余一切都是它驱动的可再生管道；
2. **CDK 在这里是内置编译器**，你不写 construct、不改生成工程，改 schema 同一份代码编译出不同的栈；
3. **本地和线上共享一个 HTTP 契约**，本地通过的代码上线不需要适配层；
4. **可观测是真的，但异步的**，写测试时给 span 留几分钟。

一句话总结：**在 AgentCore 里，你的基础设施不是你维护的代码，而是编译的代码。**

---

**环境口径**：2026-10-14 实测。AgentCore CLI 0.31.1、Node 22、本地 Python 3.11（运行时目标 `PYTHON_3_13`）、Strands Agents 1.60.0、deepseek.v3.2（us-east-1）、CodeZip 构建（无容器）。部署耗时为冷账号墙钟时间，token 数从 trace span 读出。
