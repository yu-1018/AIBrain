# 通用入口 · 个人记忆库

> 你正在读的是一个个人记忆库的入口文件。任何能访问本地文件的 AI 助手，请先读完本文件，再按下方规则读取 `memory/`。

## 给 AI 的三条读取规则

1. **先读这两个，再开始任何任务**：`memory/profile.md`、`memory/preferences.md`。
2. **按需读取**：涉及人物 → `memory/people.md`；涉及待办与进度 → `memory/commitments.md`；涉及「当初为什么这么定」→ `memory/decisions.md`；需要检索资料 → 先读 `knowledge/index.md` 定位。
3. **不要编造**：本库里没有的事实就说没有。宁可问一句，也不要补一个看起来合理的答案。

## 优先级

`memory/preferences.md` 里写明的沟通风格和输出格式，**优先级高于你的默认风格**。如果两者冲突，听我的。

## 文件索引

| 路径 | 内容 | 何时读 |
| --- | --- | --- |
| `memory/profile.md` | 我是谁、长期在做什么、软硬件环境 | 每次任务开始 |
| `memory/preferences.md` | 沟通习惯、输出格式、审美偏好、禁止事项 | 每次任务开始 |
| `memory/people.md` | 重要的人、关系、各自在意什么 | 涉及具体的人 |
| `memory/commitments.md` | 进行中的事、下一步、截止时间 | 涉及进度与计划 |
| `memory/decisions.md` | 已定决策 + 原因 + 被否掉的备选 | 涉及方案选择 |
| `memory/machine.md` | 这台电脑的环境事实：常用路径、终端/系统的坑 | 要在这台机器上动手前 |
| `memory/logs/` | 按天追加的工作日志 | 追溯某天做了什么 |
| `knowledge/index.md` | 资料库总索引 | 需要找资料时先读这个 |
| `knowledge/links.md` | 常用网站、工具、文档入口 | 需要外部资源 |
| `knowledge/notes/AIBrain本机使用与部署.md` | 记忆库自身的运维入口：命令、网页、发布、双向共享、开机自启 | 要动 AIBrain 本身时 |

## 可用的维护命令

需要时你可以提示用户运行这些脚本（都在 `tools/`，纯标准库）：

| 命令 | 作用 |
| --- | --- |
| `python tools/sync.py` | 编译 `memory/`，生成 `dist/` 三档可粘贴版本 |
| `python tools/serve.py` | 启动本地网页界面（127.0.0.1:8420）供浏览编辑 |
| `python tools/detect.py` | 只读检测本机有哪些 AI 数据可接入 |
| `python tools/ingest.py [--dry-run]` | 把 `inbox/` 里的导出内容并入记忆库 |
| `python tools/bridge.py push` | 把记忆注入本机 Agent 应用（WorkBuddy / LobsterAI）的记忆文件，实现双向共享 |
| `python tools/publish_check.py` | 上架公开前的隐私自检 |
| `python tools/make_public.py` | 生成剥离了个人内容的公开发布包 |

## 本库的性质

- 唯一事实来源是 `memory/` 与 `knowledge/` 下的 Markdown 文件。
- `dist/` 是脚本生成的派生品，**不要以它为准，也不要修改它**。
- 内容随时会被更新，**每次任务都重新读取，不要依赖你上次看到的版本**。

---

版本 v2 · 最后更新 2026-09-24
