# 待拍板事项台账（OPEN DECISIONS）

> 规则：只增不删；用户拍板后改为「已定：<结论> + 日期」；未拍板前不动相关代码。

## 代码与仓库类（2026-10-14 review 发现）

| # | 事项 | 背景与影响 | 默认建议 | 状态 |
|---|---|---|---|---|
| D1 | 模板补 `agentcore/.gitignore` | `aia.py new` 生成的用例缺这份文件，下一个用例跑完 deploy 再 `git add -A` 会把 `.cache/` 打包暂存和 `.cli/` 日志提交进公开仓库 | 从 CLI 生成的 UC01 版本复制进模板 | 待拍板 |
| D2 | `.env.example` 的 `MODEL_ID` 旧值 | 仍是 `us.anthropic.claude-sonnet-4-5-...`，照文档做的人会直接踩国别政策封锁 | 改为 `deepseek.v3.2` | 待拍板 |
| D3 | 清理三个空目录 `iac/` `scripts/` `diagrams/` | 旧布局残留，`aia.py` 已不创建不引用（`diagrams/` 由 `new` 创建但无人往里放图） | 删除；`diagrams/` 视图形存放方案再定 | 待拍板 |
| D4 | `verify-coverage.py` docstring 与 `capability-map.yaml` 注释过时 | 仍写 `iac/` 目录，代码实际检查 `agentcore/` | 同步改注释 | 待拍板 |
| D5 | `capability-map.yaml` 的 `resource_prefix: aia-` 与实际不符 | 真实命名是 `aia_uc01` / `aiauc01`，资源名不允许连字符 | 改为 `aia_` 并注明连字符限制 | 待拍板 |
| D6 | 根 `.gitignore` 未覆盖 `.idea/` | `git add -A` 会把 IDE 文件带进公开仓库；另有 `.idea/{{UC_SLUG}}.iml` 是模板占位符泄漏痕迹 | 补 `.idea/` 并删除已生成的 IDE 文件 | 待拍板 |
| D7 | uc01 原定两条断言未实现 | 「两个并发 runtimeSessionId 不串上下文」与「命名 endpoint 固定旧版本」在 UC01 近乎恒真或需额外建 endpoint；已把 yaml 对齐为实测实现的三条 + 独立性 | 维持现状，前者留给 UC07、后者视读者价值再定 | 待拍板 |
| D8 | README 与 `deployed-state.json` 含真实账号 ID `123456789012` | 仓库要公开 | README 换 `<your-account-id>`；`deployed-state.json` 是 CLI 生成物，建议连 `.gitignore` 例外一起取消追踪 | 待拍板 |

## 内容生产类（2026-10-15 规划新增）

| # | 事项 | 背景与影响 | 默认建议 | 状态 |
|---|---|---|---|---|
| D9 | 入门篇（A0）结构是否按三幕式重组 | 现有英文初稿是「under the hood」叙事，作为入门篇缺「AgentCore 是什么/不是什么」与「系列预告」两块 | 按三幕式重组，现有 10 节全部保留进新骨架 | 已定：三幕式（2026-10-15） |
| D10 | PPT 的产出形态 | 每篇一份、录视频用，共 8 份 | pptx 文件（16:9），由逐页大纲自动生成 | 已定：pptx 文件（2026-10-15） |
| D11 | 中文稿的形态与发布渠道 | 中文稿面向公众号；英文稿为单一真相源 | 中文稿 = 改写（非逐段对译），公众号版式；发布时英文稿为 canonical | 已定：公众号改写版（2026-10-15） |
| D12 | 图形的存放位置 | 图片目录名 = 文章 slug（skill 规范）；仓库现有 `usecases/*/diagrams/` 空目录 | 放 `articles/images/<slug>/`，SVG 源与 PNG 同目录 | 已定：默认方案随 A0 验证（2026-10-15） |

## 执行顺序（2026-10-15 拍板）

A0 全套先跑通（结构重组、7 图、中文稿、PPT、体检、commit），D1..D8 代码项穿插间隙修。
