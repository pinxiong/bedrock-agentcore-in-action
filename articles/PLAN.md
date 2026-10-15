# 内容规划：1 篇入门 + 7 篇用例，每篇三件套（中/英文章 + PPT）

> 状态：规划稿，待用户确认结构后动工。入门篇英文初稿已成（`aws-agentcore-under-the-hood.md`，
> commit `83ea749`），作为 A0 的底稿。
> 台账：待拍板事项见 `OPEN-DECISIONS.md`。

## 1. 八篇总览

| # | slug（图片目录同名） | 对应 | 英文标题（暂定，发布前按张力风格再出选项） | 核心卖点 | 状态 |
|---|---|---|---|---|---|
| A0 | `aws-agentcore-under-the-hood` | 入门（无用例绑定） | How AWS Bedrock AgentCore Actually Works: One JSON File In, Four CloudFormation Resources Out | schema-first 全景 + 底层机制 | 英文初稿 ✅ |
| A1 | `agentcore-first-agent` | UC01 | Your First Bedrock AgentCore Agent: Deployed in 10 Minutes, No Docker | deploy 循环 + 观测闭环 | 计划 |
| A2 | `agentcore-memory` | UC02 | Giving Your Agent a Memory That Survives Cold Starts | Memory | 计划 |
| A3 | `agentcore-gateway-identity` | UC03 | One MCP Gateway for Every Tool Your Agent Does Not Own | Gateway + Identity | 计划 |
| A4 | `agentcore-policy` | UC04 | Least Privilege for Agents: Policy Engines on AgentCore | Policy | 计划 |
| A5 | `agentcore-research-agent` | UC05 | A Research Agent with Web Search, Browser and Code Interpreter | Harness 三件套 | 计划 |
| A6 | `agentcore-quality-loop` | UC06 | Agents That Grade Themselves: Evaluations and Optimization | Evaluations + Optimization | 计划 |
| A7 | `agentcore-multi-agent` | UC07 | Multi-Agent Systems with a Registry: The Full Topology | 多 Agent + Registry | 计划 |

发布节奏：A0 打头立住「原理 + 系列」的心智，A1 之后每完成一个用例发一篇。
番外（Payments）不在 8 篇之列，做完再说。

## 2. 每篇的标准产物（7 件套）

1. **结构卡**：逐节大纲（本规划第 4 节的粒度），先确认再写正文
2. **英文稿**：`articles/<slug>.md`，Hugo front matter（draft: true），单一真相源
3. **中文稿**：`articles/zh/<slug>.md`，公众号版式（改写而非逐段对译），发布时指向英文 canonical
4. **图**：`articles/images/<slug>/`，全英文，SVG 源 + PNG 成品同目录
5. **PPT**：`articles/decks/<slug>.pptx`，16:9，逐页大纲从结构卡直接映射
6. **体检记录**：英文稿过 `en_metrics` + `final_check`；图注/图内/正文三方数字一致
7. **发布记录**：canonical、分发平台、发布日期（发完后回填）

约定：`aia.py new` 以后是否自动盖出该用例的文章骨架（结构卡 + 空 front matter），待 D12 一起定。

## 3. 生产流水线（A0 跑通后复制到 A1..A7）

| 步 | 动作 | 产出 | 质量门 |
|---|---|---|---|
| 1 | 定结构卡（三幕式模板） | 本文档第 4 节粒度的表 | 用户确认 |
| 2 | 收集实测素材 | 用例 README 的真实输出、trace、代码、踩坑 | 数字必须来自本仓库实测 |
| 3 | 写英文稿 | `<slug>.md` | `en_metrics` 六项达标 + `final_check` 0 项 |
| 4 | 画图（全英文 SVG，resvg-py 转 PNG） | `images/<slug>/` | 图注 = 图内 = 正文 |
| 5 | 出中文稿（公众号改写版） | `zh/<slug>.md` | 术语中英对照与英文稿一致 |
| 6 | 生成 PPT | `decks/<slug>.pptx` | 每页一个论点，图复用第 4 步 PNG |
| 7 | 发布检查 | 清单回填 | front matter 无泄漏、og:image、canonical |
| 8 | commit（不 push，push 走发布流程） | git | 单篇一个 commit |

## 4. 入门篇（A0）逐节结构设计

三幕式：**认识它（What）→ 上手它（How）→ 看穿它（Why）**。读者画像：会写 Python、用过 Bedrock、没部署过 agent 平台。

### 第一幕 · 认识它（约 25% 篇幅）

| 节 | 目标 | 素材（实测来源） | 图 | PPT 页 |
|---|---|---|---|---|
| 1. Hook + 一句话定位 | 两个矛盾事实开场：一个 JSON 文件 + 一条命令换来生产级 endpoint；点明本文是系列第 0 篇 | intro 两段（现有稿） | 无 | S1 标题页 / S2 钩子 |
| 2. AgentCore 是什么、不是什么 | 不是新框架，是托管运行时家族；与自管 ECS/Fargate 的对照；一句话带过 14 项能力（详见能力地图，不展开） | 14 项能力清单 | F1 能力地图全景（14 格，本篇只点亮 Runtime/Observability 两格） | S3 是什么/不是什么 |
| 3. 三层心智模型 | 你写代码和两个 JSON；CLI 生成其余；AWS 跑一个 CFN 栈。一条规则：声明在 JSON，生成皆可再生 | 现有稿 mental model + 表格 | F2 三层结构图（现有 widget 图转正式版） | S4 三层模型 |

