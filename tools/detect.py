#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键检测本机有哪些 AI 工具的记忆/资料可以接入 AIBrain。

只读扫描：全程不读取任何被扫描文件的内容、不写入任何被扫描位置。
仅统计「路径 / 类型 / 文件数 / 总大小 / 可提取价值 / 建议动作」。

命中敏感文件名（token/密码/cookie/...）的条目只记录存在、绝不读内容。

用法:
    python tools/detect.py           终端打印摘要表 + 写 inbox/detected.md
    python tools/detect.py --json    只输出机器可读 JSON 到 stdout

扫描位置集中在下方 SCAN_TARGETS / AI_CLIENTS / 等常量，便于扩展。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

# ----------------------------------------------------------------- 基础路径
USER = os.path.expanduser("~")                      # <你的路径>
APPDATA = os.environ.get("APPDATA", "")
LOCALAPPDATA = os.environ.get("LOCALAPPDATA", "")
WB = os.path.join(USER, ".workbuddy")
AIBRAIN = Path(__file__).resolve().parent.parent
INBOX = AIBRAIN / "inbox"

# 敏感关键词：命中文件名/目录名则「只记录存在、绝不读内容、不深入」
SENSITIVE_KEYWORDS = (
    "security", "credential", "token", "secret", "password", "cookie",
    "login", "auth", "key", "db", "sqlite", "session",
)
# 扫描目录时跳过的缓存/噪音子目录（避免无意义的大遍历）
SKIP_DIRS = {"node_modules", "cache", "logs", "log", "__pycache__", "tmp", "temp"}

# 已知 AI 客户端 / 笔记 目录名（在 %APPDATA% 与 %LOCALAPPDATA% 下查找）
AI_CLIENTS = [
    "Doubao", "Coze", "LobsterAI", "QwenWorkCN", "Tencent", "Code",
    "Cursor", "Claude", "ChatGPT", "Kimi", "DeepSeek", "Yuanbao",
    "Baichuan", "ChatGLM", "Wps", "Feishu", "DingTalk", "Notion",
    "Logseq", "Obsidian",
]

# 常见知识库/笔记候选目录
NOTES_CANDIDATES = [
    os.path.join(USER, "Documents", "Notes"),
    os.path.join(USER, "Documents", "笔记"),
    os.path.join(USER, "Documents", "Obsidian"),
    os.path.join(USER, "Obsidian"),
]

# 直接指定的扫描目标：(路径, 类型, 价值, 建议动作, 备注)
# 类型 ∈ 记忆/知识/配置/未知；建议动作 ∈ 直接可导入/需该平台手动导出/跳过
FIXED_TARGETS = [
    (os.path.join(WB, "MEMORY.md"), "记忆", "高", "直接可导入", "WorkBuddy 用户级长期记忆"),
    (os.path.join(WB, "SOUL.md"), "记忆", "低", "跳过", "出厂模板，无真实数据"),
    (os.path.join(WB, "USER.md"), "记忆", "低", "跳过", "出厂模板，无真实数据"),
    (os.path.join(WB, "IDENTITY.md"), "记忆", "低", "跳过", "出厂模板，无真实数据"),
    (os.path.join(USER, ".claude"), "配置", "低", "需该平台手动导出", "Claude CLI/IDE 配置"),
    (os.path.join(USER, ".cursor"), "配置", "低", "需该平台手动导出", "Cursor IDE 配置"),
]


def is_sensitive(name: str) -> bool:
    low = name.lower()
    return any(k in low for k in SENSITIVE_KEYWORDS)


def disp_width(s: str) -> int:
    """显示宽度：CJK 等宽字符算 2。"""
    return sum(2 if ord(ch) > 0x2E80 else 1 for ch in str(s))


def pad(s: str, n: int) -> str:
    return str(s) + " " * max(0, n - disp_width(s))


def scan_dir(root: str, max_depth: int = 3) -> tuple[int, int, bool]:
    """返回 (文件数, 总字节, 是否碰到敏感项)。

    只读元数据（getsепath.getsize），绝不读内容；敏感文件只计数不深入。
    """
    files = 0
    total = 0
    hit_sensitive = False
    try:
        for entry in os.scandir(root):
            if entry.is_dir(follow_symlinks=False):
                if entry.name in SKIP_DIRS or is_sensitive(entry.name):
                    # 敏感目录：不深入，仅记录存在
                    if is_sensitive(entry.name):
                        hit_sensitive = True
                    continue
                if max_depth > 1:
                    f, t, s = scan_dir(entry.path, max_depth - 1)
                    files += f
                    total += t
                    hit_sensitive = hit_sensitive or s
            elif entry.is_file(follow_symlinks=False):
                if is_sensitive(entry.name):
                    hit_sensitive = True
                try:
                    total += entry.stat().st_size
                    files += 1
                except OSError:
                    pass
    except (PermissionError, OSError):
        pass
    return files, total, hit_sensitive


def stat_location(path: str) -> tuple[bool, int, int, bool]:
    """返回 (存在, 文件数, 总大小, 含敏感项)。"""
    if not os.path.exists(path):
        return False, 0, 0, False
    if os.path.isfile(path):
        if is_sensitive(os.path.basename(path)):
            return True, 1, 0, True
        try:
            return True, 1, os.path.getsize(path), False
        except OSError:
            return True, 1, 0, False
    return True, *scan_dir(path)


