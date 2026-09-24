#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AIBrain 上架前自检脚本 (纯 Python 标准库)。

扫描 git 已跟踪的文件（失败则回退为遍历目录并跳过 .gitignore 条目），
可选扫描 git 历史中的文件名，分级检测个人/隐私/凭证泄露风险，
帮助你在把仓库公开到 GitHub 之前发现问题。

用法:
    python tools/publish_check.py
    python tools/publish_check.py --history      # 额外检查 git 历史里的文件名
    python tools/publish_check.py --repo <路径>   # 指定仓库根目录

退出码:
    存在任意「高危」项 -> 1
    否则               -> 0
"""

import argparse
import os
import re
import subprocess
import sys

HIGH = "高危"
MED = "中危"
INFO = "提示"

# ---------------------------------------------------------------------------
# 风险正则
# ---------------------------------------------------------------------------
RE_PERSONAL_PATH = re.compile(
    r'(?:[A-Za-z]:\\Users\\[^\\ \r\n]+|/Users/[^/ \r\n]+|/home/[^/ \r\n]+)',
    re.IGNORECASE,
)
RE_EMAIL = re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}')
# 保留域名（RFC 2606 / RFC 6761）：文档与示例专用，不可能是真实个人信息
EMAIL_SAFE_DOMAINS = (
    "example.com", "example.org", "example.net", "example.edu",
    "localhost", "invalid", "test",
)
RE_TOKEN = re.compile(
    r'(?:'
    r'sk-[A-Za-z0-9]{16,}|'
    r'ghp_[A-Za-z0-9]{16,}|'
    r'gho_[A-Za-z0-9]{16,}|'
    r'ghu_[A-Za-z0-9]{16,}|'
    r'ghs_[A-Za-z0-9]{16,}|'
    r'ghr_[A-Za-z0-9]{16,}|'
    r'AKIA[0-9A-Z]{16,}|'
    r'Bearer\s+[A-Za-z0-9._\-]+|'
    r'(?:api[_-]?key|secret|access[_-]?key|token|password|passwd)\s*[:=]\s*["\']?[^\s"\']{8,}'
    r')',
    re.IGNORECASE,
)
# 凭证文件名（高危，文件名即可判定）
RE_CRED_FILE = re.compile(
    r'(^|[/\\])'
    r'(\.env(\.[A-Za-z0-9]+)?|'
    r'credentials(\.[A-Za-z0-9]+)?|'
    r'secrets(\.[A-Za-z0-9]+)?|'
    r'id_rsa|id_dsa|id_ecdsa|id_ed25519|'
    r'.*\.pem|.*\.key|.*\.p12|.*\.pfx|.*\.keystore)$',
    re.IGNORECASE,
)
# 中危：example 之外疑似真实人名/公司名/手机号（高信号，避免产品名误报）
RE_PHONE = re.compile(
    r'(?<!\d)(?:\+?\d{1,3}[\-\s]?)?'
    r'(?:1[3-9]\d{9}|\d{3,4}[\-\s]?\d{3,4}[\-\s]?\d{4})(?!\d)'
)
RE_CN_NAME = re.compile(r'[\u4e00-\u9fa5]{2,4}(?:先生|女士|老师|同学|经理|总监)')
# 职衔常见搭配（不是真实姓名），如「产品经理」「项目经理」「技术总监」
NAME_STOPWORDS = (
    "产品", "项目", "客户", "销售", "市场", "技术", "运营", "研发", "设计",
    "财务", "人事", "部门", "团队", "公司", "高级", "资深", "见习", "实习",
)
RE_CN_PRIV = re.compile(r'(?:微信|手机号|身份证|住址|家庭地址|银行卡|社保|护照|公积金)')

# 本检测器自身不参与内容扫描：文件里写着上面这些正则的源码，扫自己必然自我误报
SKIP_CONTENT = {"tools/publish_check.py"}


# ---------------------------------------------------------------------------
# git / 目录 列举
# ---------------------------------------------------------------------------
def default_repo():
    # 脚本位于 <repo>/tools/publish_check.py
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(here)


def git_tracked_files(repo):
    """返回已跟踪文件相对路径列表；失败返回 None（调用方回退）。"""
    try:
        out = subprocess.run(
            ["git", "-C", repo, "ls-files"],
            capture_output=True, text=True, check=True,
        ).stdout
    except Exception:
        return None
    return [l for l in out.splitlines() if l.strip()]


def git_history_files(repo):
    """返回 git 历史中出现过的所有文件名（不读内容）。失败返回 []。"""
    try:
        out = subprocess.run(
            ["git", "-C", repo, "log", "--all", "--name-only", "--pretty=format:"],
            capture_output=True, text=True, check=True,
        ).stdout
    except Exception:
        return []
    files = set()
    for line in out.splitlines():
        line = line.strip()
        if line:
            files.add(line)
    return sorted(files)


def parse_gitignore(repo):
    """解析 .gitignore，返回规则列表 [(negated, is_dir, pattern)]。"""
    gi = os.path.join(repo, ".gitignore")
    rules = []
    if not os.path.isfile(gi):
        return rules
    with open(gi, encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            negated = line.startswith("!")
            if negated:
                line = line[1:]
            if line.startswith("/"):
                line = line[1:]
            is_dir = line.endswith("/")
            line = line.rstrip("/")
            rules.append((negated, is_dir, line))
    return rules


def _match_rule(rel, negated, is_dir, pat):
    import fnmatch
    if "/" in pat:
        # 锚定到仓库根
        if is_dir:
            return rel == pat or rel.startswith(pat + "/")
        return rel == pat
    # 无斜杠：匹配任意层级
    if fnmatch.fnmatch(os.path.basename(rel), pat):
        return True
    if is_dir:
        return (
            rel == pat
            or rel.startswith(pat + "/")
            or ("/" + pat + "/") in ("/" + rel + "/")
            or rel.endswith("/" + pat)
        )
    return False


def is_ignored(rel, rules):
    ignored = False
    for negated, is_dir, pat in rules:
        if _match_rule(rel, negated, is_dir, pat):
            ignored = not negated
    return ignored


def fallback_walk(repo):
    """git 不可用时的回退：遍历目录并跳过 .gitignore 命中项。"""
    rules = parse_gitignore(repo)
    result = []
    for root, dirs, files in os.walk(repo):
        rel_root = os.path.relpath(root, repo).replace(os.sep, "/")
        if rel_root == ".":
            rel_root = ""
        # 修剪被忽略的目录
        kept_dirs = []
        for d in dirs:
            rel = (rel_root + "/" + d) if rel_root else d
            if not is_ignored(rel, rules) and d != ".git":
                kept_dirs.append(d)
        dirs[:] = kept_dirs
        for fn in files:
            rel = (rel_root + "/" + fn) if rel_root else fn
            if is_ignored(rel, rules):
                continue
            result.append(rel)
    return sorted(result)


# ---------------------------------------------------------------------------
# 检测逻辑
# ---------------------------------------------------------------------------
def folder_medium_reason(rel):
    """非 example 的个人内容目录 -> 中危理由。"""
    if rel.startswith("memory/"):
        return "memory/ 下为个人记忆内容，公开仓库不应包含"
    if rel.startswith("knowledge/notes/"):
        return "knowledge/notes/ 下为个人知识笔记，可能含真实项目/人名"
    if rel.startswith("knowledge/work/"):
        return "knowledge/work/ 下为个人/工作项目资料，可能含真实信息"
    return None


def only_placeholder_emails(line):
    """整行里的邮箱是否全是保留域名（示例占位），没有任何真实邮箱。"""
    for m in RE_EMAIL.finditer(line):
        dom = m.group(0).rsplit("@", 1)[-1].lower()
        if not any(dom == d or dom.endswith("." + d) for d in EMAIL_SAFE_DOMAINS):
            return False
    return True


def scan_content(rel, text):
    """逐行内容扫描，返回 findings 列表 [(severity, reason, rel, line, snippet)]。"""
    findings = []
    in_example = rel.startswith("example/")
    for i, line in enumerate(text.splitlines(), 1):
        snip = " ".join(line.split())[:60]
        if RE_PERSONAL_PATH.search(line):
            findings.append((HIGH, "个人路径硬编码", rel, i, snip))
        if RE_EMAIL.search(line) and not only_placeholder_emails(line):
            findings.append((HIGH, "邮箱地址", rel, i, snip))
        if RE_TOKEN.search(line):
            findings.append((HIGH, "疑似 token/密钥/密码串", rel, i, snip))
        if in_example:
            continue
        if RE_PHONE.search(line):
            findings.append((MED, "疑似真实手机号", rel, i, snip))
        # 代码行（正则定义 / 注释 / 关键词表）不参与隐私词判断，否则会把
        # 「提醒别人不要写身份证号」这类文案误报成泄露
        if line.lstrip().startswith("#") or "re.compile(" in line:
            continue
        m_name = RE_CN_NAME.search(line)
        if m_name and not any(m_name.group(0).startswith(w) for w in NAME_STOPWORDS):
            findings.append((MED, "疑似真实人名", rel, i, snip))
        elif RE_CN_PRIV.search(line) and re.search(r"\d", line):
            findings.append((MED, "疑似隐私词+数字", rel, i, snip))
    return findings


def file_level_high(rel):
    """文件名层面的高危判定（不读内容）。"""
    findings = []
    # inbox 下非 README 的个人导出
    if rel.startswith("inbox/") and rel != "inbox/README.md":
        findings.append((HIGH, "inbox/ 下个人导出文件", rel, 0, "(文件名)"))
    # 凭证文件名
    if RE_CRED_FILE.search(rel.replace("\\", "/")):
        findings.append((HIGH, "凭证/密钥文件名", rel, 0, "(文件名)"))
    return findings


def snippet_of(text, line_no):
    """（保留备用）按行号取片段并截断 60 字符。"""
    if line_no and line_no > 0:
        try:
            line = text.splitlines()[line_no - 1]
        except IndexError:
            line = ""
    else:
        line = ""
    return " ".join(line.split())[:60]



# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="AIBrain 上架前隐私自检")
    ap.add_argument("--repo", default=default_repo(), help="仓库根目录")
    ap.add_argument("--history", action="store_true", help="额外检查 git 历史文件名")
    ap.add_argument(
        "--template", action="store_true",
        help="按公开模板包检查（memory/ 内为虚构示例）：目录级中危降级为提示，只保留文件级实证风险",
    )
    args = ap.parse_args()

    repo = os.path.abspath(args.repo)
    if not os.path.isdir(repo):
        print("错误：仓库目录不存在: %s" % repo)
        return 2

    # 1) 收集文件
    tracked = git_tracked_files(repo)
    if tracked is None:
        print("提示：git ls-files 不可用，回退为目录遍历（遵循 .gitignore）。")
        tracked = fallback_walk(repo)
    tracked_set = set(tracked)

    history_set = set()
    if args.history:
        history_set = set(git_history_files(repo))

    all_files = sorted(tracked_set | history_set)

    findings = []
    for rel in all_files:
        rel_n = rel.replace("\\", "/")
        on_disk = os.path.isfile(os.path.join(repo, *rel_n.split("/")))

        # 文件名层面高危（历史与当前都检查）
        findings.extend(file_level_high(rel_n))

        is_tracked = rel_n in tracked_set
        # 中危：个人内容目录（历史与当前都标记）
        # 模板包里这些目录装的是虚构示例，目录级判断降级为提示
        fmr = folder_medium_reason(rel_n)
        if fmr:
            findings.append((INFO if args.template else MED, fmr, rel_n, 0, "(目录)"))

        # 内容扫描仅对当前已跟踪且盘上存在的文件
        if is_tracked and on_disk and rel_n not in SKIP_CONTENT:
            try:
                with open(
                    os.path.join(repo, *rel_n.split("/")),
                    encoding="utf-8", errors="ignore",
                ) as fh:
                    text = fh.read()
            except Exception:
                continue
            findings.extend(scan_content(rel_n, text))

    # 2) 提示级检查
    info_lines = []
    if any(f.startswith("dist/") for f in all_files):
        info_lines.append(
            "dist/ 被跟踪：脚本产物应被 .gitignore 忽略，避免公开。"
        )
    gi_text = ""
    gi_path = os.path.join(repo, ".gitignore")
    if os.path.isfile(gi_path):
        with open(gi_path, encoding="utf-8", errors="ignore") as fh:
            gi_text = fh.read()
    coverage = [
        ("dist/", "dist/"),
        ("memory/logs/", "memory/logs/"),
        ("inbox/", "inbox/"),
    ]
    for needle, label in coverage:
        ok = needle.rstrip("/") in gi_text
        state = "已覆盖" if ok else "未覆盖（建议添加）"
        info_lines.append(".gitignore 是否覆盖 %s：%s" % (label, state))

    # 3) 输出
    order = {HIGH: 0, MED: 1, INFO: 2}
    findings.sort(key=lambda x: (order[x[0]], x[2], x[3]))

    counts = {HIGH: 0, MED: 0, INFO: 0}
    for sev, reason, rel, line, _snip in findings:
        counts[sev] += 1

    print("=" * 64)
    print("AIBrain 上架前自检报告")
    print("仓库: %s" % repo)
    print("扫描文件数: %d （history=%s, template=%s）" % (len(all_files), args.history, args.template))
    print("=" * 64)

    cur = None
    for sev, reason, rel, line, snip in findings:
        if sev != cur:
            cur = sev
            print("")
            print("【%s】" % sev)
        loc = "%s:%d" % (rel, line) if line and line > 0 else rel
        print("  - %s | %s" % (loc, reason))
        if snip and snip not in ("(文件名)", "(目录)"):
            print("      片段: %s" % snip)

    if findings:
        print("")
    print("-" * 64)
    print("【%s】提示项" % INFO)
    for line in info_lines:
        print("  - %s" % line)
        counts[INFO] += 1

    print("")
    print("=" * 64)
    print(
        "统计：高危 %d / 中危 %d / 提示 %d"
        % (counts[HIGH], counts[MED], counts[INFO])
    )
    if counts[HIGH] > 0:
        print("结论：建议先处理 %d 项高危后再发布。" % counts[HIGH])
        return 1
    if args.template:
        print("结论：可以发布（模板包模式：目录级提示不影响发布，请确认中危项无误）。")
    else:
        print("结论：可以发布（如存在中危项请确认无误）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
