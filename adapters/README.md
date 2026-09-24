# 各平台怎么挂载

> 不用全挂。**挂你每天真在用的那两三个就够了**，其余按需补。

## 一、先理解三种挂载方式

按优先级从高到低，能用上面的就别用下面的。

| 方式 | 原理 | 优点 | 缺点 | 哪些平台 |
| --- | --- | --- | --- | --- |
| **① 直读文件夹** | Agent 直接访问 `<你的路径>\AIBrain` | 实时，改了立刻生效，零维护 | 需要本地文件访问权限 | WorkBuddy、Cursor、Claude Desktop、Claude Code |
| **② 项目知识库** | 建一个固定的「项目 / 智能体」，把文件传进去 | 一次配置长期生效 | 源文件更新后要重新上传 | ChatGPT、Claude、Gemini、豆包、Kimi、通义 |
| **③ 每次粘贴** | 对话开头把精简版贴进去 | 什么平台都能用 | 手动，容易忘 | DeepSeek 网页版等无自定义能力的平台 |

**结论**：日常主力平台尽量配成 ① 或 ②；③ 只在临时用某个平台时兜底。

## 二、该用哪个版本

`tools/sync.py` 会生成三档，长度递减，内容同源：

| 文件 | 长度 | 用途 |
| --- | --- | --- |
| `dist/portable-full.md` | 完整 | 上传到项目知识库；给能读文件的 Agent |
| `dist/portable-compact.md` | ≤1500 字符 | 粘贴进**有长度限制的指令框**（ChatGPT 项目指令硬上限就是 1500） |
| `dist/portable-micro.md` | ≤500 字符 | 每次对话开头临时粘贴 |

**别把 full 版塞进指令框**——指令太长模型会「看后忘前」，效果反而变差。长内容一律走知识文件。

---

## 三、逐平台配置

### WorkBuddy / CodeBuddy（最省事）

方式 ①。在这个文件夹里开对话，Agent 会自动读到根目录的 `AGENTS.md`。

想让它**所有项目**都带上你的画像，就把 `dist/portable-compact.md` 的内容合并进 `<你的用户目录>\.workbuddy\MEMORY.md`（用户级记忆，跨项目生效）。

### Cursor / Claude Code / Windsurf

方式 ①，但规则文件必须放在**你写代码的那个项目里**，不是放在 AIBrain。

- Cursor：在项目里建 `.cursor/rules/brain.mdc`，内容写「读取 `<你的路径>\AIBrain\AGENTS.md` 并遵守其中的偏好」。
- Claude Code：在项目里建 `CLAUDE.md`，同样只写一行指向 AIBrain 的话。

### Claude（网页版 + 桌面版）

- **桌面版最推荐**：设置 → 连接器（Connectors）→ 装官方的「文件系统」连接器 → 授权 `<你的路径>\AIBrain` 这一个文件夹。之后它就能实时读你的记忆和资料，改完立刻生效。**只授权这一个文件夹**，别把整个用户目录给它。
- **网页版**：侧边栏 Projects → 新建项目 → 项目说明贴 `portable-compact.md` → 项目知识里上传 `portable-full.md`。免费账号最多建 5 个项目，单个文件上限 30MB（我们这点体量远够）。

### ChatGPT

侧边栏 Projects → New project → 三点菜单里的 Project settings → 指令框贴 `portable-compact.md`（上限 1500 字符，正好）→ 项目知识上传 `portable-full.md`。

配额参考：免费账号每项目 5 个文件，Go / Plus 25 个，Pro / Business / Enterprise 40 个，单次最多传 10 个。**只传 `portable-full.md` 一个文件**最省配额。

项目内的指令会覆盖你的全局自定义指令；项目记忆建议设为「仅项目」，避免和账号级记忆打架。

### Gemini

侧边栏 Explore Gems → New Gem → 写指令 + 在 Knowledge 里加文件 → **记得点 Save**（只在预览里试是不保存的，很多人栽在这）。

免费账号就能用 Gems，代价是上下文小（约 32k tokens），所以优先传 `portable-full.md` 的单文件版。

### 豆包 / Kimi / 通义 / 元宝

都是同一个套路：创建一个属于自己的智能体，把 `portable-compact.md` 贴进「人设 / 指令 / 提示词」栏，再把 `portable-full.md` 传进「知识库」。

- 豆包：首页「发现」→ 右上角「创建智能体」→ 填人设与回复逻辑，知识库在「高级技能」里。注意单文件 50MB、知识库总量 100MB 上限。
- Kimi：左侧「Kimi+」→「去创建」→ 人设栏。
- 通义 / 文心：首页「智能体」→「创建智能体」，字段和 ChatGPT 几乎一致，指令内容可以照抄。

### DeepSeek 网页版

没有原生的自定义助手。两个选择：每次对话开头粘 `portable-micro.md`；或者你有编程能力就用 API，把它作为 system message 传进去（这种方式最干净）。

### NotebookLM（只放资料，不放记忆）

它严格只根据你上传的来源回答并给引用，不会瞎编，非常适合当**资料库专用查询台**。把 `knowledge/` 下的文档丢进一个 notebook（最多 50 个来源），问「我之前关于 X 记过什么」，答案必定带出处。

但注意：它**不适合放记忆库**，因为它不会结合外部常识做推理。

---

## 四、改完记忆之后

| 改动 | 要做什么 |
| --- | --- |
| Agent 类工具（WorkBuddy / Cursor / Claude Desktop） | 什么都不用做，实时生效 |
| ChatGPT / Claude / Gemini / 豆包等项目或智能体 | 重跑 `python tools/sync.py`，重新上传 `portable-full.md`，指令框内容没变就不用动 |

## 五、一条安全提醒

上传到云端项目知识库的文件**会一直躺在那个账号里**，而且一旦你分享了项目，对方通常也能读到你的文件和指令。所以：

- `memory/` 里不要写密码、API Key、身份证件、银行卡、未公开的合同原文。
- 涉及他人隐私的信息（同事的健康、薪酬等）不要往 `people.md` 里写。
- 上传前自问一句：**一年后这个文件还躺在这个账号里，我接受吗？**
