# 一个 JSON 文件进去，四个云资源出来：拆解 AWS Bedrock AgentCore 的底层机制

> 本文是 AgentCore 系列第 0 篇。英文原版（canonical）：*How AWS Bedrock AgentCore Actually Works*，发布于 xiongpin.dev。后续 7 篇每篇拆一个实战用例，从第一个 Agent 一路做到多 Agent 系统。

多数 Agent 部署故事的结局都一样：写 Dockerfile、选实例规格、手工搓 IAM 角色，然后祈祷 YAML 没写错。AWS Bedrock AgentCore 走了另一条路：**整个部署契约就是一个 JSON 文件，一条命令把它变成一个可运行、可观测的线上服务。**

我按这条路部署了一个 Agent，中途搞挂过几次，也把从 JSON 文件到线上 endpoint 之间的每一步都翻了一遍。这篇文章讲的就是中间到底发生了什么。文中所有数据都来自 us-east-1 的真实部署，不是抄文档。

![AgentCore 14 项能力全景](../images/aws-agentcore-under-the-hood/F1-capability-map.png)

## 一、AgentCore 是什么，不是什么

AgentCore 是一组面向 AI Agent 的托管运行时，全家桶共 14 项能力：Runtime、Memory、Gateway、Identity、Policy、Web Search、Browser、Code Interpreter、Observability、Evaluations、Optimization、Payments、Registry 等。本文只点亮其中两格：Runtime 和 Observability，剩下的留给系列后续 7 篇。

**不是什么，比是什么更重要：**

- 不是新的 Agent 框架。你照旧用 Strands、LangChain、OpenAI SDK 或者裸 Python 写 Agent；
- 不是容器编排服务。Runtime 是 serverless 的，每个 session 一个 microVM，扩缩容平台包了；
- 不是模型路由器。你的代码调 Bedrock 的方式和其他任何地方一模一样。

自管过 ECS 或 Fargate 的话，体感差异非常直接：没有 Dockerfile、没有任务定义、没有 target group、没有健康检查配置。Runtime 只要求你的代码提供两个路由，其他全是平台的。

## 二、三层心智模型

**你写 Agent 代码，写两个 JSON 文件，CLI 生成其余一切，AWS 跑一个你永远不用看的 CloudFormation 栈。**

| 层 | 放什么 | 谁维护 |
|---|---|---|
| 你的代码 | `src/` 里的 Agent 入口 | 你 |
| 契约 | `agentcore.json` + `aws-targets.json` | 你，手写 |
| 管道 | `agentcore/cdk/` 下的 CDK 工程 | CLI，每次 deploy 重新生成 |

一条规则解释了绝大部分设计：**声明的都在 JSON 里，CLI 生成的一切都可重新生成。** 这篇文章剩下的部分，就是把这条规则从头到尾走一遍。

## 三、项目目录解剖

一个用例目录长这样：

```
01-first-agent/                 <- 项目根（命令在这里跑）
├── src/                        <- 你的代码
│   ├── main.py                 <- 入口
│   ├── model/load.py           <- 模型加载
│   └── model/sanitize.py       <- 流式过滤器
├── tests/smoke.py              <- 能力断言
├── README.md                   <- 操作文档
└── agentcore/                  <- CLI 工作区
    ├── agentcore.json          ★ 你写：契约
    ├── aws-targets.json        ★ 你写：部署目标
    ├── cdk/                     ⚙ CLI 生成
    ├── .cli/                    ⚙ CLI 运行状态
    └── .cache/                  ⚙ 打包暂存
```

目录分两种颜色：★ 是你的输入，⚙ 是生成物。**永远不要手改 ⚙ 文件**，下一条命令就会覆盖它。

项目根检测规则也值得知道：CLI 从当前目录逐级向上，找到同时包含 `agentcore/` 目录和 `agentcore/agentcore.json` 文件的那一层。两者缺一都不算项目，而报错 `No agentcore project found` 不会告诉你缺的是哪个。

## 四、两个 JSON 的契约

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

`agentcore create` 生成这个文件时所有资源数组都是空的，`agentcore add` 家族的子命令往里塞条目。允许手编，但以官方 schema 为准，CLI 逐字段校验。

第二个文件决定部署到哪：

```json
[{ "name": "default", "account": "123456789012", "region": "us-east-1" }]
```

这里有个反直觉的设计：`create` 只写一个空数组，账号和区域是**首次 `deploy` 时回填的**，CLI 调 STS 查明你的身份再把 target 写回文件。deploy/status/remove 都没有 `--region` 参数，这个文件就是部署位置的唯一真相源。

## 五、deploy 到底做了什么

从 `agentcore deploy` 到 Runtime READY，一共六步：

1. **打包代码**：`src/` 加平台依赖压成一个资产包，我的 Hello World 是 41 MB，本地 `.venv` 被排除。全程没有镜像构建；
2. **合成**：CLI 跑内置的 CDK app，读两个 JSON，产出 CloudFormation 模板到 `cdk.out/`；
3. **上传资产**：zip 进 S3 桶（`cdk bootstrap` 一次性建的）；
4. **建栈**：CloudFormation 只建 4 个资源：Runtime 本体、IAM 角色、IAM 策略、元信息；
5. **记录状态**：ARN 和 endpoint 写进 `deployed-state.json`；
6. **打印 endpoint**。

合成这步最能看到 schema-first 的本质。生成的 CDK app 里没有任何项目知识：

```ts
const configRoot = path.resolve(process.cwd(), '..');
const spec = await configIO.readProjectSpec();             // agentcore.json
const targets = await configIO.readAWSDeploymentTargets(); // aws-targets.json
```

