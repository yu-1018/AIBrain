# inbox/ 怎么用

这个目录是用来「收件」的：把你从各个 AI 平台导出的记忆文本，先丢进来，再统一并入 AIBrain。

## 步骤

1. **放文件**：把各平台导出的记忆文本（或让 AI 按提示词生成的「自我介绍 / 记忆备份」）存成 `.md` 或 `.txt`，放进本目录 `inbox/`。
   - 也支持 `.json`（会自动抽取里面的字符串内容）。
   - `detected.md` 和本 `README.md` 不会被导入脚本处理，放心保留。
2. **看有哪些可接入**：运行 `python tools/detect.py`，终端会打印一张本机 AI 工具来源表，并生成 `inbox/detected.md` 报告。
3. **先预览**：运行 `python tools/ingest.py --dry-run`，只打印将要合并到哪些文件、各多少条，不写任何文件。
4. **正式导入**：确认无误后，去掉 `--dry-run` 运行 `python tools/ingest.py`。
   - 以「追加」方式合并，**不覆盖、不删除**已有内容，整行级去重。
   - 每条合并内容带 `<!-- src: 来源文件名 -->` 溯源标记。
   - 导入后自动运行 `tools/sync.py` 重新编译 `dist/`。

## 分类规则（自动）

| 内容关键词 | 并入文件 |
| --- | --- |
| 偏好 / 习惯 / 风格 / 沟通 / 格式 / 语气 | `memory/preferences.md` |
| 城市 / 职业 / 岗位 / 行业 / 环境 / 工具 / 平台 / 邮箱 / 时区 | `memory/profile.md` |
| 同事 / 客户 / 负责人 / 家人 / 朋友 | `memory/people.md` |
| 正在做 / 待办 / 进行中 / 截止 | `memory/commitments.md` |
| 决定 / 选择了 / 原因是 | `memory/decisions.md` |
| 其余 | `knowledge/notes/imported-<日期>.md`（并追加索引） |

## 重要提醒

⚠️ `inbox/` 里会放你的个人数据，**不要提交到公开仓库**。如果仓库根目录的 `.gitignore` 没有包含 `inbox/`，请补上一行（不要覆盖其他已有规则）：

```
inbox/
```
