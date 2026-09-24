#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""识别「模板占位行」——各 AI 应用自带的 USER.md / IDENTITY.md 骨架里的空话。

为什么需要它
------------
`tools/bridge.py pull` 判重靠「字符串相似度」。这类行又短又通用
（`Occupation`、`Pronouns: _(optional)_`、`Bootstrapping a workspace manually`），
在 AIBrain 里当然找不到一模一样的一句，于是被判成「新信息」捞回 inbox；
要真并进记忆库，就是自找污染——记忆里躺着一句「Occupation」毫无意义。

所以必须在**抽取阶段**直接丢掉，而不是指望事后判重。

被丢掉的几类
------------
1. 值里带占位标记：`Pronouns: _(optional)_`
2. 整句就是模板原话：`Bootstrapping a workspace manually`
3. 模板字段行：`Name:` / `Occupation:` / `Timezone:` / `What to call them:` … 
   —— 这类字段的信息不是丢掉，而是**应该写进 `memory/profile.md`**，
   用我们自己的措辞和结构，不复制应用的骨架。

用法：
    from textfilter import is_template_junk
    if is_template_junk(line):
        continue
"""

from __future__ import annotations

import re

# 应用模板里的英文键名；带这些键名的行都是骨架
TEMPLATE_KEYS = {
    "name", "occupation", "pronouns", "city", "timezone", "notes", "context",
    "what to call them", "what should they call you", "their name", "your name",
    "creature", "vibe", "emoji", "summary", "read_when", "path",
}

# 模板里的整句占位话（没有键名的那些）
TEMPLATE_PHRASES = {
    "bootstrapping a workspace manually",
    "fill this in when the moment fits",
    "pick something you like",
    "learn about the person you're helping",
    "the more you know, the better you can help",
    "this is not just metadata it's the start of figuring out who you are",
    "optional",
}

# 值本身是占位符的词（无论键名是什么，这种值都不值得记）
PLACEHOLDER_VALUES = {
    "", "未告知", "待填", "未知", "未定", "无", "unknown", "n/a", "na",
    "none", "tbd", "todo", "-", "—", "_",
}

CJK_RE = re.compile(r"[\u3400-\u9fff\u3000-\u303f\uff00-\uffef]")
KEY_RE = re.compile(r"^([A-Za-z][A-Za-z _'\-]{1,30}?)\s*[:：]\s*(.*)$")
UNDERSCORE_WRAP_RE = re.compile(r"^_.+_$")


def has_cjk(text: str) -> bool:
    """整行是否含中日文（含全角标点）。纯英文的行更可能是模板残留。"""
    return bool(CJK_RE.search(text))


def is_template_junk(line: str) -> bool:
    """这一条是不是应用自带的模板占位行。是 → 丢弃，不要当成候选信息。"""
    s = (line or "").strip().lstrip("-*+ ").strip()
    if not s:
        return True

    low = s.lower().strip(" .。")
    # 1) 整句就是模板原话
    if low in TEMPLATE_PHRASES:
        return True
    # 2) 带占位标记的整句（_(optional)_ / （可选））
    if UNDERSCORE_WRAP_RE.match(s) and not has_cjk(s):
        return True
    if "optional" in low and ("_(optional)_" in low or "(optional)" in low):
        return True

    # 3) 整行就是模板字段名本身（没有冒号也没有值），如 `Occupation`
    if low.strip(" :：") in TEMPLATE_KEYS:
        return True

    # 4) 「英文键: 值」——键名属于模板字段
    m = KEY_RE.match(s)
    if m:
        key = re.sub(r"\s+", " ", m.group(1).strip().lower())
        value = m.group(2).strip()
        if key in TEMPLATE_KEYS:
            return True
        if value.strip("_* ").lower() in PLACEHOLDER_VALUES and not has_cjk(key):
            return True
    return False


if __name__ == "__main__":  # 自测：对着样例看判定结果
    samples = [
        "Bootstrapping a workspace manually",
        "Occupation",
        "Pronouns: _(optional)_",
        "Name: 未告知",
        "What to call them: 主人（明确要求）",
        "Timezone: Asia/Shanghai（本机时区）",
        "称呼：主人（本人明确要求）",
        "Bash 管道会假死，改用 Python",
        "月预算 ≤ 300 元",
    ]
    for x in samples:
        print(f"{'丢弃' if is_template_junk(x) else '保留'}  {x}")