栈名也来自 JSON：`AgentCore-<项目名>-<目标名>`。我 grep 过整个生成工程，硬编码名字零命中。**同一份 TypeScript，喂什么 JSON 就合成什么栈。** 这就是 schema-first 的实践形态：cdk/ 是编译器，agentcore.json 是程序。

耗时也交代一下：冷账号首次部署 9 分 49 秒（大头是 CDK 工程的 npm install，221 个包）；只改代码的重部署 26 秒。

## 六、跑起来：本地和云端一个面孔

`agentcore dev` 在本地 Uvicorn 起同一个 app、同样的两个路由，模型调用照样走 Bedrock（要凭证，但不用部署）。我边跑边改 `main.py`，热重载直接生效。同样的 prompt 打线上 Runtime 也通，因为契约在两边完全一致。boto3 走数据面：

```python
agentcore = boto3.client("bedrock-agentcore")
resp = agentcore.invoke_agent_runtime(
    agentRuntimeArn="arn:aws:bedrock-agentcore:...",
    payload=json.dumps({"prompt": "What is 17 plus 25?"}).encode(),
)
```

响应是 SSE 流，工具调用就明晃晃地在里面：`contentBlockStart` 带原生 `toolUse` 块，`messageStop` 的 `stopReason=tool_use`，然后第二条消息给出 `17 plus 25 equals 42.`。**AgentCore 没有发明新的工具协议，用的就是 Bedrock 原生协议块。**

成本方面：DeepSeek V3.2 输入 $0.62/M、输出 $1.85/M token，一次两轮调用 846 输入 + 82 输出，模型费约 $0.0007，Runtime 计算约 $0.0002。教学级 Agent 的基础设施账单约等于零。

## 七、入口契约：不是魔法

刨掉工具层，Runtime 对你的代码只发两种请求：`GET /ping` 健康检查，`POST /invocations` 干活。`BedrockAgentCoreApp` 是个薄适配器，把路由接到你写的异步生成器上：

```python
@app.entrypoint
async def invoke(payload, context):
    session_id = getattr(context, "session_id", "default-session")
    agent = get_or_create_agent(session_id)
    async for event in agent.stream_async(prompt):
        yield event
```

三个要点：

- **入口是异步生成器**，每个 yield 的 dict 变成一个 SSE 事件。流式是平台的默认形态，不是附加项；
- **`context.session_id` 是你分片状态的钥匙**。每个 session 独立 microVM，扩缩容平台管，你只管按 session 键控状态；
- **模型是个参数**。`MODEL_ID` 是 `agentcore.json` 声明的环境变量，换模型改一个 JSON 值。

## 八、解剖一条 trace

一次线上 invoke 在 X-Ray 里长这样：

```
invoke_agent  Strands Agents               934 tokens
├── execute_event_loop_cycle               cycle 1
│   ├── execute_tool  add_numbers          TOOL, status=success
│   └── chat  deepseek.v3.2                finish_reason=tool_use
└── execute_event_loop_cycle               cycle 2
    └── chat  deepseek.v3.2                finish_reason=end_turn
```

不用读框架源码，这棵树就把 Agent Loop 讲明白了：**每轮模型往返一个 cycle，工具调用是 cycle 里独立的 span，第二个 cycle 消费工具结果。**

两个实测出来的坑：

- **span 是异步的**：Transaction Search 要约 10 分钟才能查到，invoke 完立刻 grep CloudWatch 必然失败；
- **本地 dev 的 trace 没有独立 tool span**：工具调用只记在日志里。要在 trace 里断言工具 span，必须打线上。

## 九、四个真实故障

- **陈旧的 `cdk.out` 会弄挂下一次 deploy**。CLI 每次 synth 前删 `cdk.out`，残留状态让 synth 报 `Subprocess exited with error 1`。手动跑 `cdk synth` 是通的，说明工程没坏。`rm -rf agentcore/cdk/cdk.out` 解决。把 `cdk.out` 当普通构建产物：随时可删；
- **改名即销毁**。`name` 字段变成 CloudFormation 的 Logical ID，改名不是重命名，是删旧建新；
- **模型往文本通道漏脚手架**。DeepSeek 漏内部模板标记碎片，Nova 漏 `<thinking>` 块。我绕开 Strands 直调 `converse_stream` 验证过，试的四个模型全漏，这是模型行为不是框架 bug。修复在入口处加流式安全的过滤器；
- **区域不是 flag**。所有 `--region` 猜测都报 `unknown option`，targets 文件说了算。

## 十、带走四句话

1. **JSON 文件就是接口**，其余一切都是它驱动的可再生管道；
2. **CDK 在这里是内置编译器**，你不写 construct、不改生成工程，改 schema 同一份代码编译出不同的栈；
3. **本地和线上共享一个 HTTP 契约**，本地通过的代码上线不需要适配层；
4. **可观测是真的，但异步的**，写测试时给 span 留几分钟。

一句话总结：**在 AgentCore 里，你的基础设施不是你维护的代码，而是编译的代码。**

## 系列预告

本篇覆盖 Runtime 和 Observability。后续 7 篇逐个点亮剩余能力，难度递增：A1 第一个 Agent、A2 Memory、A3 Gateway + Identity、A4 Policy、A5 研究型 Agent（Web Search + Browser + Code Interpreter）、A6 自评自优（Evaluations + Optimization）、A7 多 Agent + Registry。每篇同一配方：真实部署、实测输出、以及所有教会我东西的故障。

---

**环境口径**：AgentCore CLI 0.31.1、Strands Agents 1.60.0、Python 3.13、deepseek.v3.2（us-east-1）、CodeZip 构建（无容器）。部署耗时为冷账号墙钟时间，token 数从 trace span 读出。
