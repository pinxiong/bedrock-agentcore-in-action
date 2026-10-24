# UC05 · Research Agent（托管 Harness 取代手写循环：搜索、浏览、计算，一次交付）

> **Series**: AgentCore in Action（7 个独立用例，难度 D1 到 D5）· **Use case**: 05 · **Difficulty**: **D4** · **Region**: `us-east-1`
> **Verified on**: 2026-10-24/25 · **Cost**: 约 $2（harness + gateway + 导出 runtime，个位数 invoke）· **Time**: 约 150 min
> **Capabilities**: `harness`、`web-search`、`browser`、`code-interpreter`（深挖）· `observability`（spans，附带）
> **Standalone**: yes。这个目录不依赖任何其他用例；`agentcore/cdk/` 是内嵌的部署栈基线。

> 文中的账号 ID 一律脱敏为 `123456789012`；真实输出里出现的是你自己的账号。

---

## 1. 本用例结束时你会看到什么

一句话：一句 prompt 打进托管 harness，span 里同时出现
`execute_tool websearch___WebSearch`（网关 web-search connector）、
`execute_tool browser` ×4（Browser 会话）、`execute_tool code_interpreter`/
`shell`（沙箱计算），沙箱里留下两个真文件——`wind.xlsx`（1806 字节，纯 stdlib
zipfile 拼的 OOXML，CRC 校验通过）和 `wind.png`（16705 字节，800×600 PNG）；
同一 session 中途把模型从 deepseek.v3.2 切到 amazon.nova-lite-v1:0 并重新部署，
追问"最小的份额是多少"原样答出 5.1%，一个工具都没重调；
`agentcore export harness` 导出的 Strands runtime agent 部署后行为一致。

证据（`evidence/`）：`20-invoke-final`（一次调用全文）·
`22-spans-final`（span 清单）· `21-exec-inspect`（`agentcore exec` 进会话 VM
校验两个产物）· `wind.png` / `wind.xlsx`（取回的产物本体）·
`30`/`32`（切模型前后同会话追问）· `33-spans-after-switch`（切换后无新工具
span，`chat deepseek.v3.2` 与 `chat amazon.nova-lite-v1:0` 同 session 共存）·
`40-export`、`41-deploy-export`、`42-invoke-export`（导出与对照）·
`50-tags`（独立性）。

## 2. 前提

| 项 | 要求 | 验证 | 失败修复 |
|---|---|---|---|
| CLI | agentcore 0.31.1 | `agentcore --version` | `npm i -g @aws/agentcore` |
| 区域 | us-east-1（web-search connector 只在此区） | `aws configure get region` | 全部命令显式 `--region us-east-1` |
| 模型 | deepseek.v3.2 与 amazon.nova-lite-v1:0 可用 | 部署后 invoke 即验 | 换可用 `modelId` |
| CDK | agentcore/cdk 有 node_modules | `agentcore deploy` | 在 `agentcore/cdk` 里 `npm install` |
| 权限 | Bedrock/AgentCore 全套 | 部署时报错即缺 | 补 IAM |

## 3. Step 1 · 三个工具资源：网关（web-search）+ harness（browser + code interpreter）

```bash
agentcore add gateway --name research-gateway --protocol-type MCP --authorizer-type NONE
agentcore add gateway-target --name websearch --gateway research-gateway \
  --type connector --connector web-search
agentcore add harness --name research --model-provider bedrock --model-id deepseek.v3.2 \
  --api-format converse_stream --tools agentcore_browser,agentcore_code_interpreter \
  --system-prompt "…" --max-iterations 30 --timeout 900
```

web-search 不在 harness 的 `--tools` 清单里，它以 gateway connector 形态存在
（`connectorId: web-search`），再把整个网关作为 `agentcore_gateway` 工具挂给
harness——网关要先部署一次拿到 ARN：

```bash
agentcore deploy -y --target default        # 首次 2m 22s（evidence/15-deploy-2）
agentcore add tool --harness research --type agentcore_gateway --name websearch \
  --gateway research-gateway --outbound-auth none
agentcore deploy -y --target default        # （evidence/18-deploy-2）
```

