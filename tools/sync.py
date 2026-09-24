#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 memory/ 编译成各平台可直接使用的版本。

用法:
    python tools/sync.py           生成 dist/ 下的三个文件
    python tools/sync.py --check   只检查长度，不写文件

设计原则:
    memory/ 是唯一事实来源，dist/ 全部由本脚本生成，不要手改 dist/。
    不依赖任何第三方库。
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEMORY = ROOT / "memory"
KNOWLEDGE = ROOT / "knowledge"
DIST = ROOT / "dist"

# 编译顺序：(文件名, 在产物里的标题)
SOURCES: list[tuple[str, str]] = [
    ("profile.md", "关于我"),
    ("preferences.md", "我的偏好与习惯"),
    ("people.md", "重要的人与关系"),
    ("commitments.md", "我正在做的事"),
    ("decisions.md", "已定的决策与理由"),
    ("machine.md", "这台电脑的环境事实"),
]

# 各档的字符上限。None = 不限制。
LIMITS: dict[str, int | None] = {
    "portable-full.md": None,
    "portable-compact.md": 1500,
    "portable-micro.md": 500,
}

# 源文件里「写给维护者看」的小节，编译进精简版时整节丢弃。
META_TITLES = {
    "模板", "记录原则", "记录纪律", "写作纪律", "状态取值",
    "命名", "命名与写法", "起手式", "存档规则", "更新记录",
}

BANNER = "<!-- 由 tools/sync.py 自动生成 · 请勿手改，改动请回 memory/ 源文件 -->"
FILLED_NOTE = re.compile(r"\s*[—\-–]\s*已填.*$")  # 内部标记，编译时去掉


# ---------------------------------------------------------------- 文本处理

