# AIBrain · 个人记忆库 + 资料库

> 把「你」写进自己的仓库，平台只是读取方。

一套**平台无关**的个人大脑。所有内容都是纯 Markdown 文件，你自己拥有，任何 AI 都能读。

## 为什么值得用

每个 AI 平台的记忆各自为政：ChatGPT 记不住你在豆包说过的话，WorkBuddy 的 MEMORY.md 也喂不给 Kimi。平台越多，你被切得越碎。这套方案**反转所有权**——把「你」和「你的资料」写进你自己的仓库，平台只负责读。换平台、换工具、换电脑，记忆不丢。

六个具体优势：

1. **数据是你的，不是厂商的。** 就是一堆 `.md` 躺在你自己的文件夹里，没有账号体系、没有订阅、没有找不到的「导出」按钮。
2. **一份档案，全网通用。** ChatGPT、Claude、Gemini、豆包、元宝、Kimi、DeepSeek、WorkBuddy、Cursor 都能读；将来冒出个新 AI，把档案扔给它，不用重新教一遍。
3. **长度自动适配。** 各平台提示词上限差得远（ChatGPT 指令框硬上限 1500 字符，有的只让贴几百字）。一条命令编译出完整 / 精简 / 微版三档，该用哪档用哪档。
4. **记得住「为什么」。** 平台记忆通常只记「用户喜欢 X」，这里额外记决策理由和被否掉的备选——三个月后还能查到当初为什么这么定。
5. **能往里搬，也能整套撤走。** 自带工具扫描本机其他 AI 留下的数据、把别处导出的记忆自动分类合并；不想用了，文件夹拷走或删掉即可，没有任何锁定。
6. **自带本地网页，不用记命令。** 浏览器里就能看全部文件、边改边存、一键编译，比在十几个平台的设置页里翻记忆条目省事。

## 目录结构

```
AIBrain/
├── AGENTS.md            ← 给 AI 读的通用入口（能读文件的 Agent 直接加载它）
├── README.md            ← 你在看的这份
├── memory/              ← 记忆库：关于你的事实、偏好、人和事
│   ├── profile.md          我是谁
│   ├── preferences.md      我的偏好与习惯
│   ├── people.md           重要的人与关系
│   ├── commitments.md      进行中的事
│   ├── decisions.md        已定的决策与理由
│   └── logs/               按天追加的工作日志（不入公开库）
├── knowledge/           ← 资料库：外部知识与你沉淀的资料
│   ├── index.md            资料总索引（AI 先读它再定位）
│   ├── links.md            常用网站与工具
│   ├── work/               工作与项目资料
│   │   ├── projects/           按项目一文件
│   │   ├── templates/          可复用模板
│   │   └── assets/             大文件（图片、SVG 等）
│   └── notes/              个人知识笔记
├── inbox/               ← 收件箱：其他 AI 导出的记忆文本先丢这里，再导入
├── adapters/            ← 对外接口
│   ├── README.md           各平台怎么挂载（ChatGPT / Claude / 豆包 / Cursor …）
│   └── memory-import.md    怎么把其他 AI 的记忆搬进来
├── web/index.html       ← 本地网页界面（左侧文件列表 + 右侧编辑 + 一键编译）
├── tools/
│   ├── sync.py             编译：生成各平台可粘贴的三档版本
│   ├── serve.py            本地服务器：把网页跑起来（默认 127.0.0.1:8420）
│   ├── detect.py           检测本机有哪些 AI 数据可以接入
│   ├── ingest.py           把 inbox/ 里的导出内容合并进记忆库
│   ├── publish_check.py    上架前隐私自检
│   └── make_public.py      一键生成可公开发布的干净包
├── example/             ← 虚构示例（公开模板用，不是你的真实数据）
├── 给AI的指令词.md       ← 发给其他 AI 让它导出记忆的现成提示词
├── PUBLISH.md           ← 上架 GitHub 的完整操作手册
└── dist/                ← 脚本产物（自动生成，不要手改）
```

## 三步上手

1. **填记忆**：打开 `memory/profile.md`，把所有 `TODO` 换成真话。哪怕只填 10 行，效果也是立刻的。
2. **跑编译**：`python tools/sync.py`，在 `dist/` 里生成三档长度的可粘贴版本。
3. **挂平台**：照着 `adapters/README.md`，把对应版本粘到你常用的平台。以后每次更新完记忆，重跑一次脚本即可。

## 一条硬规则

`memory/` 是唯一事实来源。`dist/` 里的东西全是脚本生成的，**永远不要手改**——改了下次编译就没了。

## 每天怎么维护

