#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把自己从各 AI 平台导出的记忆文本并入 AIBrain。

只读 inbox/ 下的导出文件，**绝不修改 inbox/ 源文件**；以追加方式合并进
memory/ 与 knowledge/，不覆盖、不删除已有内容，整行级去重。

用法:
    python tools/ingest.py            正式导入（结束后自动运行 sync.py）
    python tools/ingest.py --dry-run  只打印将要做什么，不写任何文件

分类映射：
    偏好/习惯/...   -> memory/preferences.md
    城市/职业/...   -> memory/profile.md
    人/同事/客户/... -> memory/people.md
    正在做/待办/...  -> memory/commitments.md
    决定/选择了/...  -> memory/decisions.md
    其余            -> knowledge/notes/imported-<日期>.md（并追加索引）
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEMORY = ROOT / "memory"
KNOWLEDGE = ROOT / "knowledge"
NOTES = KNOWLEDGE / "notes"
INBOX = ROOT / "inbox"
SYNC = Path(__file__).resolve().parent / "sync.py"

try:
    from textfilter import is_template_junk
except ImportError:  # 只有本脚本被单独拷走时才会发生；降级为不过滤
    def is_template_junk(line: str) -> bool:  # type: ignore[misc]
        return False

# inbox 内不参与导入的文件
SKIP_FILES = {"detected.md", "README.md"}

# 分类关键词（优先级自上而下：先命中先归类）
CAT_PREFERENCE = ["偏好", "习惯", "不喜欢", "喜欢", "风格", "沟通", "格式", "语气", "讨厌", "希望"]
CAT_PROFILE = ["城市", "职业", "岗位", "行业", "环境", "系统", "工具", "平台", "邮箱", "时区",
               "公司", "所在", "地址", "手机", "微信", "操作系统"]
CAT_PEOPLE = ["同事", "客户", "负责人", "家人", "朋友", "领导", "下属", "伴侣", "导师", "对接人"]
CAT_COMMITMENT = ["正在做", "待办", "进行中", "截止", "安排", "计划做", "在做", "任务", "进度"]
CAT_DECISION = ["决定", "选择了", "原因是", "决策", "选型", "采用"]