def read(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _is_row(line: str) -> bool:
    return line.startswith("|")


def _is_sep(line: str) -> bool:
    return set(line.replace("|", "").replace(" ", "")) <= set("-:")


def _heading(line: str) -> tuple[int, str]:
    m = re.match(r"^(#{1,6})\s+(.*)$", line)
    if not m:
        return 0, ""
    return len(m.group(1)), m.group(2).strip()


def drop_own_title(text: str) -> str:
    """去掉源文件自己的 H1，因为产物里会用「## 关于我」这类标题包裹。"""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        level, _ = _heading(line.strip())
        if level == 1:
            del lines[i]
            break
    return "\n".join(lines)


def normalize(text: str, strip_meta: bool = False) -> str:
    """各版本共用的清理：去注释、去「已填」标记；可选地丢弃维护者小节。"""
    out: list[str] = []
    skip_level = 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            out.append("")
            continue
        if line.startswith("<!--"):
            continue
        level, title = _heading(line)
        if level:
            if skip_level and level > skip_level:
                continue
            skip_level = 0
            if strip_meta and title in META_TITLES:
                skip_level = level
                continue
            out.append(line)
            continue
        if skip_level:
            continue
        line = FILLED_NOTE.sub("", line).rstrip()
        out.append(line)
    # 收起多余空行
    result: list[str] = []
    for line in out:
        if line or (result and result[-1]):
            result.append(line)
    return "\n".join(result).strip()


def summarize(text: str, per_section: int = 1) -> str:
    """每个小节只保留前 per_section 条内容，做成精简版。

    表格取「表头 + 第一行数据」；TODO 占位行丢弃；纯空小节整体丢弃。
    """
    out: list[str] = []
    used = 0
    in_table = False
    data_rows = 0

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            in_table = False
            continue
        if line.startswith("#"):
            out.append(line)
            used = 0
            in_table = False
            continue
        if line.startswith(">"):
            continue
        if _is_row(line):
            if not in_table:
                in_table, data_rows = True, 0
                out.append(line)  # 表头先保留，后面若没有数据行再丢
                continue
            if _is_sep(line):
                continue
            data_rows += 1
            if used < per_section and data_rows == 1:
                out.append(line)
                used += 1
            continue
        in_table = False
        content = line.lstrip("-*").strip()
        if not content or content.startswith("TODO") or content.endswith("TODO"):
            continue
        if used < per_section:
            out.append("- " + content)
            used += 1

    # 第二遍：丢掉孤儿表头（前后都没有其他表格行的表格头）
    def _orphan_header(i: int) -> bool:
        if not out[i].startswith("|"):
            return False
        prev_row = i > 0 and out[i - 1].startswith("|")
        next_row = i + 1 < len(out) and out[i + 1].startswith("|")
        return not prev_row and not next_row

    out = [line for i, line in enumerate(out) if not _orphan_header(i)]

    # 第三遍：丢弃没有任何内容的小节
    cleaned: list[str] = []
    for i, line in enumerate(out):
        if line.startswith("#"):
            has_body = False
            for nxt in out[i + 1:]:
                if nxt.startswith("#"):
                    break
                has_body = True
                break
            if not has_body:
                continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def truncate(text: str, limit: int | None) -> str:
    if limit is None or len(text) <= limit:
        return text
    cut = text.rfind("\n", 0, limit - 40)
    if cut < limit // 2:
        cut = limit - 40
    return text[:cut].rstrip() + "\n\n…（内容较长已截断，完整版见记忆库）"


# ---------------------------------------------------------------- 三档产物

def header(title: str, usage: str) -> str:
    return (
        f"{BANNER}\n"
        f"# {title}\n\n"
        f"最后更新：{date.today().isoformat()}　|　{usage}\n"
    )


def source_body(name: str, strip_meta: bool = False) -> str:
    return normalize(drop_own_title(read(MEMORY / name)), strip_meta=strip_meta)


def build_full() -> str:
    parts = [
        header(
            "我的个人档案（完整版）",
            "用途：上传到 AI 的项目知识库，或放在能读文件的 Agent 可访问的目录里。",
        )
    ]
    for name, label in SOURCES:
        body = source_body(name)
        if body:
            parts.append(f"## {label}\n\n{body}")

    index = normalize(drop_own_title(read(KNOWLEDGE / "index.md")))
    if index:
        parts.append(f"## 我的资料库索引\n\n{index}")

    return "\n\n---\n\n".join(parts) + "\n"


def build_compact() -> str:
    parts = [
        header(
            "我的个人档案（精简版）",
            "用途：粘贴进有长度限制的指令框（ChatGPT 项目指令上限 1500 字符）。",
        )
    ]
    for name, label in SOURCES:
        body = summarize(source_body(name, strip_meta=True), per_section=1)
        if body:
            parts.append(f"## {label}\n\n{body}")

    text = "\n\n".join(parts) + "\n"
    return truncate(text, LIMITS["portable-compact.md"])


def build_micro() -> str:
    profile = summarize(source_body("profile.md", strip_meta=True), per_section=1)
    prefs = summarize(source_body("preferences.md", strip_meta=True), per_section=2)
    text = (
        f"{BANNER}\n"
        "# 我的简要背景（贴在对话开头）\n\n"
        f"{profile}\n\n"
        f"{prefs}\n"
    )
    return truncate(text, LIMITS["portable-micro.md"])


# ---------------------------------------------------------------- 入口

def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="编译个人记忆库")
    parser.add_argument("--check", action="store_true", help="只检查长度，不写文件")
    args = parser.parse_args()

    missing = [n for n, _ in SOURCES if not (MEMORY / n).is_file()]
    if missing:
        print("[提醒] 缺少源文件：" + "、".join(missing))

    products = {
        "portable-full.md": build_full(),
        "portable-compact.md": build_compact(),
        "portable-micro.md": build_micro(),
    }

    print(f"{'文件':<24}{'字符数':>8}{'上限':>8}  状态")
    print("-" * 56)
    overflow = False
    for name, text in products.items():
        limit = LIMITS[name]
        n = len(text)
        limit_str = "-" if limit is None else str(limit)
        if limit is not None and n > limit:
            state, overflow = "超限", True
        else:
            state = "正常"
        print(f"{name:<24}{n:>8}{limit_str:>8}  {state}")

    if args.check:
        return 1 if overflow else 0

    DIST.mkdir(exist_ok=True)
    for name, text in products.items():
        (DIST / name).write_text(text, encoding="utf-8", newline="\n")
    print(f"\n已写入 {DIST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