- **随手记**：冒出「这个要记住」的念头，直接告诉你的 AI，或往 `memory/logs/YYYY-MM-DD.md` 追加一行。
- **定期升格**：日志里反复出现的事，升格进 `preferences.md` 或 `decisions.md`（日志会过时，升格后的才算长期记忆）。
- **资料归档**：新文档丢进 `knowledge/work/` 或 `knowledge/notes/`，同时往 `knowledge/index.md` 补一行索引。

## 用网页界面操作（可选）

不想开编辑器时，用自带的本地网页：左侧列出 `memory/` 与 `knowledge/` 的全部文件，点开即读即改，保存直接写回磁盘，顶栏「编译记忆」一键生成三档。

```bash
python tools/serve.py
# 然后浏览器打开 http://127.0.0.1:8420
```

只用 Python 标准库，零依赖；只绑定本机 127.0.0.1，所有读写路径都被限制在仓库内。

## 接入其他 AI 的记忆

记忆分两类，处理方式完全不同：

- **本机有数据的工具**（WorkBuddy、Cursor、Coze / 豆包桌面客户端等）→ 可以自动检测：
  ```bash
  python tools/detect.py        # 只读扫描，报告写到 inbox/detected.md
  ```
- **纯云端 AI**（豆包 / 元宝 / Kimi / DeepSeek / ChatGPT / Claude / Gemini）→ 记忆存在厂商服务器上，**没有任何本地文件可读**，只能让那个 AI 自己导出来：把 `给AI的指令词.md` 里的提示词发给它，拿到清单存进 `inbox/`。

导入（自动分类合并、整行去重、不覆盖已有内容）：

```bash
python tools/ingest.py --dry-run   # 先预览
python tools/ingest.py            # 正式导入，并自动重跑编译
```

详细流程、各平台操作要点见 `adapters/memory-import.md`。

> ⚠️ 不要把密码、身份证、银行卡、他人隐私粘进 `inbox/`——这些内容会进仓库。

## 同步到其他设备

仓库已经 `git init` 完成。推到一个**私有**仓库（GitHub / Gitee 私有库都行）就能多设备同步：

```bash
cd <你的路径>/AIBrain
git remote add origin <你的私有仓库地址>
git config --local credential.helper <你的凭证助手>
git add -A && git commit -m "init brain"
git push -u origin main
```

配好之后的日常同步，三选一：

1. **双击桌面 `AIBrain 同步到云端.bat`**——最简单，改完双击一下。
2. 命令行：`cd <你的路径>/AIBrain && git add -A && git commit -m "更新" && git push`
3. 手机上编辑：用 GitHub App 或网页版打开私有库，直接改 `memory/` 里的文件并提交；回到电脑 `git pull` 拉下来。

**改了哪一边都要同步**：电脑改了推上去，手机改了拉下来。冲突时先 `git pull --rebase` 再推。

> 这个仓库里会有你的个人偏好和资料，**务必用私有仓库**。

## 开机自动跑网页（可选）

把网页服务设为开机隐藏启动，省得每次敲命令：

- **Windows**：注册表启动项 `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` 加一条，值形如 `"<pythonw.exe 路径>" "<仓库路径>\tools\serve.py"`。用 `pythonw.exe` 启动不会弹黑窗口。
- **macOS / Linux**：写一个 launchd plist 或 systemd user unit，或在桌面环境里加一个开机自启项，命令同样是 `python3 <仓库路径>/tools/serve.py`。

启动后浏览器打开 `http://127.0.0.1:8420`。想临时关掉，在任务管理器里结束 `pythonw.exe` 进程。

## 想公开给别人用？

这个仓库同时就是一套模板。如果你的私人库里已经有真实内容，公开发布前**先把个人记忆剥离出去**（`make_public.py` 只在你自己的私人仓库里才有意义，别人发布的模板包里不含它）：

```bash
python tools/publish_check.py --history   # 自检：个人路径 / 邮箱 / token / 凭证文件
python tools/make_public.py               # 一条命令生成干净的发布包（默认到 ../AIBrain-public）
```

`make_public.py` 会用 `example/` 的虚构内容替换 `memory/`、剔除真实笔记与个人导出、兜底脱敏，并在输出目录自动 `git init` + 首次提交（提交作者用中性占位，不泄露你的邮箱）。它**不会 push**——推送由你自己执行。完整的文件清单、简介文案与命令序列见 `PUBLISH.md`。

## 选配：用 Obsidian 看

这个文件夹本身就是一个合法的 Obsidian 库（vault）。用 Obsidian 打开它，你能得到双链、关系图谱和全文搜索，文件仍然是普通 Markdown。不想装也没关系，记事本足够。
