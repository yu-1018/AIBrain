#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AIBrain ↔ 本机 Agent 应用 的双向桥。

默认情况下，各个 AI 应用各记各的，**不会自动共享**。
这个脚本是那座桥，只用两个动作就把它们接起来：

    push   把 AIBrain 编译产物（dist/portable-full.md）注入每个应用自己的记忆文件，
           包在 <!-- AIBrain:begin --> ... <!-- AIBrain:end --> 标记里。
           应用下次启动自动读自己的记忆文件 → 就等于读到了 AIBrain。
           可反复重跑：区块内整体替换，不会越滚越长。

    pull   反过来，把应用记忆文件里「AIBrain 还没有」的条目捞成候选清单，
           写进 inbox/（**不自动入库**），人工复核后再决定要不要收进 memory/。

    status 看每个应用接上没有、区块是不是最新的。

用法:
    python tools/bridge.py status
    python tools/bridge.py push              # 注入/更新区块（自动先跑 sync.py）
    python tools/bridge.py push --dry-run    # 只预览，不写任何文件
    python tools/bridge.py push --compact    # 注入精简版（省上下文）
    python tools/bridge.py pull              # 捞候选到 inbox/
    python tools/bridge.py pull --dry-run

想接一个新应用：在下面 APPS 里加一条就行（给出「它启动时必读的记忆文件」路径）。
只依赖 Python 标准库。
"""

from __future__ import annotations

import argparse
import difflib
import os
import re
import shutil
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
INBOX = ROOT / "inbox"
BACKUP = ROOT / ".backup" / "bridge"
SYNC = Path(__file__).resolve().parent / "sync.py"

HOME = Path.home()
APPDATA = Path(os.environ.get("APPDATA", HOME / "AppData" / "Roaming"))

BEGIN = "<!-- AIBrain:begin"
END = "<!-- AIBrain:end -->"
MARK_BANNER = (
    "<!-- AIBrain:begin · 本区块由 tools/bridge.py 自动生成，请勿手改；"
    "改记忆请改 AIBrain 的 memory/ 后重跑 bridge.py push -->"
)

# ------------------------------------------------------------------ 应用清单
# memory_file   : 该应用「每次启动都会读」的记忆文件，桥的注入目标
# extra_sources : pull 时额外扫描的只读来源（应用自己写的档案与每日记录）
APPS: list[dict] = [
    {
        "key": "workbuddy",
        "name": "WorkBuddy",
        "memory_file": HOME / ".workbuddy" / "MEMORY.md",
        "extra_sources": sorted((HOME / "WorkBuddy").glob("*/.workbuddy/memory/*.md"))
        + [HOME / ".workbuddy" / "USER.md"],
        "note": "用户级长期记忆，跨项目每次自动加载",
    },
    {
        "key": "lobsterai",
        "name": "LobsterAI",
        "memory_file": APPDATA / "LobsterAI" / "openclaw" / "state" / "workspace-main" / "MEMORY.md",
        "extra_sources": [
            APPDATA / "LobsterAI" / "openclaw" / "state" / "workspace-main" / "USER.md",
        ]
        + sorted((APPDATA / "LobsterAI" / "openclaw" / "state" / "workspace-main" / "memory").glob("*.md")),
        "note": "主会话启动时加载的长期记忆文件",
    },
]

BULLET_RE = re.compile(r"^\s*[-*+]\s+(.+?)\s*$")
SKIP_LINE_RE = re.compile(r"^\s*(#|>|\||```|\s*$)")


# ------------------------------------------------------------------ 小工具
def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def backup(path: Path, app_key: str) -> Path | None:
    """覆盖别处文件前先留一份，返回备份路径。"""
    if not path.is_file():
        return None
    BACKUP.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dst = BACKUP / f"{app_key}-{path.name}.{stamp}.bak"
    shutil.copy2(path, dst)
    return dst


def strip_own_banner(text: str) -> str:
    """去掉编译产物开头那几行自动生成注释，注入时不需要重复。"""
    lines = text.splitlines()
    while lines and lines[0].lstrip().startswith("<!--"):
        lines.pop(0)
    return "\n".join(lines).strip()


def make_block(digest: str, label: str) -> str:
    body = strip_own_banner(digest)
    return (
        f"{MARK_BANNER}\n"
        f"> 内容来自个人记忆库 AIBrain（唯一事实来源，{label}），最后推送：{date.today().isoformat()}。\n\n"
        f"{body}\n"
        f"{END}\n"
    )


def region_of(text: str) -> tuple[int, int] | None:
    """返回标记区块的 (起, 止) 字符下标；没有标记返回 None。

    只认「整行以标记开头」的行 —— 说明文字里提到标记字样不算，
    否则文档里的一句解释就会被当成区块边界，注入时把正文切碎。
    """
    start = end = None
    pos = 0
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        if start is None:
            if stripped.startswith(BEGIN):
                start = pos
        elif stripped.startswith(END):
            end = pos + len(line.rstrip("\r\n"))
            break
        pos += len(line)
    if start is None or end is None:
        return None
    return start, end


def normalize(line: str) -> str:
    s = line.strip().lstrip("-*+ ").strip()
    s = s.replace("**", "").replace("`", "").replace("　", " ")
    s = re.sub(r"\s+", " ", s)
    return s.strip(" 。，,.;；:")


def corpus_lines() -> list[str]:
    """AIBrain 里所有的记忆与资料文本行，用来判断一条内容是否已经有了。"""
    out: list[str] = []
    for base in (ROOT / "memory", ROOT / "knowledge", ROOT / "example"):
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*.md")):
            out.extend(normalize(ln) for ln in read(p).splitlines() if normalize(ln))
    return [x for x in out if len(x) >= 4]


def source_lines(path: Path) -> list[str]:
    """从一个应用文件里抽取候选条目（跳过标记区块、标题、表格、代码）。"""
    text = read(path)
    reg = region_of(text)
    if reg:
        text = text[: reg[0]] + text[reg[1]:]
    out: list[str] = []
    for raw in text.splitlines():
        if SKIP_LINE_RE.match(raw):
            continue
        m = BULLET_RE.match(raw)
        if not m:
            continue
        s = normalize(m.group(1))
        if 6 <= len(s) <= 300:
            out.append(s)
    return out


# ------------------------------------------------------------------ push
def run_sync() -> None:
    try:
        r = subprocess.run(
            [sys.executable, str(SYNC)], capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
        print(r.stdout.strip() or r.stderr.strip())
    except OSError as exc:  # noqa: BLE001
        print(f"[提醒] 自动编译失败（{exc}），改用已有的 dist/ 产物。")


def cmd_push(args) -> int:
    digest_name = "portable-compact.md" if args.compact else "portable-full.md"
    digest_path = DIST / digest_name
    if not args.dry_run:
        print("先跑 tools/sync.py 刷新编译产物：")
        run_sync()
    if not digest_path.is_file():
        print(f"[停止] 找不到 {digest_path}，请先运行 python tools/sync.py")
        return 1

    digest = read(digest_path)
    block = make_block(digest, "完整版" if not args.compact else "精简版")
    print(f"\n注入内容：{digest_name}（区块 {len(block)} 字符）"
          + ("　[dry-run 不写文件]" if args.dry_run else ""))

    for app in APPS:
        if args.app and app["key"] != args.app:
            continue
        target: Path = app["memory_file"]
        old = read(target)
        reg = region_of(old)
        if reg:
            new = old[: reg[0]] + block + old[reg[1]:].lstrip("\n")
            action = "更新已有区块"
        else:
            new = (old.rstrip() + "\n\n" if old.strip() else "") + block
            action = "新增区块（追加到文件末尾）"
        changed = new != old
        print(f"\n● {app['name']}　{target}")
        print(f"    {action}；文件 {len(old)} → {len(new)} 字符；原有内容全部保留")
        if not changed:
            print("    内容与上次一致，跳过写入")
            continue
        if args.dry_run:
            continue
        if old.strip():
            b = backup(target, app["key"])
            if b:
                print(f"    已备份原文件 → {b}")
        write(target, new)
        print("    已写入")

    if args.dry_run:
        print("\n[dry-run] 没有改动任何文件。")
    else:
        print("\n完成。两个应用下次启动就会读到同一份记忆。")
    return 0


# ------------------------------------------------------------------ pull
def is_duplicate(line: str, known_set: set[str], known: list[str]) -> bool:
    """判断一条候选是不是 AIBrain 里已经有了。

    三道关：完全一样 → 谁包含谁 → 相似度够高（长句标准略宽，因为中文长句
    只要换个标点、多个尾巴，相似度就会掉下来）。
    """
    if line in known_set:
        return True
    ratio_floor = 0.9 if len(line) > 40 else 0.86
    for k in known:
        if abs(len(k) - len(line)) > 25:
            continue
        if len(line) >= 8 and len(k) >= 8 and (line in k or k in line):
            return True
        if difflib.SequenceMatcher(None, line, k).quick_ratio() < ratio_floor:
            continue
        if difflib.SequenceMatcher(None, line, k).ratio() >= ratio_floor:
            return True
    return False


def cmd_pull(args) -> int:
    known = corpus_lines()
    known_set = set(known)
    print(f"AIBrain 现有条目 {len(known)} 条，用来判重。\n")

    blocks: list[tuple[str, Path, list[str]]] = []
    for app in APPS:
        if args.app and app["key"] != args.app:
            continue
        sources: list[Path] = [app["memory_file"]] + list(app["extra_sources"])
        for src in sources:
            if not src.is_file():
                continue
            fresh: list[str] = []
            for line in source_lines(src):
                if len(line) < 8 or is_duplicate(line, known_set, known):
                    continue
                if line in fresh:
                    continue
                fresh.append(line)
            if fresh:
                blocks.append((app["name"], src, fresh))

    total = sum(len(b[2]) for b in blocks)
    if not blocks:
        print("没有捞到新东西——两个应用的记忆基本都已经在 AIBrain 里了。")
        return 0

    out = INBOX / f"from-apps-{date.today().isoformat()}.md"
    lines = [
        f"# 从本机应用捞回的候选条目（{date.today().isoformat()}）",
        "",
        "> 由 `tools/bridge.py pull` 生成。下面是「应用里写过、AIBrain 里还没有」的条目。",
        "> **这些条目没有自动入库**。复核后：有用的复制进 `memory/` 对应文件；",
        "> 或保持本文件在 `inbox/` 里，跑 `python tools/ingest.py` 让脚本分类合并（inbox 不入 git）。",
        "",
    ]
    for app_name, src, fresh in blocks:
        lines.append(f"## 来源：{app_name} · `{src}`")
        lines.append("")
        lines.extend(f"- {x}" for x in fresh)
        lines.append("")

    print(f"共捞到 {total} 条候选：")
    for app_name, src, fresh in blocks:
        print(f"  {app_name} · {src.name}: {len(fresh)} 条")
    if args.dry_run:
        print("\n[dry-run] 未写文件。")
        return 0
    write(out, "\n".join(lines))
    print(f"\n已写入 {out}")
    print("下一步：复核这份清单，把有用的并进 memory/（或跑 python tools/ingest.py）。")
    return 0


# ------------------------------------------------------------------ status
def cmd_status(args) -> int:
    print(f"{'应用':<12}{'记忆文件':<58}{'文件':>7}{'区块':>7}  状态")
    print("-" * 100)
    for app in APPS:
        if args.app and app["key"] != args.app:
            continue
        target: Path = app["memory_file"]
        print(app["name"])
        old = read(target)
        size = len(old) if target.is_file() else 0
        reg = region_of(old)
        blocksize = (reg[1] - reg[0]) if reg else 0
        if not target.is_file():
            state = "尚未接入（跑 push 即可）"
        elif not reg:
            state = "文件在，但没有 AIBrain 区块"
        elif f"最后推送：{date.today().isoformat()}" in old[reg[0]:reg[1]]:
            state = "已接入，且是今天推送的最新版"
        else:
            state = "已接入，区块可能是旧版（记忆改过后跑一次 push）"
        print(f"    {target}")
        print(f"    文件 {size} 字符；区块 {blocksize} 字符；{state}")
        others = [s for s in app["extra_sources"] if s.is_file()]
        if others:
            print(f"    另有 {len(others)} 个可扫描来源（pull 会看）："
                  + "、".join(s.name for s in others[:6])
                  + ("…" if len(others) > 6 else ""))
        print()
    print("说明：push 注入、pull 捞回、status 自查。详见 adapters/双向共享.md")
    return 0


# ------------------------------------------------------------------ 入口
def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass

    ap = argparse.ArgumentParser(description="AIBrain 与本机 Agent 应用的双向桥")
    ap.add_argument("action", choices=["push", "pull", "status"], help="要做的动作")
    ap.add_argument("--app", help="只处理某个应用（workbuddy / lobsterai）")
    ap.add_argument("--compact", action="store_true", help="push 时用精简版（省上下文）")
    ap.add_argument("--dry-run", action="store_true", help="只预览，不写文件")
    args = ap.parse_args()

    if args.app and args.app not in {a["key"] for a in APPS}:
        print("可选的应用：" + "、".join(a["key"] for a in APPS))
        return 2
    return {"push": cmd_push, "pull": cmd_pull, "status": cmd_status}[args.action](args)


if __name__ == "__main__":
    raise SystemExit(main())