def human_size(n: int) -> str:
    units = ("B", "KB", "MB", "GB")
    size = float(n)
    for unit in units:
        if size < 1024 or unit == "GB":
            if unit == "B":
                return f"{int(size)}B"
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{int(size)}B"


def find_obsidian_vaults(parents) -> list[str]:
    """在给定父目录下发现含 .obsidian 的知识库（深度≤3）。"""
    vaults: list[str] = []
    for parent in parents:
        if not os.path.isdir(parent):
            continue
        try:
            for entry in os.scandir(parent):
                if entry.is_dir(follow_symlinks=False) and entry.name not in SKIP_DIRS:
                    if os.path.isdir(os.path.join(entry.path, ".obsidian")):
                        vaults.append(entry.path)
        except (PermissionError, OSError):
            pass
    return vaults


def build_targets() -> list[dict]:
    targets: list[dict] = []

    # 1) 固定目标
    for path, typ, val, action, note in FIXED_TARGETS:
        targets.append({"path": path, "type": typ, "value": val,
                        "action": action, "note": note})

    # 2) AppData / LocalAppData 下的 AI 客户端目录
    for base in (APPDATA, LOCALAPPDATA):
        if not base:
            continue
        for name in AI_CLIENTS:
            p = os.path.join(base, name)
            if os.path.isdir(p):
                targets.append({
                    "path": p, "type": "记忆", "value": "中",
                    "action": "需该平台手动导出",
                    "note": f"{name} 客户端数据目录（二进制/缓存为主）",
                })

    # 3) Obsidian 知识库
    for v in find_obsidian_vaults([USER, os.path.join(USER, "Documents")]):
        targets.append({
            "path": v, "type": "知识", "value": "高",
            "action": "需该平台手动导出",
            "note": "Obsidian 知识库（含 .obsidian）",
        })

    # 4) 常见笔记目录
    for p in NOTES_CANDIDATES:
        if os.path.isdir(p):
            targets.append({
                "path": p, "type": "知识", "value": "中",
                "action": "直接可导入",
                "note": "本地笔记目录（纯文本，可直接并入）",
            })
    return targets


def collect() -> list[dict]:
    rows: list[dict] = []
    for t in build_targets():
        exists, files, size, sensitive = stat_location(t["path"])
        if not exists:
            continue
        row = {
            "path": t["path"],
            "type": t["type"],
            "files": files,
            "size": size,
            "size_human": human_size(size),
            "value": t["value"],
            "action": t["action"],
            "note": t["note"],
            "has_sensitive": sensitive,
        }
        rows.append(row)
    return rows


def print_table(rows: list[dict]) -> None:
    headers = ["路径", "类型", "文件数", "总大小", "价值", "建议动作", "备注"]
    widths = [40, 6, 7, 9, 5, 18, 28]
    line = " | ".join(pad(h, w) for h, w in zip(headers, widths))
    print(line)
    print("-" * disp_width(line))
    for r in rows:
        cells = [r["path"], r["type"], str(r["files"]), r["size_human"],
                 r["value"], r["action"], r["note"]]
        if r["has_sensitive"]:
            cells[6] += " [含敏感项·仅记录]"
        print(" | ".join(pad(c, w) for c, w in zip(cells, widths)))
    print()
    print(f"共扫描命中 {len(rows)} 个位置。敏感文件/目录仅记录存在，未读内容。")


def write_report(rows: list[dict]) -> None:
    INBOX.mkdir(parents=True, exist_ok=True)
    out = AIBRAIN / "inbox" / "detected.md"
    lines = [
        f"# 本机 AI 记忆/资料 可接入检测报告",
        "",
        f"> 生成时间：{date.today().isoformat()}　|　只读扫描，未读取任何被扫描文件内容、未写入被扫描位置。",
        f"> 敏感文件名（token/密码/cookie/...）仅记录存在，绝不读内容。",
        "",
        "## 命中位置汇总",
        "",
        "| 路径 | 类型 | 文件数 | 总大小 | 价值 | 建议动作 | 备注 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        note = r["note"] + (" [含敏感项·仅记录]" if r["has_sensitive"] else "")
        lines.append(
            f"| `{r['path']}` | {r['type']} | {r['files']} | "
            f"{r['size_human']} | {r['value']} | {r['action']} | {note} |"
        )
    lines += [
        "",
        "## 下一步",
        "",
        "1. 把各平台导出的记忆文本（或 AI 按提示词生成的自我介绍）存成 `.md`/`.txt` 放进 `inbox/`。",
        "2. 运行 `python tools/ingest.py --dry-run` 预览将要合并的内容。",
        "3. 去掉 `--dry-run` 运行 `python tools/ingest.py` 正式导入。",
        "",
    ]
    out.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"已写入报告: {out}")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="检测本机可接入的 AI 记忆/资料")
    parser.add_argument("--json", action="store_true", help="输出机器可读 JSON 到 stdout")
    args = parser.parse_args()

    rows = collect()
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    print_table(rows)
    write_report(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
