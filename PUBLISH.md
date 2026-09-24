# PUBLISH.md · AIBrain 上架到 GitHub 操作手册

本仓库是你的个人记忆库 + 资料库模板。上架公开前请先读这份手册，避免把个人内容泄露出去。

## 一、发布什么

**核心原则：公开仓库不应包含你的个人记忆。** `memory/` 写的是「你是谁」，`knowledge/notes/`、`knowledge/work/` 多为真实项目与笔记，都不该对外。

两种方案：

### 方案 A（推荐）：只发布模板 —— 一条命令

```bash
python tools/make_public.py
```

脚本会自动在 `../AIBrain-public` 生成一个干净的、可直接推送的发布包，它做这些事：

1. `memory/` → 用 `example/` 的虚构内容替换（不复制你的真实记忆）
2. `knowledge/` → 只保留索引、链接与模板，真实笔记不复制
3. 排除 `dist/`、`memory/logs/`、`inbox/` 个人导出、`.git/`
4. 兜底脱敏：把残留的个人路径、邮箱替换成占位符
5. 在输出目录自动 `git init` + 首次提交（提交邮箱用中性占位，不泄露你自己的）
6. 跑一遍模板模式自检，并打印推送命令

生成后**不会 push**，你只需加远端再推送。常用参数：`--out <目录>` 换输出位置，`--no-git` 只生成文件，`--force` 重新生成（仅对脚本自己生成过的目录生效）。

### 方案 B：保留个人内容，用私有仓库

仓库设为 Private，只同步给自己，**绝不对外**。

### 手动做法（不用脚本时）

把 `example/` 五个文件复制为 `memory/` 同名占位；删除 `knowledge/notes/` 下真实笔记与 `knowledge/work/projects/` 下真实项目文件；清空 `memory/logs/` 与个人 `inbox/` 导出。

### 文件清单

应包含（通用 / 模板）文件：
```
README.md  README.en.md  LICENSE  .gitignore  .gitattributes  AGENTS.md  PUBLISH.md
给AI的指令词.md
adapters/README.md  adapters/memory-import.md
tools/sync.py  tools/serve.py  tools/detect.py  tools/ingest.py  tools/publish_check.py
web/index.html
example/profile.md  example/preferences.md  example/people.md  example/commitments.md  example/decisions.md
knowledge/index.md  knowledge/links.md  knowledge/notes/README.md
knowledge/work/projects/README.md  knowledge/work/templates/project.md
inbox/README.md
```

应排除（个人 / 产物）文件：
```
memory/                                     # 全部个人记忆（profile/preferences/people/commitments/decisions + logs/）
knowledge/notes/*.md                        # 真实知识笔记（个人整理的主题笔记）
knowledge/work/projects/*.md                # 真实项目资料
inbox/*                                     # 个人导出数据（保留 inbox/README.md 使用说明）
dist/*                                      # 脚本产物（已被 .gitignore 忽略）
tools/__pycache__/                          # 已被 .gitignore 忽略
tools/make_public.py                        # 发布工具本身，公开包不需要
```

## 二、上架前必做

在仓库根目录运行自检脚本，处理所有「高危」项（个人路径、邮箱、token、凭证文件名等）：
```bash
python tools/publish_check.py
python tools/publish_check.py --history
```
- 两命令均退出码 `0` 才干净（有高危项退出码为 `1`）。
- `--history` 额外扫 git 历史文件名，防「曾提交后删除」的隐私残留。
- 高危必须修；中危（个人记忆/笔记目录）请确认你选了方案 A（已剔除）。
- 在**发布的模板包**里检查时加 `--template`：目录级判断降级为提示，只保留文件级实证风险（否则 `memory/` 里的虚构示例也会被当成个人内容报警）。`make_public.py` 已自动用这个参数。

## 三、可直接复制的仓库简介文案

GitHub Description（一行，≤120 字符）：
```
中文：平台无关的个人记忆库+资料库：纯 Markdown、数据自有、可被任何 AI 读取，一键编译成各平台可粘贴版本。
英文：A platform-agnostic personal memory & knowledge base: pure Markdown, you own the data, any AI can read it, one-click compile to paste-ready versions.
```

About 区 Topics 标签（8–12 个）：
```
ai-memory, personal-knowledge-base, markdown, agents-md, second-brain, obsidian, claude, chatgpt, privacy-first, llm-tools, knowledge-management, self-hosted
```

README 顶部 slogan + 项目定位段：
```
中文 slogan：把「你」写进自己的仓库，平台只是读取方。
英文 slogan：Put "you" in your own repo — platforms are just readers.
定位段：AIBrain 是一套平台无关的个人大脑模板：所有内容都是纯 Markdown 文件，你完全拥有数据，不绑定任何厂商。任何能读文件的 AI（ChatGPT、Claude、豆包、WorkBuddy、Cursor 等）都能直接加载，换平台记忆不丢。内置 tools/sync.py 可一键把你的记忆编译成完整版 / 精简版 / 微版三种长度，直接粘贴到各平台。你只需维护自己的仓库，其余交给脚本。
```

## 四、命令序列

### 方案 A（发布包已在 `../AIBrain-public`，脚本已完成 init 与首次提交）

```bash
cd ../AIBrain-public
git remote add origin https://github.com/<你的用户名>/AIBrain.git
git push -u origin main
```
> 推送前若又改了内容，先 `git add -A && git commit -m "..."`，再重跑 `python tools/publish_check.py --template` 确认干净。
> 提交作者是脚本写入的中性占位（`AIBrain <noreply@example.com>`），你自己的邮箱不会进公开历史。

### 方案 B（直接在私人仓库里操作）

```bash
# 1. 关联远端（换成你自己的仓库地址）
git remote add origin https://github.com/<你的用户名>/AIBrain.git
# 2. 暂存（.gitignore 已忽略 dist/、memory/logs/、inbox/*、__pycache__）
git add -A
# 3. 提交
git commit -m "AIBrain: init (platform-agnostic personal brain)"
# 4. 统一定为 main 再推送
git branch -M main
git push -u origin main
```
> 若 `git remote add` 提示已存在，用 `git remote set-url origin <新地址>` 修改。私有仓库请在 GitHub 上把可见性设为 Private 再推送。

## 五、发布后可选

可加一个 GitHub Actions 做 Markdown lint（如 `markdownlint`），在每次 push 时自动检查格式。