BULLET_RE = re.compile(r"^[\s]*([-*+]|\d+[.)])\s+(.*)$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
FENCE_RE = re.compile(r"^```")


def classify(text: str) -> str:
    """按内容粗分类，返回目标文件名（不含路径）。

    优先级：偏好 > 进行中/待办 > 决定 > 人 > 档案 > 知识。
    把「城市/工具/平台」等宽泛名词放到靠后，避免抢走动作/关系类信号。
    """
    for kw, name in (
        (CAT_PREFERENCE, "preferences.md"),
        (CAT_COMMITMENT, "commitments.md"),
        (CAT_DECISION, "decisions.md"),
        (CAT_PEOPLE, "people.md"),
        (CAT_PROFILE, "profile.md"),
    ):
        if any(k in text for k in kw):
            return name
    return None  # 落入 knowledge


def extract_entries(text: str) -> list[str]:
    """从文本中抽取事实条目（列表行 + ## 小节下的纯内容行）。"""
    entries: list[str] = []
    current_h2 = None
    in_fence = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = HEADING_RE.match(line)
        if m:
            if len(m.group(1)) == 2:          # 仅跟踪 ## 小节
                current_h2 = m.group(2).strip()
            continue
        if not line.strip():
            continue
        if line.lstrip().startswith(">"):     # 引用说明跳过
            continue
        bm = BULLET_RE.match(line)
        if bm:
            entries.append(bm.group(2).strip())
            continue
        # ## 小节下的普通内容行也算一条
        if current_h2:
            entries.append(line.strip())
    # 过滤过短/占位/模板骨架（见 tools/textfilter.py）
    return [e for e in entries if len(e) >= 2 and not is_template_junk(e)]


def extract_from_json(obj) -> list[str]:
    """递归收集 JSON 里的字符串叶子作为条目。"""
    out: list[str] = []
    if isinstance(obj, dict):
        for v in obj.values():
            out.extend(extract_from_json(v))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(extract_from_json(v))
    elif isinstance(obj, str):
        s = obj.strip()
        if len(s) >= 2:
            out.append(s)
    return out


def read_source(path: Path) -> list[str]:
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8", errors="replace")
    if suffix == ".json":
        try:
            return extract_from_json(json.loads(text))
        except json.JSONDecodeError:
            return extract_entries(text)
    return extract_entries(text)


def existing_lines(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    return {ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()}


def append_block(path: Path, new_entries: list[str], source_name: str,
                 dry_run: bool, existing: set[str]) -> tuple[int, int]:
    """把去重后的新条目追加到 path 末尾，并返回 (新增, 跳过)。"""
    added, skipped = [], 0
    seen = set(existing)
    for e in new_entries:
        key = e.strip()
        if key in seen:
            skipped += 1
            continue
        seen.add(key)
        added.append("- " + e)
    if not added:
        return 0, skipped
    block = "\n".join(added) + f"\n\n<!-- src: {source_name} -->\n"
    if not dry_run:
        with path.open("a", encoding="utf-8") as f:
            f.write("\n" + block if path.stat().st_size else block)
    return len(added), skipped


def append_index_row(date_str: str, dry_run: bool) -> None:
    idx = KNOWLEDGE / "index.md"
    if not idx.is_file():
        return
    lines = idx.read_text(encoding="utf-8").splitlines()
    start = next((i for i, l in enumerate(lines) if l.startswith("## 索引")), None)
    last_pipe = -1
    if start is not None:
        for i in range(start + 1, len(lines)):
            if lines[i].startswith("#"):
                break
            if lines[i].startswith("|"):
                last_pipe = i
    row = (f"| 导入笔记（{date_str}） | `notes/imported-{date_str}.md` | "
           f"由各平台导出文本导入 | {date_str} |")
    if not dry_run:
        if last_pipe >= 0:
            lines.insert(last_pipe + 1, row)
        else:
            lines.append(row)
        idx.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="把 inbox 导出文本并入 AIBrain")
    parser.add_argument("--dry-run", action="store_true", help="只预览，不写文件")
    args = parser.parse_args()
    dry = args.dry_run

    if not INBOX.is_dir():
        print("inbox/ 目录不存在，没有可导入的文件。")
        return 0

    sources = sorted(
        p for p in INBOX.iterdir()
        if p.is_file() and p.suffix.lower() in (".md", ".txt", ".json")
        and p.name not in SKIP_FILES
    )
    if not sources:
        print("inbox/ 下没有待处理的 .md/.txt/.json 文件（已略过 detected.md、README.md）。")
        return 0

    date_str = date.today().isoformat()
    # 收集：来源文件名 -> {目标文件相对名: [条目]}
    plan: dict[str, dict[str, list[str]]] = {}
    for src in sources:
        entries = read_source(src)
        if not entries:
            continue
        buckets: dict[str, list[str]] = {}
        for e in entries:
            target = classify(e) or f"notes/imported-{date_str}.md"
            buckets.setdefault(target, []).append(e)
        plan[src.name] = buckets

    # 打印计划
    print("导入计划" + ("（--dry-run，不写文件）" if dry else "") + "：\n")
    summary: list[dict] = []
    for src_name, buckets in plan.items():
        print(f"● 来源: {src_name}")
        for target, items in buckets.items():
            print(f"    → {target}  ({len(items)} 条候选)")
        summary.append({"source": src_name, "buckets": {t: len(i) for t, i in buckets.items()}})

    if dry:
        print("\n[dry-run] 未写入任何文件。")
        return 0

    # 执行合并
    print("\n开始合并：")
    total_by_target: dict[str, tuple[int, int]] = {}
    for src_name, buckets in plan.items():
        for target, items in buckets.items():
            if target.startswith("notes/"):
                tpath = NOTES / target.split("/", 1)[1]
                tpath.parent.mkdir(parents=True, exist_ok=True)
            else:
                tpath = MEMORY / target
            existing = existing_lines(tpath)
            added, skipped = append_block(tpath, items, src_name, dry, existing)
            prev = total_by_target.get(str(tpath), (0, 0))
            total_by_target[str(tpath)] = (prev[0] + added, prev[1] + skipped)
            print(f"  {src_name} → {tpath.name}: 新增 {added}，跳过 {skipped}")

    # knowledge 索引追加一行（仅当产生了 imported 笔记）
    if any(t.startswith("notes/") for b in plan.values() for t in b):
        append_index_row(date_str, dry)
        print(f"  已为 imported-{date_str}.md 追加索引行到 knowledge/index.md")

    # 摘要
    print("\n合并摘要：")
    for src_name, buckets in plan.items():
        print(f"  来源 {src_name}: " + ", ".join(f"{t}×{n}" for t, n in buckets.items()))
    print("\n各目标文件累计：")
    for tpath, (a, s) in total_by_target.items():
        print(f"  {tpath}: 新增 {a} 行，跳过 {s} 行（整行级去重）")

    # 自动运行 sync.py
    print("\n运行 tools/sync.py：")
    import subprocess
    try:
        res = subprocess.run([sys.executable, str(SYNC)], capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        print(res.stdout)
        if res.stderr:
            print(res.stderr)
        print(f"[sync] 退出码 {res.returncode}")
    except Exception as exc:  # noqa: BLE001
        print(f"[sync] 运行失败: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