If it fails：`agentcore create` 只在全新目录可用；给已有 contract 补 CDK 栈时，
用临时目录 create --no-agent 后把 `agentcore/cdk/` 拷回（node_modules 用
`npm install` 现装）。session id 必须 ≥33 字符，短 id 报 400。

## 4. Step 2 · 一次 prompt，三段 span，两个文件

```bash
agentcore invoke --session-id research-session-0004-artifacts-run --prompt "Produce a short market note on wind power. …"
```

全程 4m 02s。span 清单（`evidence/22`，aws/spans 日志组）：
websearch 1 次 success、browser 4 次 success、code_interpreter 6 次 error
（DeepSeek 的 DSML 函数调用解析不了嵌套 dict 入参）+ shell 11 次 success
（executeCommand 兜底干成了活）。

`agentcore exec` 钉住同一 session 进 VM 验货（`evidence/21`）：

```bash
agentcore exec --harness research --session-id research-session-0004-artifacts-run -- \
  sh -c "ls -la /home && python3 -c \"import zipfile; z=zipfile.ZipFile('/home/wind.xlsx'); print(z.testzip() is None, z.namelist())\""
```

`zip OK, CRC check: True`，五个 OOXML 成员；PNG magic `89504e470d0a1a0a`，
800×600。两个文件用 `base64` 取回本地，就是 `evidence/wind.xlsx` 与
`evidence/wind.png`。

## 5. Step 3 · 会话中途换模型

同一 session 先追问一次（`evidence/30`：India 5.1%），再把
`app/research/harness.json` 的 `modelId` 改成 `amazon.nova-lite-v1:0`，
`agentcore deploy -y --target default`（1m 40s，harness 版本 5），同 session
再问（`evidence/32`）：India 5.1%、wind.xlsx 1806 字节、wind.png 16705 字节
原样背出。span 侧（`evidence/33`）：切换后只有 chat span（
`chat deepseek.v3.2` 与 `chat amazon.nova-lite-v1:0` 同 session 相邻），
没有 execute_tool——答案全部来自对话状态，不是重查的。

## 6. Step 4 · 导出成 Runtime agent

```bash
agentcore export harness --name research --target-agent-name researchAgent
agentcore deploy -y --target default
agentcore invoke --runtime researchAgent --session-id research-session-0006-export-run --prompt "…"
```

导出是 CodeZip 形态：browser 工具被排除（Playwright node driver 跑不了，
EXPORT_NOTES.md 写明，要 Container build 才能带上；本机无 Docker，未验证
Container 路径）。websearch（网关 MCP）与 code interpreter 原样迁过去，
导出 agent 对同一研究问题的行为与 harness 一致（`evidence/42`）。

## 7. 成本

harness runtime（会话时长计费）+ gateway（按请求）+ web-search connector +
导出 runtime。全部流量是个位数 invoke，合计约 $2，拆干净后不再计费。

## 8. 清理

```bash
agentcore remove all -y
agentcore deploy -y --target default      # 把栈 reconcile 成空
agentcore status                          # 应为空
```

注意：`remove all -y` 会清空 `agentcore/agentcore.json` 与
`agentcore/aws-targets.json`，复跑前从 git 恢复。CDK bootstrap 与资产桶
是账号级一次性资源，特意保留。

## 9. 为独立性而内嵌的基线

`agentcore/cdk/`（node_modules 不入库，`npm install` 现装）是内嵌部署栈。
`app/research/` 只有 harness.json 与 system-prompt.md——托管 harness 的意义
正在于没有 agent 循环可写。`app/researchAgent/` 是 `agentcore export` 的
产物，属于本用例自己的资源。

## 10. Going further

- `--memory`、`--session-storage`（EFS/S3 挂载）可让产物与记忆跨会话持久化，
  本例刻意未用（exec 已能取回沙箱文件）。
- Evaluations / Online insights 是 UC06 的主题。
- 难度阶梯：上一档 UC04（边界），下一档 UC06（质量）。