### 第二幕 · 上手它（约 40% 篇幅）

| 节 | 目标 | 素材 | 图 | PPT 页 |
|---|---|---|---|---|
| 4. 最小项目解剖 | 目录树 + 手写/生成物分色；项目根检测规则（走到 `/`、两者齐备才算项目） | UC01 目录实测 + 检测函数行为 | F3 目录解剖图（手写 vs CLI 生成双色） | S5 目录 / S6 项目根规则 |
| 5. 两个 JSON 的契约 | `agentcore.json` 全文（trimmed）+ `aws-targets.json` 空数组被首次 deploy 回填；无 `--region` | create/deploy 实测 | 无（代码块为主） | S7 契约 |
| 6. deploy 到底做了什么 | 六步流水线；`cdk.ts` 片段；4 个 CFN 资源；首次 9m49s vs 重部 26s | deploy 日志、栈资源统计 | F4 六步流水线图（标注各步耗时与产物） | S8 流水线 / S9 CDK 是编译器 |
| 7. 跑起来：本地与云端 | `agentcore dev` 交互 + boto3 数据面 invoke + SSE 事件流原文；同面结论 | dev/invoke 实测输出 | F5 同一面孔两种宿主（Uvicorn vs microVM） | S10 本地 / S11 云端 invoke |
| 8. 花了什么 | 一次 invoke 的成本拆解 + 时间成本 | $0.0007 + $0.0002、846/82 tokens | 无（数字进正文） | S12 成本 |

### 第三幕 · 看穿它（约 35% 篇幅）

| 节 | 目标 | 素材 | 图 | PPT 页 |
|---|---|---|---|---|
| 9. 入口契约的代码 | `/ping` + `/invocations` 两请求；entrypoint 异步生成器；session/microVM/模型即参数 | main.py 精简版 | 无 | S13 HTTP 契约 |
| 10. 解剖一条 trace | span 树原文 + 如何读出 agent loop 机制；两个坑（异步延迟、本地无 tool span） | X-Ray batch-get-traces 实测 | F6 span 树图（现有文本树转图形） | S14 trace |
| 11. 四个真实故障 | 陈旧 cdk.out / 改名即销毁 / DSML 泄漏 / 区域不是 flag | Troubleshooting 实测 | 无 | S15 故障四连 |
| 12. Takeaways + 系列预告 | 4 条要点 + 金句 + 7 篇路线图（A1..A7 一行一篇） | 现有稿 + 规划第 1 节 | F7 系列路线图（7 格难度阶梯） | S16 takeaways / S17 预告收尾 |

PPT 共约 17 页；F1..F7 共 7 张图，全部英文。

### 现有英文稿到新结构的映射

| 现有节 | 去向 |
|---|---|
| Intro | 第 1 节，补一句系列定位 |
| The mental model | 第 3 节，原样保留 |
| The contract | 第 5 节，原样保留 |
| What deploy actually does | 第 6 节，原样保留 |
| The code side | 第 9 节，位置后移（把「上手」提前，「原理」归拢到第三幕） |
| Local and cloud | 第 7 节，位置前移 |
| The trace | 第 10 节，原样保留 |
| What broke / cost / takeaways / setup | 第 8、11、12 节与文末口径 |

新增缺口（需要新写）：第 2 节「是什么、不是什么」、第 12 节系列预告、全部 7 张图、中文稿、PPT。

## 5. PPT 设计规范

- 16:9；`articles/decks/<slug>.pptx`；每页一个论点，标题即结论（如「CDK 是编译器，JSON 是程序」）
- 页面类型固定五种：标题页 / 论点页 / 代码页 / 图页 / 收尾页，新篇不发明新类型
- 图直接复用文章 PNG（英文），不放中文文字进图
- 代码页字号 ≥ 18pt，每页 ≤ 15 行代码，超出就拆页
- 录制友好：讲稿不进 PPT，放结构卡的「备注」列

## 6. 图形规范（两稿共用）

- 图内文字全英文；中文稿直接复用同一批 PNG
- 每图一个主题色 + 线条分色；SVG 源与 PNG 同存 `articles/images/<slug>/`
- 渲染用 `resvg-py`（本机 qlmanage/headless Chrome/cairo 方案已验证不可用）
- 图注、图内数字、正文口径三方一致（历史上出过事故，列为硬门）

## 7. 发布矩阵

| 语种 | 主阵地 | 分发 | canonical |
|---|---|---|---|
| 英文 | xiongpin.dev（Hugo） | Dev.to、Medium、daily.dev、Hacker News、Lobsters、Reddit | xiongpin.dev 为源 |
| 中文 | 公众号 | 按现有 wechat 流程 | 文首注明英文原文链接 |
| 视频 | 本地录制（PPT + 终端演示） | 后定 | 不适用 |
